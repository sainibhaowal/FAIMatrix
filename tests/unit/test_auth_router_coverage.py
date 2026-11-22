"""Security-boundary tests for the auth router.

These tests keep the external mail, Redis, database, and vector services fake so
the branches are deterministic while preserving the router's real contracts.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import NAMESPACE_DNS, uuid5

import pytest


def _request(user=None):
    return SimpleNamespace(state=SimpleNamespace(user=user))


class _Session:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


class _UserRepo:
    record = None
    created = []
    updates = []
    pending = []
    enabled = []
    disabled = []
    regenerated = []

    def __init__(self, session):
        self.session = session

    def get_by_email(self, _email):
        return self.record

    def get_by_id(self, _user_id):
        return self.record

    def create_user(self, user_id, email, full_name=None):
        self.created.append((user_id, email, full_name))
        self.record = SimpleNamespace(
            id=user_id,
            email=email,
            full_name=full_name,
            totp_enabled=False,
            recovery_code_hashes=[],
        )
        return self.record

    def update_profile(self, user_id, full_name):
        self.updates.append((user_id, full_name))
        self.record.full_name = full_name
        return self.record

    def set_totp_pending(self, user_id, encrypted):
        self.pending.append((user_id, encrypted))

    def enable_totp(self, user_id, encrypted, hashes):
        self.enabled.append((user_id, encrypted, hashes))

    def set_recovery_code_hashes(self, user_id, hashes):
        self.regenerated.append((user_id, hashes))

    def disable_totp(self, user_id):
        self.disabled.append(user_id)


def _install_repo(monkeypatch, session, record=None):
    import runtime.context as runtime_context
    import store.pg.repos.user_repo as user_repo_module

    _UserRepo.record = record
    _UserRepo.created = []
    _UserRepo.updates = []
    _UserRepo.pending = []
    _UserRepo.enabled = []
    _UserRepo.disabled = []
    _UserRepo.regenerated = []
    monkeypatch.setattr(runtime_context, "get_session", lambda: session)
    monkeypatch.setattr(user_repo_module, "UserRepository", _UserRepo)


def test_auth_helpers_and_encryption_failures(monkeypatch):
    from api.routers import auth

    monkeypatch.delenv("NEXTAUTH_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="NEXTAUTH_SECRET"):
        auth._get_encryption_key()
    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    assert auth._normalize_code("a1-2 b") == "12"
    assert auth._verify_totp("JBSWY3DPEHPK3PXP", "12", now=1) is False
    with pytest.raises(ValueError, match="Invalid encrypted secret"):
        auth._decrypt_secret("bad-format")
    with pytest.raises(ValueError, match="Invalid encrypted secret"):
        auth._decrypt_secret("v2:00:00")
    assert "otpauth://totp/FAIMATRIX%3Auser%40example.com" in auth._build_otpauth_uri(
        "user@example.com", "SECRET"
    )
    assert len(auth._generate_otp()) == 6
    assert len(auth._generate_recovery_codes()) == auth.RECOVERY_CODE_COUNT
    user = SimpleNamespace(recovery_code_hashes=None)
    assert auth._consume_recovery_code(user, "") is False


def test_redis_auth_store_memory_expiry_and_failure_fallback(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    monkeypatch.delenv("REDIS_URL", raising=False)
    auth._OTP_STORE.clear()
    auth._RATE_LIMIT_STORE.clear()
    auth._FAILED_ATTEMPTS.clear()
    store = auth.RedisAuthStore()
    store.set_otp("email", "hash", 1)
    assert store.get_otp("email") == "hash"
    auth._OTP_STORE["expired"] = {
        "otp_hash": "old",
        "expiry": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    assert store.get_otp("expired") is None
    store.delete_otp("email")
    assert store.get_otp("email") is None
    assert store.check_rate_limit("a@example.com", 15, 1) is True
    store.record_rate_limit("a@example.com", 15)
    assert store.check_rate_limit("a@example.com", 15, 1) is False
    assert store.record_failed_attempt("a@example.com", 2, 30) == 1
    assert store.record_failed_attempt("a@example.com", 2, 30) == 2
    assert store.check_lockout("a@example.com") is not None
    store.clear_failed_attempts("a@example.com")
    assert store.check_lockout("a@example.com") is None

    class Pipeline:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def incr(self, key):
            client.values[key] = b"2"

        def expire(self, key, seconds):
            client.expiries[key] = seconds

        def execute(self):
            return []

    class Client:
        values = {}
        expiries = {}

        def ping(self):
            return True

        def setex(self, key, seconds, value):
            self.values[key] = value.encode() if isinstance(value, str) else value

        def get(self, key):
            return self.values.get(key)

        def delete(self, *keys):
            for key in keys:
                self.values.pop(key, None)

        def pipeline(self):
            return Pipeline()

        def incr(self, key):
            self.values[key] = b"5"
            return 5

        def expire(self, key, seconds):
            self.expiries[key] = seconds

        def ttl(self, key):
            return 12

    client = Client()
    fake_redis = SimpleNamespace(from_url=lambda _url: client)
    monkeypatch.setitem(sys.modules, "redis", fake_redis)
    monkeypatch.setenv("REDIS_URL", "redis://test")
    redis_store = auth.RedisAuthStore()
    redis_store.set_otp("e", "h", 2)
    assert redis_store.get_otp("e") == "h"
    redis_store.delete_otp("e")
    assert redis_store.check_rate_limit("a@example.com", 15, 10) is True
    redis_store.record_rate_limit("a@example.com", 15)
    client.values["auth:lock:whatever"] = b"true"
    # The exact key is derived from the email; use the router helper so the
    # fake Redis branch observes the same tenant-independent keying contract.
    client.values[f"auth:lock:{auth._hash_email('a@example.com')}"] = b"true"
    assert redis_store.check_lockout("a@example.com") == 12
    assert redis_store.record_failed_attempt("a@example.com", 5, 30) == 5
    redis_store.clear_failed_attempts("a@example.com")


def test_send_otp_email_configuration_and_http_outcomes(monkeypatch):
    from api.routers import auth

    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    assert auth._send_otp_email("a@example.com", "123456") is False


def test_redis_auth_store_operation_failures_fall_back_to_memory(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")

    class Broken:
        def __getattr__(self, _name):
            def fail(*_args, **_kwargs):
                raise RuntimeError("redis operation failed")

            return fail

    store = auth.RedisAuthStore()
    store._client = Broken()
    store._available = True
    store.set_otp("broken", "hash", 1)
    assert store.get_otp("broken") == "hash"
    store.delete_otp("broken")
    assert store.check_rate_limit("broken@example.com", 15, 5) is True
    store.record_rate_limit("broken@example.com", 15)
    assert store.check_lockout("broken@example.com") is None
    assert store.record_failed_attempt("broken@example.com", 5, 30) == 1
    store.clear_failed_attempts("broken@example.com")


def test_otp_hash_and_totp_window_contract(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    stored = auth._hash_otp("123456", "user@example.com")
    assert auth._verify_otp_hash(stored, "123456", "user@example.com") is True
    assert auth._verify_otp_hash(stored, "000000", "user@example.com") is False
    secret = "JBSWY3DPEHPK3PXP"
    now = 1_700_000_000
    assert auth._verify_totp(secret, auth._totp_at(secret, now // 30 + 2), now=now)
    code = auth._totp_at(secret, now // 30)
    assert auth._verify_totp(secret, f"{code[:3]}-{code[3:]}", now=now) is True
    calls = []

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code

    fake_httpx = SimpleNamespace(
        post=lambda *args, **kwargs: calls.append((args, kwargs)) or Response(200)
    )
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setenv("RESEND_API_KEY", "resend-test")
    assert auth._send_otp_email("a@example.com", "123456") is True
    assert calls[0][1]["json"]["to"] == ["a@example.com"]
    fake_httpx.post = lambda *args, **kwargs: Response(500)
    assert auth._send_otp_email("a@example.com", "123456") is False
    fake_httpx.post = lambda *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError("network")
    )
    assert auth._send_otp_email("a@example.com", "123456") is False


@pytest.mark.asyncio
async def test_request_otp_signup_rate_limit_and_delivery_branches(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    session = _Session()
    _install_repo(monkeypatch, session, None)
    monkeypatch.setattr(auth, "_check_rate_limit", lambda _email: True)
    monkeypatch.setattr(auth, "_record_rate_limit", lambda _email: None)
    monkeypatch.setattr(auth, "_send_otp_email", lambda *_args: True)
    response = await auth.request_otp(
        auth.OTPRequestBody(email="new@example.com", mode="signup"), None
    )
    assert response.success is True

    existing = SimpleNamespace(totp_enabled=False)
    _install_repo(monkeypatch, session, existing)
    with pytest.raises(auth.HTTPException) as exc:
        await auth.request_otp(
            auth.OTPRequestBody(email="new@example.com", mode="signup"), None
        )
    assert exc.value.status_code == 409

    _install_repo(monkeypatch, session, None)
    monkeypatch.setattr(auth, "_check_rate_limit", lambda _email: False)
    with pytest.raises(auth.HTTPException) as exc:
        await auth.request_otp(
            auth.OTPRequestBody(email="new@example.com", mode="signup"), None
        )
    assert exc.value.status_code == 429

    monkeypatch.setattr(auth, "_check_rate_limit", lambda _email: True)
    monkeypatch.setattr(auth, "_record_rate_limit", lambda _email: None)
    monkeypatch.setattr(auth, "_send_otp_email", lambda *_args: False)
    monkeypatch.setenv("FAIM_MODE", "production")
    with pytest.raises(auth.HTTPException) as exc:
        await auth.request_otp(
            auth.OTPRequestBody(email="new@example.com", mode="signup"), None
        )
    assert exc.value.status_code == 503
    monkeypatch.setenv("FAIM_MODE", "development")
    response = await auth.request_otp(
        auth.OTPRequestBody(email="new@example.com", mode="signup"), None
    )
    assert response.success is True


@pytest.mark.asyncio
async def test_verify_email_success_failure_lockout_and_registration(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    session = _Session()
    _install_repo(monkeypatch, session, None)
    monkeypatch.setattr(auth, "_check_lockout", lambda _email: None)
    monkeypatch.setattr(auth.store, "get_otp", lambda _key: None)
    attempts = []
    monkeypatch.setattr(
        auth, "_record_failed_attempt", lambda _email: attempts.append(1) or 1
    )
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="new@example.com", code="000000")
    )
    assert result.success is False and attempts

    monkeypatch.setattr(auth.store, "get_otp", lambda _key: "stored")
    monkeypatch.setattr(auth, "_verify_otp_hash", lambda *_args: False)
    monkeypatch.setattr(auth, "_record_failed_attempt", lambda _email: 5)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="new@example.com", code="000000")
    )
    assert "locked" in result.message

    _install_repo(monkeypatch, session, None)
    monkeypatch.setattr(auth, "_verify_otp_hash", lambda *_args: True)
    monkeypatch.setattr(auth.store, "delete_otp", lambda _key: None)
    monkeypatch.setattr(auth, "_clear_failed_attempts", lambda _email: None)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="new@example.com", code="123456", full_name="New User")
    )
    assert result.success is True
    assert _UserRepo.created
    assert session.closed >= 1

    record = SimpleNamespace(
        id=uuid5(NAMESPACE_DNS, "existing@example.com"),
        email="existing@example.com",
        full_name=None,
        totp_enabled=False,
        recovery_code_hashes=[],
    )
    _install_repo(monkeypatch, session, record)
    monkeypatch.setattr(auth.store, "get_otp", lambda _key: "stored")
    result = await auth.verify_otp(
        auth.OTPVerifyBody(
            email="existing@example.com", code="123456", full_name="Existing User"
        )
    )
    assert result.success is True
    assert _UserRepo.updates


@pytest.mark.asyncio
async def test_verify_totp_and_recovery_error_branches(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    session = _Session()
    _install_repo(monkeypatch, session, None)
    monkeypatch.setattr(auth, "_check_lockout", lambda _email: None)
    failures = []
    monkeypatch.setattr(
        auth, "_record_failed_attempt", lambda _email: failures.append(1) or 1
    )
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="x@example.com", code="1", factor_type="totp")
    )
    assert result.success is False

    record = SimpleNamespace(totp_enabled=False)
    _install_repo(monkeypatch, session, record)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="x@example.com", code="1", factor_type="totp")
    )
    assert result.success is False

    record = SimpleNamespace(totp_enabled=True, totp_secret_encrypted=None)
    _install_repo(monkeypatch, session, record)
    monkeypatch.setattr(auth, "_decrypt_secret", lambda _secret: "secret")
    monkeypatch.setattr(auth, "_verify_totp", lambda *_args: False)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="x@example.com", code="1", factor_type="totp")
    )
    assert result.success is False

    record = SimpleNamespace(totp_enabled=False, recovery_code_hashes=[])
    _install_repo(monkeypatch, session, record)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="x@example.com", code="1", factor_type="recovery_code")
    )
    assert result.success is False

    # A valid TOTP clears the lockout and follows the existing-user path.
    record = SimpleNamespace(
        id=uuid5(NAMESPACE_DNS, "x@example.com"),
        full_name="X",
        totp_enabled=True,
        totp_secret_encrypted="encrypted",
        recovery_code_hashes=[],
    )
    _install_repo(monkeypatch, session, record)
    monkeypatch.setattr(auth, "_decrypt_secret", lambda _value: "secret")
    monkeypatch.setattr(auth, "_verify_totp", lambda *_args: True)
    monkeypatch.setattr(auth, "_clear_failed_attempts", lambda _email: None)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="x@example.com", code="1", factor_type="totp")
    )
    assert result.success is True

    # Valid recovery code commits the one-time consumption.
    record.totp_enabled = True
    _install_repo(monkeypatch, session, record)
    monkeypatch.setattr(auth, "_consume_recovery_code", lambda *_args: True)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(
            email="x@example.com", code="recovery", factor_type="recovery_code"
        )
    )
    assert result.success is True
    assert session.commits >= 1

    record = SimpleNamespace(totp_enabled=True, recovery_code_hashes=[])
    _install_repo(monkeypatch, session, record)
    monkeypatch.setattr(auth, "_consume_recovery_code", lambda *_args: False)
    result = await auth.verify_otp(
        auth.OTPVerifyBody(email="x@example.com", code="1", factor_type="recovery_code")
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_totp_lifecycle_endpoints_and_auth_guard(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    user_id = uuid5(NAMESPACE_DNS, "user@example.com")
    unauthenticated = _request()
    with pytest.raises(auth.HTTPException) as exc:
        auth._current_user_id(unauthenticated)
    assert exc.value.status_code == 401
    with pytest.raises(auth.HTTPException):
        await auth.get_current_user(unauthenticated)
    with pytest.raises(auth.HTTPException):
        await auth.delete_account(unauthenticated)

    session = _Session()
    record = SimpleNamespace(
        id=user_id,
        email="user@example.com",
        full_name="User",
        totp_enabled=False,
        totp_secret_encrypted=None,
        recovery_code_hashes=[],
    )
    _install_repo(monkeypatch, session, record)
    request = _request({"id": str(user_id), "email": "user@example.com"})
    status = await auth.get_totp_status(request)
    assert status.enabled is False
    setup = await auth.setup_totp(request)
    assert setup.success and setup.secret
    assert _UserRepo.pending

    record.totp_secret_encrypted = auth._encrypt_secret(setup.secret)
    monkeypatch.setattr(auth, "_verify_totp", lambda *_args: False)
    with pytest.raises(auth.HTTPException) as exc:
        await auth.confirm_totp(auth.TOTPConfirmBody(code="000000"), request)
    assert exc.value.status_code == 400

    monkeypatch.setattr(auth, "_verify_totp", lambda *_args: True)
    monkeypatch.setattr(auth, "_generate_recovery_codes", lambda: ["RECOVERY123"])
    monkeypatch.setattr(auth, "_hash_recovery_codes", lambda codes: ["hash"])
    confirm = await auth.confirm_totp(auth.TOTPConfirmBody(code="123456"), request)
    assert confirm.success

    record.totp_enabled = True
    record.totp_secret_encrypted = auth._encrypt_secret(setup.secret)
    regenerate = await auth.regenerate_recovery_codes(
        auth.TOTPConfirmBody(code="123456"), request
    )
    assert regenerate.success
    disabled = await auth.disable_totp(auth.TOTPDisableBody(code="123456"), request)
    assert disabled.enabled is False

    current = await auth.get_current_user(request)
    assert current.user["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_totp_not_found_and_invalid_state_errors(monkeypatch):
    from api.routers import auth

    monkeypatch.setenv("NEXTAUTH_SECRET", "auth-test-secret")
    user_id = uuid5(NAMESPACE_DNS, "missing@example.com")
    request = _request({"id": str(user_id), "email": "missing@example.com"})
    session = _Session()
    _install_repo(monkeypatch, session, None)
    with pytest.raises(auth.HTTPException) as exc:
        await auth.get_totp_status(request)
    assert exc.value.status_code == 404
    with pytest.raises(auth.HTTPException) as exc:
        await auth.setup_totp(request)
    assert exc.value.status_code == 404
    with pytest.raises(auth.HTTPException) as exc:
        await auth.confirm_totp(auth.TOTPConfirmBody(code="1"), request)
    assert exc.value.status_code == 400
    with pytest.raises(auth.HTTPException) as exc:
        await auth.regenerate_recovery_codes(auth.TOTPConfirmBody(code="1"), request)
    assert exc.value.status_code == 400
    with pytest.raises(auth.HTTPException) as exc:
        await auth.disable_totp(auth.TOTPDisableBody(code="1"), request)
    assert exc.value.status_code == 400

    record = SimpleNamespace(
        id=user_id,
        email="missing@example.com",
        totp_enabled=True,
        totp_secret_encrypted=auth._encrypt_secret("JBSWY3DPEHPK3PXP"),
        recovery_code_hashes=[],
    )
    _install_repo(monkeypatch, session, record)
    with pytest.raises(auth.HTTPException) as exc:
        await auth.setup_totp(request)
    assert exc.value.status_code == 409
    with pytest.raises(auth.HTTPException) as exc:
        await auth.confirm_totp(auth.TOTPConfirmBody(code="1"), request)
    assert exc.value.status_code == 409
    with pytest.raises(auth.HTTPException) as exc:
        await auth.regenerate_recovery_codes(auth.TOTPConfirmBody(code="1"), request)
    assert exc.value.status_code == 400
    with pytest.raises(auth.HTTPException) as exc:
        await auth.disable_totp(auth.TOTPDisableBody(code="1"), request)
    assert exc.value.status_code == 400

    no_email_request = _request({"id": str(user_id)})
    record.totp_enabled = False
    with pytest.raises(auth.HTTPException) as exc:
        await auth.setup_totp(no_email_request)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_account_purges_sql_and_vector_collection(monkeypatch):
    import index.qdrant_index as qdrant_module
    import runtime.context as runtime_context
    from api.routers import auth

    class Query:
        def __init__(self):
            self.filters = []
            self.deleted = 0

        def filter(self, *args):
            self.filters.extend(args)
            return self

        def filter_by(self, **kwargs):
            self.filters.append(kwargs)
            return self

        def delete(self, **_kwargs):
            self.deleted += 1
            return 1

        def __clause_element__(self):
            from sqlalchemy import select

            return select(1)

    class Session(_Session):
        def __init__(self):
            super().__init__()
            self.queries = []

        def query(self, *_models):
            query = Query()
            self.queries.append(query)
            return query

    session = Session()
    monkeypatch.setattr(runtime_context, "get_session", lambda: session)
    deleted = []

    class Index:
        def __init__(self, project_id):
            deleted.append(project_id)

        def delete_collection(self):
            deleted.append("collection")

    monkeypatch.setattr(qdrant_module, "FAIMIndex", Index)
    user_id = str(uuid5(NAMESPACE_DNS, "purge@example.com"))
    result = await auth.delete_account(_request({"id": user_id}))
    assert result.success is True
    assert session.commits == 1
    assert session.closed == 1
    assert "collection" in deleted
    assert len(session.queries) == 12


@pytest.mark.asyncio
async def test_delete_account_rolls_back_and_tolerates_vector_failure(monkeypatch):
    import index.qdrant_index as qdrant_module
    import runtime.context as runtime_context
    from api.routers import auth

    class BrokenSession(_Session):
        def query(self, *_models):
            raise RuntimeError("database unavailable")

    session = BrokenSession()
    monkeypatch.setattr(runtime_context, "get_session", lambda: session)
    with pytest.raises(auth.HTTPException) as exc:
        await auth.delete_account(_request({"id": "user-id"}))
    assert exc.value.status_code == 500
    assert session.rollbacks == 1
    assert session.closed == 1

    class GoodSession(_Session):
        def query(self, *_models):
            class Query:
                def filter(self, *args):
                    return self

                def filter_by(self, **kwargs):
                    return self

                def delete(self, **kwargs):
                    return 1

                def __clause_element__(self):
                    from sqlalchemy import select

                    return select(1)

            return Query()

    # This query fixture is intentionally minimal; the vector failure is
    # independently covered after the SQL transaction completes.
    good = GoodSession()
    monkeypatch.setattr(runtime_context, "get_session", lambda: good)

    class BrokenIndex:
        def __init__(self, _project_id):
            pass

        def delete_collection(self):
            raise RuntimeError("qdrant unavailable")

    monkeypatch.setattr(qdrant_module, "FAIMIndex", BrokenIndex)
    result = await auth.delete_account(_request({"id": "user-id"}))
    assert result.success is True

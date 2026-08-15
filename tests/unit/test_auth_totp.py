"""TOTP authenticator login tests."""

from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

import pytest
from api.routers import auth as auth_router
from store.pg.models_auth import UserModel


def test_totp_secret_round_trips_encrypted(monkeypatch):
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret-for-totp")

    secret = auth_router._generate_totp_secret()
    encrypted = auth_router._encrypt_secret(secret)

    assert encrypted != secret
    assert encrypted.startswith("v1:")
    assert auth_router._decrypt_secret(encrypted) == secret


def test_totp_code_verifies_with_clock_window():
    secret = "JBSWY3DPEHPK3PXP"
    now = 1_700_000_000
    counter = now // auth_router.TOTP_PERIOD_SECONDS
    code = auth_router._totp_at(secret, counter)

    assert auth_router._verify_totp(secret, code, now=now) is True
    assert auth_router._verify_totp(secret, "000000", now=now) is False


def test_recovery_code_consumes_one_hash():
    codes = ["ABCDEFGHJK", "KLMNPQRSTU"]
    hashes = auth_router._hash_recovery_codes(codes)
    user = UserModel(
        email="user@example.com",
        recovery_code_hashes=hashes,
    )

    assert auth_router._consume_recovery_code(user, "abcdefghjk") is True
    assert len(user.recovery_code_hashes) == 1
    assert auth_router._consume_recovery_code(user, "ABCDEFGHJK") is False


def test_totp_model_and_schema_markers_present():
    cols = set(UserModel.__table__.columns.keys())
    assert {
        "totp_enabled",
        "totp_secret_encrypted",
        "totp_confirmed_at",
        "recovery_code_hashes",
    } <= cols

    migration_file = Path("faim_native/store/pg/migrations/0022_user_totp_2fa.sql")
    assert migration_file.exists()

    schema = Path("faim_native/store/pg/schema.sql").read_text(encoding="utf-8")
    assert "totp_secret_encrypted" in schema
    assert "recovery_code_hashes" in schema


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.closed = 0

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed += 1


class _FakeUserRepo:
    user = None
    created = []

    def __init__(self, session) -> None:  # noqa: ANN001
        self.session = session

    def get_by_email(self, email: str):  # noqa: ANN201
        return self.user

    def create_user(self, user_id, email: str, full_name=None):  # noqa: ANN001, ANN201
        self.created.append((user_id, email, full_name))
        self.user = UserModel(id=user_id, email=email, full_name=full_name)
        return self.user

    def update_profile(self, user_id, full_name: str):  # noqa: ANN001, ANN201
        if self.user:
            self.user.full_name = full_name
        return self.user


@pytest.mark.asyncio
async def test_otp_request_default_email_when_totp_disabled(monkeypatch):
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret-for-totp")
    fake_session = _FakeSession()
    _FakeUserRepo.user = UserModel(
        id=uuid5(NAMESPACE_DNS, "user@example.com"),
        email="user@example.com",
        totp_enabled=False,
    )

    import runtime.context as runtime_context
    import store.pg.repos.user_repo as user_repo_module

    monkeypatch.setattr(runtime_context, "get_session", lambda: fake_session)
    monkeypatch.setattr(user_repo_module, "UserRepository", _FakeUserRepo)
    monkeypatch.setattr(auth_router, "_check_rate_limit", lambda _email: True)
    monkeypatch.setattr(auth_router, "_record_rate_limit", lambda _email: None)
    monkeypatch.setattr(auth_router, "_send_otp_email", lambda _email, _code: True)

    response = await auth_router.request_otp(
        auth_router.OTPRequestBody(email="user@example.com", mode="login"),
        request=None,
    )

    assert response.success is True
    assert response.method == "email_otp"
    assert response.totp_enabled is False
    assert fake_session.closed == 1


@pytest.mark.asyncio
async def test_otp_request_routes_totp_user_to_authenticator_app(monkeypatch):
    """A TOTP-enabled user must be challenged by the authenticator app, not
    sent an email OTP (email OTP would bypass the second factor)."""
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret-for-totp")
    fake_session = _FakeSession()
    _FakeUserRepo.user = UserModel(
        id=uuid5(NAMESPACE_DNS, "user@example.com"),
        email="user@example.com",
        totp_enabled=True,
        totp_secret_encrypted=auth_router._encrypt_secret("JBSWY3DPEHPK3PXP"),
    )

    import runtime.context as runtime_context
    import store.pg.repos.user_repo as user_repo_module

    monkeypatch.setattr(runtime_context, "get_session", lambda: fake_session)
    monkeypatch.setattr(user_repo_module, "UserRepository", _FakeUserRepo)
    monkeypatch.setattr(auth_router, "_check_rate_limit", lambda _email: True)
    sent_emails = []
    monkeypatch.setattr(
        auth_router, "_send_otp_email", lambda _email, _code: sent_emails.append(_email) or True
    )

    response = await auth_router.request_otp(
        auth_router.OTPRequestBody(email="user@example.com", mode="login"),
        request=None,
    )

    assert response.success is True
    assert response.method == "totp"
    assert response.totp_enabled is True
    # No email OTP may be sent for a TOTP user (no 2FA bypass).
    assert sent_emails == []


@pytest.mark.asyncio
async def test_otp_login_does_not_allow_admin_email_shortcut(monkeypatch):
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret-for-totp")
    fake_session = _FakeSession()
    _FakeUserRepo.user = None

    import runtime.context as runtime_context
    import store.pg.repos.user_repo as user_repo_module

    monkeypatch.setattr(runtime_context, "get_session", lambda: fake_session)
    monkeypatch.setattr(user_repo_module, "UserRepository", _FakeUserRepo)

    with pytest.raises(auth_router.HTTPException) as exc:
        await auth_router.request_otp(
            auth_router.OTPRequestBody(email="admin@example.com", mode="login"),
            request=None,
        )

    assert exc.value.status_code == 404
    assert fake_session.closed == 1


@pytest.mark.asyncio
async def test_recovery_code_login_consumes_code_once(monkeypatch):
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret-for-totp")
    fake_session = _FakeSession()
    recovery_hashes = auth_router._hash_recovery_codes(["ABCDEFGHJK"])
    _FakeUserRepo.user = UserModel(
        id=uuid5(NAMESPACE_DNS, "user@example.com"),
        email="user@example.com",
        full_name="User",
        totp_enabled=True,
        totp_secret_encrypted=auth_router._encrypt_secret("JBSWY3DPEHPK3PXP"),
        recovery_code_hashes=recovery_hashes,
    )

    import runtime.context as runtime_context
    import store.pg.repos.user_repo as user_repo_module

    monkeypatch.setattr(runtime_context, "get_session", lambda: fake_session)
    monkeypatch.setattr(user_repo_module, "UserRepository", _FakeUserRepo)
    monkeypatch.setattr(auth_router, "_check_lockout", lambda _email: None)
    monkeypatch.setattr(auth_router, "_clear_failed_attempts", lambda _email: None)

    first = await auth_router.verify_otp(
        auth_router.OTPVerifyBody(
            email="user@example.com",
            code="abcdefghjk",
            factor_type="recovery_code",
        )
    )
    second = await auth_router.verify_otp(
        auth_router.OTPVerifyBody(
            email="user@example.com",
            code="abcdefghjk",
            factor_type="recovery_code",
        )
    )

    assert first.success is True
    assert first.user is not None
    assert first.user["email"] == "user@example.com"
    assert _FakeUserRepo.user.recovery_code_hashes == []
    assert fake_session.commits == 1
    assert second.success is False

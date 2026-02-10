"""Phase D: production security policy enforcement tests."""

from __future__ import annotations


def test_runtime_config_requires_encryption_and_fail_closed_in_production(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_p": ["key_p"]}')
    monkeypatch.setenv("FAIM_ENV", "production")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "false")
    monkeypatch.setenv("FAIM_ENCRYPTION_FAIL_CLOSED", "false")

    reset_config()
    try:
        try:
            load_config()
            assert False, "Expected production policy validation failure"
        except ValueError as exc:
            message = str(exc)
            assert "Production requires FAIM_ENCRYPTION_AT_REST=true" in message
            assert "Production requires FAIM_ENCRYPTION_FAIL_CLOSED=true" in message
    finally:
        reset_config()


def test_runtime_context_rejects_plain_raw_store_in_production(monkeypatch):
    import runtime.context as runtime_context

    runtime_context._raw_store_plain = None
    runtime_context._raw_store_by_tenant.clear()

    monkeypatch.setenv("FAIM_ENV", "production")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "false")
    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "")

    try:
        runtime_context._get_raw_store("tenant_secure")
        assert False, "Expected RuntimeError for plaintext raw store in production"
    except RuntimeError as exc:
        assert "requires encrypted raw store" in str(exc)


def test_runtime_context_fails_closed_on_cipher_init_error_in_production(monkeypatch):
    import runtime.context as runtime_context

    runtime_context._raw_store_plain = None
    runtime_context._raw_store_by_tenant.clear()

    monkeypatch.setenv("FAIM_ENV", "production")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "true")
    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "envelope")
    monkeypatch.setenv("FAIM_ENCRYPTION_FAIL_CLOSED", "true")
    monkeypatch.delenv("FAIM_MASTER_KEY", raising=False)
    monkeypatch.delenv("FAIM_MASTER_PASSWORD", raising=False)
    monkeypatch.delenv("FAIM_MASTER_SALT", raising=False)

    try:
        runtime_context._get_raw_store("tenant_secure")
        assert False, "Expected RuntimeError when envelope cipher initialization fails"
    except RuntimeError as exc:
        assert "Encryption-at-rest initialization failed" in str(exc)

from __future__ import annotations

import pytest


def test_dev_cors_defaults_include_localhost(monkeypatch):
    from api.app import _get_cors_origins

    monkeypatch.delenv("FAIM_CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("FAIM_PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("NEXTAUTH_URL", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("FAIM_MODE", raising=False)
    monkeypatch.delenv("FAIM_ENV", raising=False)

    origins = _get_cors_origins()

    assert "http://localhost:8010" in origins
    assert "http://127.0.0.1:8010" in origins
    assert "*" not in origins


def test_prod_cors_requires_explicit_public_origin(monkeypatch):
    from api.app import _get_cors_origins

    monkeypatch.setenv("FAIM_MODE", "production")
    monkeypatch.delenv("FAIM_CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("FAIM_PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("NEXTAUTH_URL", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    with pytest.raises(RuntimeError):
        _get_cors_origins()


def test_prod_cors_uses_explicit_origin(monkeypatch):
    from api.app import _get_cors_origins

    monkeypatch.setenv("FAIM_MODE", "production")
    monkeypatch.setenv("FAIM_CORS_ALLOW_ORIGINS", "https://app.example.com")

    origins = _get_cors_origins()

    assert origins == ["https://app.example.com"]


def test_prod_csp_removes_unsafe_eval_and_localhost(monkeypatch):
    from api.middleware.security import build_content_security_policy

    monkeypatch.setenv("FAIM_MODE", "production")
    monkeypatch.setenv("FAIM_PUBLIC_ORIGIN", "https://app.example.com")
    monkeypatch.setenv("NEXTAUTH_URL", "https://app.example.com")

    csp = build_content_security_policy()

    assert "'unsafe-eval'" not in csp
    assert "http://localhost:8000" not in csp
    assert "https://app.example.com" in csp


def test_dev_csp_allows_localhost_and_eval(monkeypatch):
    from api.middleware.security import build_content_security_policy

    monkeypatch.setenv("FAIM_MODE", "development")
    monkeypatch.delenv("FAIM_PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("NEXTAUTH_URL", raising=False)

    csp = build_content_security_policy()

    assert "'unsafe-eval'" in csp
    assert "http://localhost:8000" in csp

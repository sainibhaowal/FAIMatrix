"""Unit tests for MCP Streamable HTTP endpoint and OAuth 2.1 + PKCE flow."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sys
import time
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
_FAIM_NATIVE = _ROOT / "faim_native"
if str(_FAIM_NATIVE) not in sys.path:
    sys.path.insert(0, str(_FAIM_NATIVE))


def _make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def test_mcp_oauth_pkce_end_to_end(monkeypatch) -> None:
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-mcp-oauth-secret-key-123456")
    monkeypatch.setenv("FAIM_PUBLIC_ORIGIN", "https://api.faim.example")
    monkeypatch.setenv("FRONTEND_URL", "https://app.faim.example")

    from api.app import create_app

    client = TestClient(create_app())

    # 1. Unauthenticated /mcp must return 401 with WWW-Authenticate resource_metadata
    unauth = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert unauth.status_code == 401
    www_auth = unauth.headers.get("www-authenticate", "")
    assert "resource_metadata=" in www_auth
    assert "/.well-known/oauth-protected-resource" in www_auth

    # 2. Discovery metadata
    prm = client.get("/.well-known/oauth-protected-resource")
    assert prm.status_code == 200
    assert prm.json()["resource"] == "https://api.faim.example/mcp"

    asm = client.get("/.well-known/oauth-authorization-server")
    assert asm.status_code == 200
    assert (
        asm.json()["authorization_endpoint"]
        == "https://app.faim.example/oauth/authorize"
    )
    assert asm.json()["token_endpoint"] == "https://api.faim.example/oauth/token"
    assert (
        asm.json()["registration_endpoint"] == "https://api.faim.example/oauth/register"
    )
    assert "S256" in asm.json()["code_challenge_methods_supported"]

    # 3. Dynamic Client Registration
    reg = client.post(
        "/oauth/register",
        json={
            "client_name": "Cursor",
            "redirect_uris": ["http://127.0.0.1:4321/callback"],
        },
    )
    assert reg.status_code == 201
    client_id = reg.json()["client_id"]

    # 4. Mint auth code as a logged-in NextAuth user
    user_jwt = jwt.encode(
        {
            "sub": "user-42",
            "userId": "user-42",
            "email": "alice@example.com",
            "exp": int(time.time()) + 300,
        },
        os.environ["NEXTAUTH_SECRET"],
        algorithm="HS256",
    )
    verifier, challenge = _make_pkce()
    code_resp = client.post(
        "/api/v1/oauth/code",
        headers={"Authorization": f"Bearer {user_jwt}"},
        json={
            "client_id": client_id,
            "redirect_uri": "http://127.0.0.1:4321/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "mcp:read mcp:write",
            "state": "xyz",
        },
    )
    assert code_resp.status_code == 200
    code = code_resp.json()["code"]

    # 5. Exchange code + PKCE verifier for OAuth token pair
    tok = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:4321/callback",
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert tok.status_code == 200
    tok_data = tok.json()
    access_token = tok_data["access_token"]
    refresh_token = tok_data["refresh_token"]

    # Single-use code replay must fail
    replay = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:4321/callback",
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert replay.status_code == 400

    # Refresh token flow
    refreshed = client.post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    # 6. Call /mcp with OAuth access_token
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    init_resp = client.post(
        "/mcp",
        headers=auth_headers,
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert init_resp.status_code == 200
    assert init_resp.headers.get("mcp-session-id")
    assert init_resp.json()["result"]["serverInfo"]["name"] == "faim-mcp"

    tools_resp = client.post(
        "/mcp",
        headers=auth_headers,
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    assert tools_resp.status_code == 200
    tool_names = {t["name"] for t in tools_resp.json()["result"]["tools"]}
    assert {
        "faim_memory_write",
        "faim_memory_search",
        "faim_query",
        "faim_ingest_text",
        "faim_memory_get",
        "faim_graph_surface",
    }.issubset(tool_names)

    # 7. List active MCP grants for this user
    grants_resp = client.get(
        "/api/v1/oauth/grants", headers={"Authorization": f"Bearer {user_jwt}"}
    )
    assert grants_resp.status_code == 200
    grants = grants_resp.json()["items"]
    assert len(grants) == 1
    grant_id = grants[0]["grant_id"]
    assert grants[0]["client_name"] == "Cursor"
    assert grants[0]["last_used_at"] is not None

    # 8. Disconnect grant -> subsequent /mcp and refresh_token calls must fail with 401
    disc = client.delete(
        f"/api/v1/oauth/grants/{grant_id}",
        headers={"Authorization": f"Bearer {user_jwt}"},
    )
    assert disc.status_code == 200
    assert disc.json()["disconnected"] is True

    after_disc_mcp = client.post(
        "/mcp",
        headers=auth_headers,
        json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
    )
    assert after_disc_mcp.status_code == 401
    assert "resource_metadata=" in after_disc_mcp.headers.get("www-authenticate", "")

    after_disc_refresh = client.post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    assert after_disc_refresh.status_code == 401

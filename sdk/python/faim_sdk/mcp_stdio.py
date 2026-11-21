"""FAIM MCP CLI: Browser OAuth 2.1 + PKCE login and local stdio MCP bridge."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from typing import Any, Dict

import httpx

from .client import DEFAULT_CREDENTIALS_PATH, FAIMClient


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def cmd_login(base_url: str) -> int:
    base_url = base_url.rstrip("/")
    with httpx.Client(base_url=base_url, timeout=15.0) as http:
        meta = http.get("/.well-known/oauth-authorization-server")
        meta.raise_for_status()
        as_meta = meta.json()

        result_box: Dict[str, str] = {}
        done = threading.Event()

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)
                if "code" in qs:
                    result_box["code"] = qs["code"][0]
                if "state" in qs:
                    result_box["state"] = qs["state"][0]
                if "error" in qs:
                    result_box["error"] = qs["error"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h3>FAIM MCP connected. You can close this window.</h3></body></html>"
                )
                done.set()

            def log_message(self, format: str, *args: Any) -> None:
                return

        server = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
        port = server.server_address[1]
        redirect_uri = f"http://127.0.0.1:{port}/callback"

        reg = http.post(
            as_meta["registration_endpoint"],
            json={"client_name": "faim-mcp-cli", "redirect_uris": [redirect_uri]},
        )
        reg.raise_for_status()
        client_id = reg.json()["client_id"]

        verifier, challenge = _pkce_pair()
        state = secrets.token_urlsafe(16)
        auth_params = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "mcp:read mcp:write",
                "state": state,
            }
        )
        auth_url = f"{as_meta['authorization_endpoint']}?{auth_params}"

        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()
        print(f"Opening browser to authorize FAIM MCP:\n{auth_url}", file=sys.stderr)
        webbrowser.open(auth_url)
        done.wait(timeout=300)
        server.server_close()

        if "error" in result_box or "code" not in result_box:
            print(
                f"Authorization failed: {result_box.get('error', 'timeout')}",
                file=sys.stderr,
            )
            return 1
        if result_box.get("state") != state:
            print("State mismatch during OAuth callback", file=sys.stderr)
            return 1

        tok = http.post(
            as_meta["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": result_box["code"],
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        )
        tok.raise_for_status()
        creds = tok.json()
        creds["base_url"] = base_url
        creds["client_id"] = client_id
        DEFAULT_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_CREDENTIALS_PATH.write_text(
            json.dumps(creds, indent=2), encoding="utf-8"
        )
        print(
            f"Saved FAIM MCP credentials to {DEFAULT_CREDENTIALS_PATH}", file=sys.stderr
        )
        return 0


def cmd_stdio(base_url: str | None) -> int:
    client = FAIMClient(base_url=base_url)
    try:
        for line in sys.stdin:
            raw = line.strip()
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            resp = client._client.post("/mcp", json=msg, headers=client._headers())
            if resp.status_code == 202 or not resp.content:
                continue
            sys.stdout.write(resp.text + "\n")
            sys.stdout.flush()
    finally:
        client.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="faim-mcp")
    sub = parser.add_subparsers(dest="command")
    login_p = sub.add_parser(
        "login", help="Authenticate with your FAIM account via browser"
    )
    login_p.add_argument(
        "--url", default=os.getenv("FAIM_BASE_URL", "http://localhost:8000")
    )
    stdio_p = sub.add_parser("stdio", help="Run stdio MCP bridge (default)")
    stdio_p.add_argument("--url", default=None)

    args = parser.parse_args()
    if args.command == "login":
        raise SystemExit(cmd_login(args.url))
    raise SystemExit(cmd_stdio(getattr(args, "url", None)))


if __name__ == "__main__":
    main()

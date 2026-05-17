from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_localprod_compose_includes_caddy_and_local_ports():
    content = (ROOT / "docker-compose.localprod.yml").read_text()

    assert "caddy:" in content
    assert "8443:443" in content
    assert "8080:80" in content
    assert "FAIM_PUBLIC_ORIGIN: https://faimatrix.localhost:8443" in content
    assert "NEXTAUTH_URL: https://faimatrix.localhost:8443" in content
    assert "FAIM_ADMIN_KEY" in content
    assert "RESEND_API_KEY" in content
    assert "FAIM_ADMIN_EMAILS_JSON" in content


def test_localprod_caddy_routes_backend_health_and_frontend():
    content = (ROOT / "deploy/Caddyfile.localprod").read_text()

    assert "\nlocalhost {" not in content
    assert "reverse_proxy api:8000" in content
    assert "reverse_proxy frontend:8010" in content
    assert "tls /data/certs/faimatrix.localhost.pem" in content
    assert "Strict-Transport-Security" in content
    assert "handle @backend_health" in content


def test_localprod_scripts_are_present():
    for rel in [
        "scripts/localprod_up.sh",
        "scripts/localprod_down.sh",
        "scripts/localprod_smoke.sh",
        "scripts/localprod_backup.sh",
        "scripts/localprod_restore.sh",
    ]:
        assert (ROOT / rel).exists(), rel

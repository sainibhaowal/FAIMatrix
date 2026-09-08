from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_vps_compose_keeps_app_private_and_sets_public_origin():
    content = (ROOT / "docker-compose.vps.yml").read_text()

    assert "caddy:" in content
    caddy_section = content.split("\n  caddy:", 1)[1].split("\nnetworks:", 1)[0]
    assert "ports:" not in caddy_section
    assert "networks: [faim-net, gateway-net]" in caddy_section
    assert "name: aurelinx_default" in content
    assert "FAIM_PUBLIC_ORIGIN:" in content and "https://faimatrix.com" in content
    assert "NEXTAUTH_URL:" in content and "https://faimatrix.com" in content
    assert "RESEND_API_KEY" in content
    assert "Runtime/vps" in content


def test_vps_caddy_routes_backend_health_and_frontend():
    content = (ROOT / "deploy/Caddyfile.vps").read_text()

    assert ":80 {" in content
    assert "faimatrix.com" not in content
    assert "www.faimatrix.com" not in content
    assert "reverse_proxy api:8000" in content
    assert "reverse_proxy frontend:8010" in content
    assert "Strict-Transport-Security" in content


def test_vps_scripts_are_present():
    for rel in [
        "scripts/vps_sync.sh",
        "scripts/vps_up.sh",
        "scripts/vps_down.sh",
        "scripts/vps_smoke.sh",
        "scripts/vps_backup.sh",
        "scripts/vps_restore.sh",
    ]:
        assert (ROOT / rel).exists(), rel

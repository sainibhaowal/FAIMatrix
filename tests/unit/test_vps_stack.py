from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_unified_compose_defines_vps_proxy_and_gpu_controls():
    content = (ROOT / "docker-compose.yml").read_text()

    assert "caddy:" in content
    caddy_section = content.split("\n  caddy:", 1)[1].split("\n  postgres-test:", 1)[0]
    assert "profiles: [\"vps\"]" in caddy_section
    assert "ports:" not in caddy_section
    assert "networks: [faim-net, gateway-net]" in caddy_section
    assert "gateway-net:" in content and "${FAIM_GATEWAY_NETWORK:-faim-gateway-net}" in content
    assert "FAIM_CONTAINER_RUNTIME" in content
    assert "NVIDIA_VISIBLE_DEVICES" in content
    assert "FAIM_MIN_CUDA_FREE_MIB" in content
    assert "worker-ingest:" in content and "worker-evolve:" in content
    assert "API_HOST=faim-api:8000" in content


def test_vps_caddy_routes_backend_health_and_frontend():
    content = (ROOT / "deploy/Caddyfile.vps").read_text()

    assert ":80 {" in content
    assert "reverse_proxy faim-api:8000" in content
    assert "reverse_proxy faim-frontend:8010" in content
    assert "Strict-Transport-Security" in content


def test_env_example_keys_are_wired_into_unified_compose():
    compose_content = (ROOT / "docker-compose.yml").read_text()
    example_lines = (ROOT / ".env.example").read_text().splitlines()
    keys = [
        line.split("=", 1)[0].strip()
        for line in example_lines
        if line.strip() and not line.strip().startswith("#") and "=" in line
    ]
    missing = [key for key in keys if key not in compose_content]
    assert not missing, f".env.example keys missing from docker-compose.yml: {missing}"


def test_vps_scripts_are_present():
    for rel in [
        "scripts/vps_sync.sh",
        "scripts/vps_up.sh",
        "scripts/vps_down.sh",
        "scripts/vps_smoke.sh",
        "scripts/vps_backup.sh",
        "scripts/vps_restore.sh",
        "scripts/vps_deploy_ci.sh",
    ]:
        assert (ROOT / rel).exists(), rel

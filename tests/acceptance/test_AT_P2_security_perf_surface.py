"""Acceptance checks for P2 security/perf hardening surface."""

from __future__ import annotations

import inspect
import pathlib


def test_tenant_crypto_migration_exists():
    migration_path = pathlib.Path(
        "faim_native/store/pg/migrations/0006_tenant_crypto_keys.sql"
    )
    assert migration_path.exists()
    content = migration_path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS tenant_crypto_keys" in content
    assert "dek_wrapped" in content


def test_tenant_crypto_rotation_migration_exists():
    migration_path = pathlib.Path(
        "faim_native/store/pg/migrations/0027_tenant_crypto_keys_rotation_metadata.sql"
    )
    assert migration_path.exists()
    content = migration_path.read_text(encoding="utf-8")
    assert "master_key_fingerprint" in content


def test_query_flow_has_cache_parameter():
    from orchestration.query_flow import run_query

    sig = inspect.signature(run_query)
    assert "cache" in sig.parameters


def test_perf_layer_marked_isolated():
    from orchestration.perf import PERF_LAYER_STATUS

    assert PERF_LAYER_STATUS == "isolated_legacy"

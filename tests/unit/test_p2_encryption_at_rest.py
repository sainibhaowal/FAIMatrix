"""P2 tests: tenant envelope encryption-at-rest wiring."""

from __future__ import annotations


def test_tenant_dek_manager_roundtrip(monkeypatch, session_factory):
    """Tenant DEK should be created once and decrypt correctly."""
    from store.crypto.envelope import TenantDEKManager
    from store.pg.models_crypto import TenantCryptoKey

    monkeypatch.setenv("FAIM_MASTER_KEY", "11" * 32)

    manager = TenantDEKManager(session_factory=session_factory.create)
    plaintext = b"p2-envelope-roundtrip"

    encrypted = manager.encrypt_for_tenant("tenant_alpha", plaintext)
    assert encrypted != plaintext

    decrypted = manager.decrypt_for_tenant("tenant_alpha", encrypted)
    assert decrypted == plaintext

    # Ensure only one wrapped key row exists for this tenant.
    with session_factory.session() as session:
        rows = (
            session.query(TenantCryptoKey)
            .filter(TenantCryptoKey.tenant_id == "tenant_alpha")
            .all()
        )
        assert len(rows) == 1
        assert rows[0].dek_wrapped
        assert rows[0].master_key_fingerprint


def test_encrypted_raw_store_stores_ciphertext(
    monkeypatch, tmp_blob_dir, session_factory
):
    """EncryptedRawStore should persist ciphertext while returning plaintext on load."""
    from store.raw.crypto import EnvelopeCipher
    from store.raw.encrypted_payload_store import EncryptedRawStore
    from store.raw.raw_store import RawStore

    monkeypatch.setenv("FAIM_MASTER_KEY", "22" * 32)

    inner = RawStore(tmp_blob_dir)
    cipher = EnvelopeCipher(
        tenant_id="tenant_beta", session_factory=session_factory.create
    )
    store = EncryptedRawStore(inner=inner, cipher=cipher, graph_id="tenant_beta")

    payload = b"secret-bytes-for-p2"
    raw_ref = store.store(payload, mime_type="text/plain", graph_id="graph_demo")

    raw_ciphertext = inner.load(raw_ref, verify=True)
    assert raw_ciphertext != payload
    assert store.load(raw_ref, verify=True) == payload

    stats = store.get_stats()
    assert stats.get("encrypted") is True
    assert "cipher_version" in stats


def test_tenant_dek_rotation_rewraps_and_preserves_payload(monkeypatch, session_factory):
    import tempfile

    from store.crypto.envelope import TenantDEKManager, master_key_fingerprint
    from store.pg.models_crypto import TenantCryptoKey
    from store.raw.crypto import EnvelopeCipher
    from store.raw.encrypted_payload_store import EncryptedRawStore
    from store.raw.raw_store import RawStore

    old_key = "33" * 32
    new_key = "44" * 32

    monkeypatch.setenv("FAIM_MASTER_KEY", old_key)
    inner = RawStore(tempfile.mkdtemp(prefix="faim-rotation-test-"))
    tenant_id = "tenant_rotation"
    cipher = EnvelopeCipher(tenant_id=tenant_id, session_factory=session_factory.create)
    store = EncryptedRawStore(inner=inner, cipher=cipher, graph_id=tenant_id)

    payload = b"rotation-preserves-payload"
    raw_ref = store.store(payload, mime_type="text/plain", graph_id="graph_rotation")
    assert store.load(raw_ref, verify=True) == payload

    old_fingerprint = master_key_fingerprint(bytes.fromhex(old_key))

    monkeypatch.setenv("FAIM_MASTER_KEY", new_key)
    monkeypatch.setenv("FAIM_MASTER_KEY_PREVIOUS_JSON", f'["{old_key}"]')

    manager = TenantDEKManager(session_factory=session_factory.create)
    rotation = manager.rotate_tenant_dek(tenant_id)
    assert rotation["status"] == "rewrapped"
    assert rotation["master_key_fingerprint"] == master_key_fingerprint(
        bytes.fromhex(new_key)
    )
    assert rotation["source_master_key_fingerprint"] == old_fingerprint

    with session_factory.session() as session:
        row = (
            session.query(TenantCryptoKey)
            .filter(TenantCryptoKey.tenant_id == tenant_id)
            .first()
        )
        assert row is not None
        assert row.master_key_fingerprint == master_key_fingerprint(
            bytes.fromhex(new_key)
        )

    monkeypatch.delenv("FAIM_MASTER_KEY_PREVIOUS_JSON", raising=False)
    fresh_cipher = EnvelopeCipher(tenant_id=tenant_id, session_factory=session_factory.create)
    fresh_store = EncryptedRawStore(inner=inner, cipher=fresh_cipher, graph_id=tenant_id)
    assert fresh_store.load(raw_ref, verify=True) == payload

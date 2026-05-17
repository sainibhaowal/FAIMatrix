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

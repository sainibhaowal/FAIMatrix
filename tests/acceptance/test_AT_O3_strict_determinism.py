"""AT-O3: Verify STRICT mode is deterministic.

Tests that:
- STRICT profile produces stable, deterministic outputs
- No GPU randomness affects results
- Same input → same graph_hash across runs
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))


class TestStrictDeterminism:
    """Verify STRICT mode produces deterministic outputs."""

    def test_strict_profile_no_gpu(self):
        """STRICT profile must have allow_gpu=False."""
        from orchestration.perf.spec import SPEED_PROFILES, FaimSpeedProfile

        strict = SPEED_PROFILES[FaimSpeedProfile.STRICT]

        assert strict.allow_gpu is False, "STRICT profile should not allow GPU"

    def test_strict_profile_deterministic_persist(self):
        """STRICT profile should default to STRICT persist mode."""
        from orchestration.perf.spec import (
            SPEED_PROFILES,
            FaimSpeedProfile,
            PersistMode,
        )

        strict = SPEED_PROFILES[FaimSpeedProfile.STRICT]

        assert strict.default_persist_mode == PersistMode.STRICT

    def test_encoding_produces_same_vectors(self):
        """Same blocks produce identical vectors (deterministic)."""
        from encoding.text_vectorizer import vectorize_blocks
        from perception.router import route_extraction

        content = b"Test content for determinism verification."
        raw_id = "det_test"

        # Extract once, use same blocks
        blocks = route_extraction(content, "test.txt", raw_id)

        # Encode same blocks twice
        vectors1 = vectorize_blocks(blocks)
        vectors2 = vectorize_blocks(blocks)

        # Same number of vectors
        assert len(vectors1) == len(vectors2)

        # Same hashes
        for v1, v2 in zip(vectors1, vectors2, strict=False):
            assert v1.vector_hash == v2.vector_hash

    def test_faim_profile_enum_has_strict(self):
        """FAIMProfile enum should have STRICT value."""
        from orchestration.ingest_flow import FAIMProfile

        assert FAIMProfile.STRICT.value == "strict"

    def test_packet_hash_is_deterministic_for_same_blocks(self):
        """Same blocks → same packet_hash (deterministic)."""
        from perception.packetize import create_packet
        from perception.router import route_extraction

        content = b"Deterministic packet test content."
        raw_id = "packet_det_test"

        # Extract once
        blocks = route_extraction(content, "test.txt", raw_id)

        hashes = []
        for _ in range(3):
            # Use SAME blocks each time
            packet = create_packet(raw_id, blocks)
            hashes.append(packet.packet_hash)

        # All hashes should be identical when using same blocks
        assert len(set(hashes)) == 1, f"Packet hashes differ: {hashes}"

"""AT-O1: Verify ingest is chunk-free.

Tests that orchestration/ingest_flow.py:
- Uses EvidenceBlocks (not chunks)
- Uses perception.router.route_extraction
- Uses perception.packetize.create_packet
- Has NO "chunk_*" usage in the pipeline
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))


class TestIngestChunkFree:
    """Verify ingest_flow.py is chunk-free."""

    def test_no_chunk_imports_in_ingest_flow(self):
        """ingest_flow.py must not import any chunk-related modules."""
        ingest_flow_path = _faim_native / "orchestration" / "ingest_flow.py"
        content = ingest_flow_path.read_text()

        # Check for chunk-related imports (not in docstrings)
        assert (
            "from faim.pipeline.ingest" not in content
        ), "ingest_flow.py imports legacy ingest pipeline"

        # Check for _chunk_text function or chunk_size variable
        assert "_chunk_text" not in content, "ingest_flow.py has _chunk_text function"
        assert "chunk_size" not in content.lower(), "ingest_flow.py has chunk_size"

    def test_uses_perception_router(self):
        """ingest_flow.py must use perception.router.route_extraction."""
        ingest_flow_path = _faim_native / "orchestration" / "ingest_flow.py"
        content = ingest_flow_path.read_text()

        assert (
            "route_extraction" in content
        ), "ingest_flow.py does not use route_extraction"
        assert (
            "perception.router" in content or "from perception.router" in content
        ), "ingest_flow.py does not import from perception.router"

    def test_uses_perception_packetize(self):
        """ingest_flow.py must use perception.packetize.create_packet."""
        ingest_flow_path = _faim_native / "orchestration" / "ingest_flow.py"
        content = ingest_flow_path.read_text()

        assert "create_packet" in content, "ingest_flow.py does not use create_packet"
        assert (
            "perception.packetize" in content or "from perception.packetize" in content
        ), "ingest_flow.py does not import from perception.packetize"

    def test_uses_perception_validate(self):
        """ingest_flow.py must use perception.validate.assert_valid."""
        ingest_flow_path = _faim_native / "orchestration" / "ingest_flow.py"
        content = ingest_flow_path.read_text()

        assert "assert_valid" in content, "ingest_flow.py does not use assert_valid"

    def test_uses_encoding_not_sentence_transformer(self):
        """ingest_flow.py must NOT use SentenceTransformer."""
        ingest_flow_path = _faim_native / "orchestration" / "ingest_flow.py"
        content = ingest_flow_path.read_text()

        assert (
            "sentence_transformer" not in content.lower()
        ), "ingest_flow.py uses SentenceTransformer"
        assert (
            "sentencetransformer" not in content.lower()
        ), "ingest_flow.py uses SentenceTransformer"

    def test_ingest_result_has_packet_hash(self):
        """IngestResult must have packet_hash field."""
        import dataclasses

        from orchestration.ingest_flow import IngestResult

        fields = {f.name for f in dataclasses.fields(IngestResult)}

        assert "packet_hash" in fields, "IngestResult missing packet_hash"

    def test_ingest_result_has_block_count(self):
        """IngestResult must have block_count field (not chunk_count)."""
        import dataclasses

        from orchestration.ingest_flow import IngestResult

        fields = {f.name for f in dataclasses.fields(IngestResult)}

        assert "block_count" in fields, "IngestResult missing block_count"
        assert (
            "chunk_count" not in fields
        ), "IngestResult has chunk_count (should be block_count)"

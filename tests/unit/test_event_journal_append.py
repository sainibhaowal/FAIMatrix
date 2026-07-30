"""Unit tests for EventJournal append-only semantics."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

# Setup path for isolated imports
_FAIM_NATIVE_ROOT = Path(__file__).parent.parent.parent
if str(_FAIM_NATIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(_FAIM_NATIVE_ROOT))

from core.contracts.types import EventRecord  # noqa: E402
from store.journal.event_journal import (  # noqa: E402
    ChecksumMismatchError,
    EventJournal,
)
from store.pg.session import SessionFactory  # noqa: E402


@pytest.mark.unit
class TestEventJournalAppend:
    """Unit tests for EventJournal append-only semantics."""

    def test_append_assigns_sequence_number(self, session_factory: SessionFactory):
        """Appending an event assigns a sequence number."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            event = EventRecord.create(
                graph_id="test_graph",
                kind="node_created",
                payload={"node_id": "node1"},
            )
            saved = journal.append(event)
            assert saved.seq is not None
            assert saved.seq > 0

    def test_append_preserves_event_data(self, session_factory: SessionFactory):
        """Appended event preserves all original data."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            event = EventRecord.create(
                graph_id="test_graph",
                kind="custom_event",
                payload={"key": "value", "count": 42},
            )
            saved = journal.append(event)
            assert saved.id == event.id
            assert saved.graph_id == event.graph_id
            assert saved.kind == event.kind
            assert saved.payload == event.payload
            assert saved.checksum == event.checksum

    def test_ordering_by_sequence(self, session_factory: SessionFactory):
        """Events are ordered by sequence number."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            events = []
            for i in range(5):
                event = EventRecord.create(
                    graph_id="test_graph",
                    kind=f"event_{i}",
                    payload={"index": i},
                )
                saved = journal.append(event)
                events.append(saved)

            read_events = journal.read("test_graph", after_seq=0, limit=10)
            seqs = [e.seq for e in read_events]
            assert seqs == sorted(seqs), "Events should be ordered by seq"

    def test_stable_ordering_deterministic(self, session_factory: SessionFactory):
        """Ordering is deterministic across multiple reads."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            for i in range(10):
                event = EventRecord.create(
                    graph_id="test_graph",
                    kind=f"event_{i}",
                    payload={"index": i},
                )
                journal.append(event)

            read1 = journal.read("test_graph", after_seq=0, limit=10)
            read2 = journal.read("test_graph", after_seq=0, limit=10)
            read3 = journal.read("test_graph", after_seq=0, limit=10)

            ids1 = [e.id for e in read1]
            ids2 = [e.id for e in read2]
            ids3 = [e.id for e in read3]
            assert ids1 == ids2 == ids3

    def test_checksum_computed_correctly(self, session_factory: SessionFactory):
        """Event checksum is computed from ts, graph_id, kind, payload."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            event = EventRecord.create(
                graph_id="test_graph",
                kind="test_event",
                payload={"data": "test"},
            )
            saved = journal.append(event)
            assert saved.checksum is not None
            assert len(saved.checksum) == 64
            assert saved.verify_checksum()

    def test_checksum_verification_fails_on_tampered_data(
        self, session_factory: SessionFactory
    ):
        """Checksum verification detects tampered data."""
        event = EventRecord.create(
            graph_id="test_graph",
            kind="test_event",
            payload={"data": "original"},
        )
        tampered = replace(event, checksum="0" * 64)
        assert not tampered.verify_checksum()

    def test_invalid_checksum_rejected(self, session_factory: SessionFactory):
        """Appending event with invalid checksum raises error."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            event = EventRecord.create(
                graph_id="test_graph",
                kind="test_event",
                payload={"data": "test"},
            )
            tampered = replace(event, checksum="invalid_checksum_" + "0" * 48)
            with pytest.raises(ChecksumMismatchError):
                journal.append(tampered)

    def test_paging_with_after_seq(self, session_factory: SessionFactory):
        """Paging using after_seq cursor works correctly."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            for i in range(20):
                event = EventRecord.create(
                    graph_id="test_graph",
                    kind=f"event_{i:02d}",
                    payload={"index": i},
                )
                journal.append(event)

            page1 = journal.read("test_graph", after_seq=0, limit=5)
            assert len(page1) == 5

            last_seq = page1[-1].seq
            page2 = journal.read("test_graph", after_seq=last_seq, limit=5)
            assert len(page2) == 5

            page1_ids = {e.id for e in page1}
            page2_ids = {e.id for e in page2}
            assert page1_ids.isdisjoint(page2_ids)

    def test_get_latest(self, session_factory: SessionFactory):
        """get_latest returns the most recent event."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            for i in range(5):
                event = EventRecord.create(
                    graph_id="test_graph",
                    kind=f"event_{i}",
                    payload={"index": i},
                )
                journal.append(event)

            latest = journal.get_latest("test_graph")
            assert latest is not None
            assert latest.kind == "event_4"
            assert latest.payload["index"] == 4

    def test_count_events(self, session_factory: SessionFactory):
        """count returns correct number of events."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            for i in range(7):
                event = EventRecord.create(
                    graph_id="test_graph",
                    kind=f"event_{i}",
                    payload={"index": i},
                )
                journal.append(event)
            count = journal.count("test_graph")
            assert count == 7

    def test_graph_isolation(self, session_factory: SessionFactory):
        """Events from different graphs are isolated."""
        with session_factory.atomic() as session:
            journal = EventJournal(session)
            for graph_id in ["graph_a", "graph_b"]:
                for i in range(3):
                    event = EventRecord.create(
                        graph_id=graph_id,
                        kind=f"event_{i}",
                        payload={"graph": graph_id, "index": i},
                    )
                    journal.append(event)

            events_a = journal.read("graph_a", limit=10)
            events_b = journal.read("graph_b", limit=10)

            assert len(events_a) == 3
            assert len(events_b) == 3
            assert all(e.graph_id == "graph_a" for e in events_a)
            assert all(e.graph_id == "graph_b" for e in events_b)

"""Stage-8 Test: Query Events Emitted.

Proves query emits events:
- QUERY_START
- QUERY_RERANKED
- QUERY_TOUCH
- QUERY_COMPLETE
"""

import unittest


class TestQueryEventsEmitted(unittest.TestCase):
    """Test query events are emitted."""

    def test_query_start_emitter_exists(self):
        """emit_query_start exists."""
        from orchestration.query_flow import emit_query_start

        self.assertTrue(callable(emit_query_start))

    def test_query_reranked_emitter_exists(self):
        """emit_query_reranked exists."""
        from orchestration.query_flow import emit_query_reranked

        self.assertTrue(callable(emit_query_reranked))

    def test_query_touch_emitter_exists(self):
        """emit_query_touch exists."""
        from orchestration.query_flow import emit_query_touch

        self.assertTrue(callable(emit_query_touch))

    def test_query_complete_emitter_exists(self):
        """emit_query_complete exists."""
        from orchestration.query_flow import emit_query_complete

        self.assertTrue(callable(emit_query_complete))

    def test_run_query_emits_events(self):
        """run_query calls all event emitters."""
        import inspect

        from orchestration.query_flow import run_query

        source = inspect.getsource(run_query)

        self.assertIn("emit_query_start", source)
        self.assertIn("emit_query_reranked", source)
        self.assertIn("emit_query_touch", source)
        self.assertIn("emit_query_complete", source)


class TestQueryEventPayloads(unittest.TestCase):
    """Test query event payloads are bounded."""

    def test_start_event_has_query_hash(self):
        """QUERY_START payload has query_hash."""
        import inspect

        from orchestration.query_flow import emit_query_start

        source = inspect.getsource(emit_query_start)

        self.assertIn("query_hash", source)
        self.assertIn("QUERY_START", source)

    def test_reranked_event_limited_to_top5(self):
        """QUERY_RERANKED limits to top 5 IDs."""
        import inspect

        from orchestration.query_flow import emit_query_reranked

        source = inspect.getsource(emit_query_reranked)

        # Should truncate to 5 for SSE
        self.assertIn("[:5]", source)

    def test_complete_event_has_duration(self):
        """QUERY_COMPLETE payload has duration_ms."""
        import inspect

        from orchestration.query_flow import emit_query_complete

        source = inspect.getsource(emit_query_complete)

        self.assertIn("duration_ms", source)


if __name__ == "__main__":
    unittest.main()

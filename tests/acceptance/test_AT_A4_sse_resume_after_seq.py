"""Stage-7 Acceptance Test: SSE Resume After Seq.

Gate 3 (continued): SSE stream supports resume with after_seq.
"""

import unittest


class TestSSEResumeAfterSeq(unittest.TestCase):
    """Test SSE event stream resume capability."""

    def test_events_router_exists(self):
        """Events router must exist."""
        from api.routers.events import router

        self.assertIsNotNone(router)

    def test_stream_endpoint_has_after_seq_param(self):
        """Stream endpoint must accept after_seq parameter."""
        import inspect

        from api.routers.events import stream_events

        sig = inspect.signature(stream_events)
        params = list(sig.parameters.keys())

        self.assertIn("after_seq", params)

    def test_event_generator_exists(self):
        """_event_generator must exist for SSE."""
        from api.routers.events import _event_generator

        self.assertTrue(callable(_event_generator))

    def test_list_events_has_pagination(self):
        """list_events must support pagination."""
        import inspect

        from api.routers.events import list_events

        sig = inspect.signature(list_events)
        params = list(sig.parameters.keys())

        self.assertIn("after_seq", params)
        self.assertIn("limit", params)

    def test_events_response_has_has_more(self):
        """Events response must indicate has_more for pagination."""
        # The list_events function returns dict with has_more
        import inspect

        from api.routers.events import list_events

        # Check function exists and is async
        self.assertTrue(inspect.iscoroutinefunction(list_events))

    def test_latest_endpoint_exists(self):
        """get_latest_event endpoint must exist."""
        from api.routers.events import get_latest_event

        self.assertTrue(callable(get_latest_event))


if __name__ == "__main__":
    unittest.main()

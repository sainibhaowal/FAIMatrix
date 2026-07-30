import time
from collections import deque
from threading import Lock


class ThroughputTracker:
    """
    Rolling window throughput tracker (synapses/sec).
    """

    def __init__(self, window_size_sec: float = 30.0):
        self._window_size = window_size_sec
        self._events = deque()  # (timestamp, count)
        self._lock = Lock()

    def record(self, count: int = 1):
        """Record processed events."""
        now = time.time()
        with self._lock:
            self._events.append((now, count))
            self._cleanup(now)

    def get_throughput(self) -> float:
        """Return average events per second in the window."""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if not self._events:
                return 0.0
            total_count = sum(c for _, c in self._events)
            # Duration is either the window size or time since first event
            duration = now - self._events[0][0]
            if duration <= 0:
                return float(total_count)
            # We use the full window size as denominator to be conservative
            # or the actual duration if shorter but window isn't full yet
            denom = min(duration, self._window_size)
            if denom < 0.1:  # avoid spikes on first click
                return float(total_count)
            return total_count / denom

    def _cleanup(self, now: float):
        """Remove events outside the window."""
        while self._events and self._events[0][0] < now - self._window_size:
            self._events.popleft()


# Singleton for engine-wide tracking
global_throughput = ThroughputTracker()

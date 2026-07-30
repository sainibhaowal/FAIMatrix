"""Performance layer status for FAIM-native.

P2 decision: keep this namespace isolated from the active ingest/query path.
It is treated as experimental/legacy until a dedicated integration program
defines contracts, tests, and rollout controls.
"""

PERF_LAYER_STATUS = "isolated_legacy"

__all__ = ["PERF_LAYER_STATUS"]

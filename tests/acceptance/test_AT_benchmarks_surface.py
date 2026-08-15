from __future__ import annotations

from typing import Set

from api.app import app
from fastapi.routing import (
    APIRoute,
    _IncludedRouter,  # noqa: PLC2701
)


def _api_paths(routes=None, prefix: str = "") -> Set[str]:
    """Flatten every registered route path, surviving FastAPI's router wrapping.

    Newer FastAPI versions expose included routers as ``_IncludedRouter``
    wrappers; the effective ``/api/v1`` prefix lives in their
    ``include_context.prefix`` and the inner ``APIRoute`` objects hold the
    remaining path suffix.
    """
    if routes is None:
        routes = app.routes
    paths: Set[str] = set()
    for route in routes:
        if isinstance(route, _IncludedRouter):
            sub_prefix = prefix + (route.include_context.prefix or "")
            paths |= _api_paths(route.original_router.routes, sub_prefix)
        elif isinstance(route, APIRoute):
            paths.add(prefix + route.path)
    return paths


def test_benchmark_router_registered():
    paths = _api_paths()
    assert "/api/v1/benchmarks/{graph_id}/run" in paths
    assert "/api/v1/benchmarks/{graph_id}/latest" in paths
    assert "/api/v1/benchmarks/{graph_id}/series" in paths
    assert "/api/v1/benchmarks/{graph_id}/runs" in paths
    assert "/api/v1/benchmarks/{graph_id}/runs/{run_id}" in paths


def test_faim_bench_publication_routes_registered():
    paths = _api_paths()
    assert "/api/v1/faim-bench/{graph_id}/publication/run" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/latest" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/leaderboard" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/spec" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/repro" in paths
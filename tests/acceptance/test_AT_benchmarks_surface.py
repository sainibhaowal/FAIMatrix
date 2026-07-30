from __future__ import annotations

from api.app import app


def test_benchmark_router_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/benchmarks/{graph_id}/run" in paths
    assert "/api/v1/benchmarks/{graph_id}/latest" in paths
    assert "/api/v1/benchmarks/{graph_id}/series" in paths
    assert "/api/v1/benchmarks/{graph_id}/runs" in paths
    assert "/api/v1/benchmarks/{graph_id}/runs/{run_id}" in paths


def test_faim_bench_publication_routes_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/faim-bench/{graph_id}/publication/run" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/latest" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/leaderboard" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/spec" in paths
    assert "/api/v1/faim-bench/{graph_id}/publication/repro" in paths

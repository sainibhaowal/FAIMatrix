"""P2 tests: query cache wiring and index contract alignment."""

from __future__ import annotations

import inspect
from uuid import UUID


def test_recall_candidates_index_prefers_top_k_contract():
    """recall_candidates_index must accept top_k contract."""
    from core.query.query_engine import recall_candidates_index

    u1 = UUID("11111111-1111-1111-1111-111111111111")
    u2 = UUID("22222222-2222-2222-2222-222222222222")

    class _TopKIndex:
        def top_k(self, graph_id, query_vec, k=32):  # noqa: ANN001
            return [
                (str(u2), 0.8),
                ("not-a-uuid", 0.99),  # should be ignored
                (str(u1), 0.8),
            ]

    results = recall_candidates_index(
        index=_TopKIndex(),
        tenant_id="tenant_x",
        graph_id="graph_x",
        q_vec=(0.1, 0.2, 0.3),
        n=10,
    )

    assert [r[0] for r in results] == [u1, u2]
    assert [r[1] for r in results] == [0.8, 0.8]


def test_recall_candidates_index_supports_legacy_search_contract():
    """recall_candidates_index should remain backward compatible with search()."""
    from core.query.query_engine import recall_candidates_index

    u1 = UUID("33333333-3333-3333-3333-333333333333")

    class _SearchIndex:
        def search(self, tenant_id, graph_id, vector, k=32):  # noqa: ANN001
            return [{"id": str(u1), "score": 0.75}]

    results = recall_candidates_index(
        index=_SearchIndex(),
        tenant_id="tenant_y",
        graph_id="graph_y",
        q_vec=(0.4, 0.5, 0.6),
        n=10,
    )

    assert results == [(u1, 0.75)]


def test_query_flow_uses_cache_get_and_set():
    """run_query source should show cache integration wiring."""
    from orchestration.query_flow import run_query

    source = inspect.getsource(run_query)
    assert "cache.get(" in source
    assert "cache.set(" in source
    assert "graph_version=graph_version" in source

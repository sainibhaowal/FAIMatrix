from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from faim_native.core.operators.entity_linking import (
    build_domain_candidate_scores,
    resolve_query_links,
)


class _EdgeRepo:
    def __init__(self, edges):
        self.edges = edges

    def list_graph_neighbors(self, graph_id, node_ids, kinds=None, limit=1000):
        return list(self.edges)


def test_resolve_query_links_matches_surface_forms():
    node_id = uuid4()
    rows = [
        SimpleNamespace(
            surface_form="acme",
            canonical_form="entity:acme",
            kind="entity_alias",
            score=1.0,
            meta={"node_id": str(node_id)},
        )
    ]
    linked = resolve_query_links("acme revenue", rows)
    assert linked
    assert linked[0].node_id == node_id


def test_build_domain_candidate_scores_adds_fact_support():
    entity_id = uuid4()
    fact_id = uuid4()
    linked = [SimpleNamespace(node_id=entity_id, kind="entity_alias", score=1.0)]
    edges = [SimpleNamespace(src_node_id=entity_id, dst_node_id=fact_id, kind="entity_relation", weight=int(0.9 * 1e9))]
    candidates, scores = build_domain_candidate_scores(
        edge_repo=_EdgeRepo(edges),
        graph_id="g",
        linked_terms=linked,
    )
    assert fact_id in candidates
    assert scores[fact_id]["fact_support"] > 0.0

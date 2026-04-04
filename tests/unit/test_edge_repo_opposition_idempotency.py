"""Unit tests: opposition edge writes are idempotent and conflict-safe."""

from __future__ import annotations

from uuid import uuid4

from store.pg.repos.edge_repo import EdgeRepo


def test_add_opposition_edge_is_idempotent_for_same_pair(session_factory):
    tenant_id = "tenant_edge_idem"
    graph_id = "graph_edge_idem"
    a_id = uuid4()
    b_id = uuid4()

    with session_factory.session() as session:
        repo = EdgeRepo(session, tenant_id=tenant_id)

        first_edge_id = repo.add_opposition_edge(
            graph_id=graph_id,
            a_id=a_id,
            b_id=b_id,
            weight=0.97,
            meta={"run": 1, "reason": "first"},
        )
        second_edge_id = repo.add_opposition_edge(
            graph_id=graph_id,
            a_id=a_id,
            b_id=b_id,
            weight=0.99,
            meta={"run": 2, "reason": "second"},
        )
        session.commit()

        # Upsert behavior keeps a single logical edge for the pair.
        assert str(first_edge_id) == str(second_edge_id)

        edges = repo.list_opposition_edges(graph_id=graph_id, limit=10)
        assert len(edges) == 1
        edge = edges[0]
        assert int(edge.weight) == int(0.99 * 1e9)
        assert (edge.meta or {}).get("run") == 2


def test_add_opposition_edge_is_order_invariant(session_factory):
    tenant_id = "tenant_edge_order"
    graph_id = "graph_edge_order"
    a_id = uuid4()
    b_id = uuid4()

    with session_factory.session() as session:
        repo = EdgeRepo(session, tenant_id=tenant_id)

        first_edge_id = repo.add_opposition_edge(
            graph_id=graph_id,
            a_id=a_id,
            b_id=b_id,
            weight=0.96,
            meta={"run": "ab"},
        )
        second_edge_id = repo.add_opposition_edge(
            graph_id=graph_id,
            a_id=b_id,
            b_id=a_id,
            weight=0.96,
            meta={"run": "ba"},
        )
        session.commit()

        assert str(first_edge_id) == str(second_edge_id)

        edges = repo.list_opposition_edges(graph_id=graph_id, limit=10)
        assert len(edges) == 1
        edge = edges[0]
        assert edge.src_node_id in {a_id, b_id}
        assert edge.dst_node_id in {a_id, b_id}
        assert edge.src_node_id != edge.dst_node_id

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.domain.intelligence import (
    build_domain_graph,
    build_domain_overview,
    list_domain_terms,
)
from faim_native.store.pg.models_faim import (
    EdgeModel,
    GraphDomainLexiconModel,
    GraphKBSourceModel,
    GraphVersionModel,
    NodeModel,
    create_all_tables,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_domain_intelligence_surfaces_overview_terms_and_graph():
    session = _session()
    tenant_id = "tenant_domain_intelligence"
    graph_id = "graph-domain-intelligence"
    now = datetime.now(timezone.utc)

    linked_node_id = uuid4()
    other_node_id = uuid4()
    edge_id = uuid4()

    session.add(
        GraphVersionModel(
            tenant_id=tenant_id,
            graph_id=graph_id,
            version=7,
            reason="domain_profile_rebuild",
            updated_at=now,
        )
    )
    session.add(
        NodeModel(
            node_id=linked_node_id,
            tenant_id=tenant_id,
            graph_id=graph_id,
            kind="entity",
            vector_hash="vh-1",
            anchor_json={"text": "EBITDA margin expanded in 2026"},
            v_native=[],
            residual=0,
            level=1,
            touch_count=3,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        NodeModel(
            node_id=other_node_id,
            tenant_id=tenant_id,
            graph_id=graph_id,
            kind="fact",
            vector_hash="vh-2",
            anchor_json={"text": "Revenue reached 10M"},
            v_native=[],
            residual=0,
            level=1,
            touch_count=1,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        EdgeModel(
            edge_id=edge_id,
            tenant_id=tenant_id,
            graph_id=graph_id,
            src_node_id=linked_node_id,
            dst_node_id=other_node_id,
            kind="entity_relation",
            weight=int(0.82 * 1e9),
            meta={"source": "autonomous_domain"},
            created_at=now,
        )
    )
    session.add_all(
        [
            GraphDomainLexiconModel(
                tenant_id=tenant_id,
                graph_id=graph_id,
                surface_form="ebitda margin",
                canonical_form="ebitda margin",
                kind="domain_term",
                domain_pack="finance",
                support_count=6,
                score=0.91,
                meta={"node_id": str(linked_node_id)},
                updated_at=now,
            ),
            GraphDomainLexiconModel(
                tenant_id=tenant_id,
                graph_id=graph_id,
                surface_form="api latency",
                canonical_form="api latency",
                kind="domain_term",
                domain_pack="software",
                support_count=4,
                score=0.73,
                meta={},
                updated_at=now,
            ),
            GraphDomainLexiconModel(
                tenant_id=tenant_id,
                graph_id=graph_id,
                surface_form="revenue",
                canonical_form="revenue",
                kind="entity_alias",
                domain_pack="finance",
                support_count=5,
                score=0.88,
                meta={"node_id": str(other_node_id)},
                updated_at=now,
            ),
            GraphDomainLexiconModel(
                tenant_id=tenant_id,
                graph_id=graph_id,
                surface_form="api latency",
                canonical_form="api latency",
                kind="concept_bundle",
                domain_pack="software",
                support_count=5,
                score=0.89,
                meta={
                    "bundle_key": "bundle:software:test",
                    "bundle_members": [
                        "api latency",
                        "application programming interface latency",
                    ]
                },
                updated_at=now,
            ),
            GraphKBSourceModel(
                tenant_id=tenant_id,
                graph_id=graph_id,
                source_id="src-1",
                source_kind="autonomous_domain",
                source_hash="hash-1",
                meta={"title": "Finance upload"},
                updated_at=now,
            ),
        ]
    )
    session.commit()

    overview = build_domain_overview(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        limit=8,
    )
    assert overview["graph_version"] == 7
    assert overview["lexicon_total"] == 4
    assert overview["source_total"] == 1
    assert overview["linked_total"] >= 1
    assert "finance" in overview["detected_packs"]
    assert overview["pack_strengths"]
    assert overview["top_terms"]

    terms = list_domain_terms(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        q="ebitda",
        limit=10,
    )
    assert terms["total"] == 1
    assert terms["items"][0]["surface_form"] == "ebitda margin"

    graph = build_domain_graph(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        limit=10,
    )
    assert graph["terms_sampled"] == 4
    assert any(node["type"] == "pack" for node in graph["nodes"])
    assert any(node["type"] == "bundle" for node in graph["nodes"])
    assert any(node["type"] == "graph" for node in graph["nodes"])
    assert any(edge["kind"] == "graph_link" for edge in graph["edges"])
    assert any(edge["kind"] == "bundle_member" for edge in graph["edges"])
    assert any(edge["kind"] == "entity_relation" for edge in graph["edges"])

    session.close()

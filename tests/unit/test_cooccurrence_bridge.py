from __future__ import annotations

from unittest.mock import patch

from lexical.cooccurrence_bridge import (
    build_ppmi_cooccurrence_bridges,
    extract_concept_terms,
    run_cooccurrence_bridge_learning,
)
from lexical.semantic_registry import resolve_semantic_registry_expansions
from orchestration.query_flow import _domain_weighted_expansions
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store.pg.models_faim import Base, NodeRepresentationV2Model
from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo
from store.pg.repos.graph_version_repo import GraphVersionRepo
from uuid import uuid4


def _make_memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_extract_concept_terms_filters_stopwords_and_builds_bigrams():
    terms = extract_concept_terms("My car won't start, please check 123 battery!")
    assert "car" in terms
    assert "won't" in terms
    assert "start" in terms
    assert "battery" in terms
    assert "won't start" in terms
    assert "my" not in terms
    assert "123" not in terms


def test_second_order_ppmi_bridges_zero_word_overlap_paraphrases():
    docs = [
        "car won't start check battery",
        "ignition battery failure troubleshooting",
        "vehicle battery terminal corrosion check",
    ]
    rows = build_ppmi_cooccurrence_bridges(
        docs,
        min_similarity=0.15,
        max_bridges_per_term=12,
        max_total_bridges=500,
    )
    pairs = {(r["surface_form"], r["canonical_form"]): r for r in rows}
    assert ("won't start", "ignition") in pairs
    bridge = pairs[("won't start", "ignition")]
    assert bridge["kind"] == "cooccurrence_bridge"
    assert bridge["meta"]["order"] == 2
    assert "battery" in bridge["meta"]["bridges"]
    assert bridge["score"] >= 0.45


def test_end_to_end_db_learning_and_query_expansion():
    session = _make_memory_session()
    tenant_id = "tenant-ppmi"
    graph_id = "graph-ppmi"
    docs = [
        "car won't start check battery",
        "ignition battery failure troubleshooting",
        "vehicle battery terminal corrosion check",
    ]
    for idx, text in enumerate(docs):
        session.add(
            NodeRepresentationV2Model(
                node_id=uuid4(),
                tenant_id=tenant_id,
                graph_id=graph_id,
                repr_hash=f"h{idx}",
                normalized_text=text,
            )
        )
    session.commit()

    res = run_cooccurrence_bridge_learning(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        min_similarity=0.15,
        max_bridges_per_term=12,
    )
    session.commit()

    assert res.status == "completed"
    assert res.documents_scanned == 3
    assert res.bridges_persisted > 0
    assert res.graph_version == 1

    domain_repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
    domain_rows = domain_repo.list_lexicon_entries(graph_id)
    domain_map = domain_repo.get_domain_map(graph_id)

    assert "ignition" in domain_map.get("won't start", ())
    weighted = _domain_weighted_expansions("won't start", domain_rows)
    expanded_terms = {item.term for item in weighted}
    assert "ignition" in expanded_terms

    reg_expansions, _info = resolve_semantic_registry_expansions(
        query_text="won't start",
        domain_map=domain_map,
    )
    assert any(item.term == "ignition" for item in reg_expansions)


def test_multi_domain_scientific_corpus_bridges_and_caps():
    docs = [
        "myocardial infarction causes elevated coronary artery pressure",
        "cardiac troponin biomarker indicates coronary artery damage",
        "acute coronary artery blockage requires stent intervention",
    ]
    rows = build_ppmi_cooccurrence_bridges(
        docs,
        min_similarity=0.15,
        max_bridges_per_term=12,
        max_total_bridges=500,
    )
    assert len(rows) <= 500
    pairs = {(r["surface_form"], r["canonical_form"]) for r in rows}
    assert ("myocardial infarction", "cardiac troponin") in pairs or (
        "myocardial",
        "troponin",
    ) in pairs
    capped = build_ppmi_cooccurrence_bridges(
        docs,
        min_similarity=0.15,
        max_bridges_per_term=2,
        max_total_bridges=10,
    )
    assert len(capped) <= 10


def test_cooccurrence_bridge_edge_cases(monkeypatch):
    assert build_ppmi_cooccurrence_bridges([]) == []
    assert build_ppmi_cooccurrence_bridges(["single document only"]) == []

    res_no_sess = run_cooccurrence_bridge_learning(
        session=None, tenant_id="t", graph_id="g"
    )
    assert res_no_sess.status == "skipped"
    assert res_no_sess.reason == "no_session"

    monkeypatch.setenv("FAIM_COOCCURRENCE_BRIDGE_ENABLED", "false")
    res_disabled = run_cooccurrence_bridge_learning(
        session=object(), tenant_id="t", graph_id="g"
    )
    assert res_disabled.status == "skipped"
    assert res_disabled.reason == "cooccurrence_bridge_disabled"


def test_domain_autonomy_invokes_cooccurrence_bridge_learning():
    from orchestration.domain_autonomy import run_domain_autonomy_now

    with (
        patch(
            "orchestration.domain_profile_rebuild.run_domain_profile_rebuild",
            return_value={"ok": True},
        ),
        patch(
            "lexical.cooccurrence_bridge.run_cooccurrence_bridge_learning"
        ) as mock_learn,
    ):
        out = run_domain_autonomy_now(
            session="sess",
            tenant_id="t1",
            graph_id="g1",
            raw_repo=None,
            storage_file_repo=None,
            raw_store=None,
            node_repo=None,
            gv_repo=None,
        )

    assert out == {"ok": True}
    mock_learn.assert_called_once_with(
        session="sess", tenant_id="t1", graph_id="g1"
    )

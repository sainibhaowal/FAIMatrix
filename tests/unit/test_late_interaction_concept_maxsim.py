from __future__ import annotations

from core.query.late_interaction_native import (
    _build_query_units,
    build_query_concept_neighbors,
    score_late_interaction_native,
)
from encoding.representation_v2 import build_query_representation_v2


def test_concept_expanded_maxsim_scores_zero_overlap_higher_than_unrelated():
    q_repr = build_query_representation_v2("alpha_symptom")
    doc_concept = build_query_representation_v2("beta_diagnosis mechanism")
    doc_unrelated = build_query_representation_v2("gamma_music symphony")

    q_units = _build_query_units(q_repr)
    concept_neighbors = build_query_concept_neighbors(
        q_units,
        max_hops=1,
        decay=0.45,
        extra_graph={"alpha_symptom": [("beta_diagnosis", "Causes", 0.85)]},
        use_conceptnet=False,
    )
    assert "alpha_symptom" in concept_neighbors

    s_concept = score_late_interaction_native(
        query_repr=q_repr,
        doc_repr=doc_concept,
        precomputed_query_units=q_units,
        concept_neighbors=concept_neighbors,
    )
    s_unrelated = score_late_interaction_native(
        query_repr=q_repr,
        doc_repr=doc_unrelated,
        precomputed_query_units=q_units,
        concept_neighbors=concept_neighbors,
    )
    assert s_concept.total > s_unrelated.total
    assert s_concept.components["token_maxsim"] > 0.0


def test_exact_match_always_strictly_outranks_concept_expanded_match():
    q_repr = build_query_representation_v2("alpha_symptom")
    doc_exact = build_query_representation_v2("alpha_symptom details")
    doc_concept = build_query_representation_v2("beta_diagnosis details")

    q_units = _build_query_units(q_repr)
    concept_neighbors = build_query_concept_neighbors(
        q_units,
        max_hops=1,
        decay=0.45,
        extra_graph={"alpha_symptom": [("beta_diagnosis", "Causes", 0.95)]},
        use_conceptnet=False,
    )

    s_exact = score_late_interaction_native(
        query_repr=q_repr,
        doc_repr=doc_exact,
        precomputed_query_units=q_units,
        concept_neighbors=concept_neighbors,
    )
    s_concept = score_late_interaction_native(
        query_repr=q_repr,
        doc_repr=doc_concept,
        precomputed_query_units=q_units,
        concept_neighbors=concept_neighbors,
    )
    assert s_exact.components["token_maxsim"] > s_concept.components["token_maxsim"]
    assert s_exact.total > s_concept.total


def test_build_query_concept_neighbors_respects_env_disable_and_decay_cap(monkeypatch):
    q_repr = build_query_representation_v2("alpha_symptom")
    q_units = _build_query_units(q_repr)

    neighbors = build_query_concept_neighbors(
        q_units,
        max_hops=1,
        decay=0.45,
        extra_graph={"alpha_symptom": [("beta_diagnosis", "Synonym", 0.95)]},
        use_conceptnet=False,
    )
    for _term, weight in neighbors["alpha_symptom"]:
        assert weight <= 0.45

    monkeypatch.setenv("FAIM_MAXSIM_CONCEPT_EXPANSION", "false")
    assert (
        build_query_concept_neighbors(
            q_units,
            extra_graph={"alpha_symptom": [("beta_diagnosis", "Synonym", 0.95)]},
            use_conceptnet=False,
        )
        == {}
    )

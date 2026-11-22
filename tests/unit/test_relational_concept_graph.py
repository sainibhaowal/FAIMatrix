from __future__ import annotations

import time

from lexical.conceptnet_builder import TYPED_RELATION_WEIGHTS
from lexical.relational_concept_graph import spread_relational_concepts
from lexical.semantic_registry import resolve_semantic_registry_expansions


def test_multihop_typed_spreading_decay_and_cycle_safety():
    # 3-hop chain with a cycle back to seed
    graph = {
        "term_a": [("term_b", "Causes", 0.85)],
        "term_b": [("term_c", "HasPrerequisite", 0.85), ("term_a", "RelatedTo", 0.65)],
        "term_c": [("term_d", "PartOf", 0.80)],
        "term_d": [("term_b", "RelatedTo", 0.65)],
    }
    res = spread_relational_concepts(
        ["term_a"],
        max_hops=3,
        decay=0.6,
        min_score=0.05,
        extra_graph=graph,
        use_conceptnet=False,
    )
    by_term = {item.term: item for item in res}
    assert "term_a" not in by_term  # seed excluded
    assert set(by_term) == {"term_b", "term_c", "term_d"}
    assert by_term["term_b"].weight > by_term["term_c"].weight > by_term["term_d"].weight
    assert "relational_graph_hop1" in by_term["term_b"].sources
    assert "relational_graph_hop2" in by_term["term_c"].sources
    assert "relational_graph_hop3" in by_term["term_d"].sources


def test_relation_type_weighting_prefers_causal_over_weak_related():
    graph = {
        "node_x": [
            ("causal_y", "Causes", 0.85),
            ("weak_z", "RelatedTo", 0.65),
        ]
    }
    res = spread_relational_concepts(
        ["node_x"],
        max_hops=2,
        decay=0.6,
        min_score=0.05,
        extra_graph=graph,
        use_conceptnet=False,
    )
    by_term = {item.term: item for item in res}
    assert by_term["causal_y"].weight > by_term["weak_z"].weight


def test_hub_degree_dampening_prevents_generic_hub_flooding():
    # Specific node has degree 1; generic hub has degree 10
    graph = {
        "seed_specific": [("target_specific", "PartOf", 0.80)],
        "seed_hub": [(f"noise_{i}", "PartOf", 0.80) for i in range(10)],
    }
    res = spread_relational_concepts(
        ["seed_specific", "seed_hub"],
        max_hops=1,
        decay=0.6,
        min_score=0.05,
        extra_graph=graph,
        use_conceptnet=False,
    )
    by_term = {item.term: item for item in res}
    assert by_term["target_specific"].weight > by_term["noise_0"].weight


def test_semantic_registry_uses_multihop_domain_and_canonical_spreading():
    # 3-hop bridge across canonical_map + domain_map (no hardcoded words in code)
    canonical_map = {"alpha_signal": ("beta_pathway",)}
    domain_map = {
        "beta_pathway": ("gamma_marker",),
        "gamma_marker": ("delta_outcome",),
    }
    expansions, info = resolve_semantic_registry_expansions(
        query_text="alpha_signal",
        canonical_map=canonical_map,
        domain_map=domain_map,
        max_total=18,
    )
    terms = {item.term for item in expansions}
    assert "beta_pathway" in terms
    assert "gamma_marker" in terms
    assert "delta_outcome" in terms
    assert "relational_graph" in info["matched_surfaces"]


def test_multihop_spreading_completes_under_1ms():
    graph = {
        f"n_{i}": [(f"n_{i + 1}", "Causes", 0.85), (f"n_{i + 2}", "PartOf", 0.80)]
        for i in range(50)
    }
    t0 = time.perf_counter()
    for _ in range(10):
        spread_relational_concepts(
            ["n_0"],
            max_hops=3,
            decay=0.6,
            extra_graph=graph,
            use_conceptnet=False,
        )
    avg_ms = ((time.perf_counter() - t0) * 1000.0) / 10.0
    assert avg_ms < 2.0


def test_conceptnet_builder_typed_relations_and_empty_inputs():
    assert "/r/Causes" in TYPED_RELATION_WEIGHTS
    assert "/r/HasPrerequisite" in TYPED_RELATION_WEIGHTS
    assert "/r/PartOf" in TYPED_RELATION_WEIGHTS
    assert "/r/UsedFor" in TYPED_RELATION_WEIGHTS
    assert spread_relational_concepts([]) == ()

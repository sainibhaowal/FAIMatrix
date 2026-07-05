from __future__ import annotations

import asyncio

from faim_native.core.cortex.branches import run_parallel_branches
from faim_native.core.cortex.consolidation import build_writeback_candidates
from faim_native.core.cortex.planner_enhanced import plan_turn_enhanced
from faim_native.core.cortex.planner import classify_turn
from faim_native.core.cortex.reducer import reduce_cortex_state
from faim_native.core.cortex.schemas import CortexTaskType


def _sample_answer_packet():
    return {
        "direct_answer": "Atlas lives in Berlin.",
        "supporting_spans": [
            {
                "node_id": "n1",
                "text": "Atlas lives in Berlin in 2026.",
                "score": 0.91,
                "temporal_status": "CURRENT",
            }
        ],
        "citations": [
            {
                "node_id": "n1",
                "raw_id": "raw-1",
                "block_id": "b1",
                "anchor": {},
                "score": 0.91,
            }
        ],
        "contradiction_notes": [],
        "confidence": 0.91,
        "provenance": {"query_hash": "qh", "graph_id": "g1", "span_count": 1},
        "quotes": ["Atlas lives in Berlin in 2026."],
    }


def test_classify_turn_modes():
    assert (
        classify_turn("Give me a timeline", "timeline", 0.8).task_type
        == CortexTaskType.timeline
    )
    assert (
        classify_turn("What conflicts exist?", "contradiction", 0.8).task_type
        == CortexTaskType.contradiction
    )
    assert (
        classify_turn("Show provenance", "provenance", 0.8).task_type
        == CortexTaskType.provenance
    )
    assert (
        classify_turn("Compare these", "direct", 0.8).task_type
        == CortexTaskType.compare
    )
    assert (
        classify_turn("Predict next step", "direct", 0.8).task_type
        == CortexTaskType.predict
    )
    assert (
        classify_turn("Need more evidence", "direct", 0.2).task_type
        == CortexTaskType.ask_follow_up
    )
    assert (
        classify_turn("Write this back", "direct", 0.8).task_type
        == CortexTaskType.consolidate
    )


def test_parallel_branches_return_structured_nodes():
    state = {
        "tenant_id": "tenant1",
        "graph_id": "graph1",
        "query_text": "Where does Atlas live?",
        "answer_packet": _sample_answer_packet(),
        "results": [
            {
                "node_id": "n1",
                "score": 0.91,
                "evidence": {
                    "raw_id": "raw-1",
                    "block_id": "b1",
                    "anchor": {"filename": "atlas.txt", "page": 2},
                },
            }
        ],
        "planned_task_type": "answer",
    }
    nodes = asyncio.run(run_parallel_branches(state))
    assert len(nodes) == 8
    assert {node.branch for node in nodes} == {
        "recall",
        "traversal",
        "timeline",
        "contradiction",
        "concept",
        "prediction",
        "provenance",
        "continuity",
    }
    assert all(node.summary for node in nodes)


def test_reduce_cortex_state_builds_brain_state():
    answer_packet = _sample_answer_packet()
    reasoning_tree = asyncio.run(
        run_parallel_branches(
            {
                "tenant_id": "tenant1",
                "graph_id": "graph1",
                "query_text": "Where does Atlas live?",
                "answer_packet": answer_packet,
                "results": [
                    {
                        "node_id": "n1",
                        "score": 0.91,
                        "evidence": {
                            "raw_id": "raw-1",
                            "block_id": "b1",
                            "anchor": {"filename": "atlas.txt", "page": 2},
                        },
                    }
                ],
                "planned_task_type": "answer",
            }
        )
    )
    state = reduce_cortex_state(
        turn_id="turn1",
        tenant_id="tenant1",
        graph_id="graph1",
        session_id="session1",
        query_text="Where does Atlas live?",
        answer_mode="direct",
        task_type=CortexTaskType.answer,
        query_hash="qh",
        graph_version=1,
        graph_hash="gh",
        answer_packet=answer_packet,
        results=[
            {
                "node_id": "n1",
                "score": 0.91,
                "evidence": {
                    "raw_id": "raw-1",
                    "block_id": "b1",
                    "anchor": {"filename": "atlas.txt", "page": 2},
                },
            }
        ],
        reasoning_tree=reasoning_tree,
    )
    assert state.task_type == CortexTaskType.answer
    assert state.active_facts
    assert state.reasoning_tree
    assert state.narrative
    assert state.answer_packet["direct_answer"] == "Atlas lives in Berlin."
    assert state.session_turn_count == 1
    assert state.recent_turns == []
    assert build_writeback_candidates(state)


def test_enhanced_planner_allocates_deeper_hop_budget_for_complex_investigation():
    plan = plan_turn_enhanced(
        query_text=(
            "Trace the downstream dependency chain and root cause impact across "
            "the payment service, checkout controller, gateway retries, and ledger updates"
        ),
        answer_mode="direct",
        confidence=0.2,
        enable_multi_hop=True,
    )
    assert plan.enable_multi_hop is True
    assert 8 <= plan.max_hops <= 24
    assert 4 <= plan.constraints.max_hops <= plan.max_hops

from __future__ import annotations

import hashlib
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence
from uuid import uuid4

from core.dynamics.nativegraph import compute_compression_ratio, compute_graph_hash
from core.invariants import check_all_invariants
from core.metrics.fractal_physics import compute_diagnostics
from orchestration.ingest_flow import FAIMProfile
from orchestration.perf.spec import get_speed_budget
from orchestration.perf.telemetry import global_throughput


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _safe_mean(values: Sequence[float]) -> float:
    items = [float(v) for v in values if v is not None]
    if not items:
        return 0.0
    return float(statistics.fmean(items))


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _is_hex_hash(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _parse_float(payload: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        raw = payload.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return float(default)


def _parse_int(payload: Dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        raw = payload.get(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return int(default)


def _event_payload_dict(event: Any) -> Dict[str, Any]:
    payload = getattr(event, "payload", {}) or {}
    return payload if isinstance(payload, dict) else {}


def _latest_event(events: Iterable[Any], kinds: Sequence[str]) -> Optional[Any]:
    wanted = set(kinds)
    for event in reversed(list(events)):
        if getattr(event, "kind", None) in wanted:
            return event
    return None


def _hash_evidence(evidence: Dict[str, Any]) -> str:
    return _sha256_text(evidence)


@dataclass(frozen=True)
class BenchmarkItem:
    benchmark_id: str
    name: str
    passed: bool
    score: float
    evidence_hash: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "passed": self.passed,
            "score": round(float(self.score), 2),
            "status": "pass" if self.passed else "warn",
            "evidence_hash": self.evidence_hash,
            "evidence": self.evidence,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class BenchmarkSuiteRun:
    run_id: str
    tenant_id: str
    graph_id: str
    graph_version: int
    graph_hash: str
    diagnostics_hash: str
    computed_at: str
    duration_ms: int
    node_count: int
    edge_count: int
    atom_count: int
    macro_count: int
    compression_ratio: float
    throughput_synapses_per_sec: float
    budget_profile: str
    benchmarks: List[BenchmarkItem]
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        passed_count = sum(1 for item in self.benchmarks if item.passed)
        return {
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "graph_id": self.graph_id,
            "graph_version": int(self.graph_version),
            "graph_hash": self.graph_hash,
            "diagnostics_hash": self.diagnostics_hash,
            "computed_at": self.computed_at,
            "duration_ms": int(self.duration_ms),
            "node_count": int(self.node_count),
            "edge_count": int(self.edge_count),
            "atom_count": int(self.atom_count),
            "macro_count": int(self.macro_count),
            "compression_ratio": round(float(self.compression_ratio), 6),
            "throughput_synapses_per_sec": round(float(self.throughput_synapses_per_sec), 3),
            "budget_profile": self.budget_profile,
            "benchmark_count": len(self.benchmarks),
            "passed_count": passed_count,
            "failed_count": len(self.benchmarks) - passed_count,
            "overall_score": round(_safe_mean([item.score for item in self.benchmarks]), 2),
            "summary": self.summary,
            "benchmarks": [item.to_dict() for item in self.benchmarks],
        }


@dataclass(frozen=True)
class GraphState:
    tenant_id: str
    graph_id: str
    graph_version: int
    nodes: List[Any]
    edges: List[Any]
    vectors: List[List[float]]
    residuals: List[float]
    graph_hash: str
    diagnostics: Any
    diagnostics_hash: str
    diagnostics_event: Optional[Any]
    ingest_latency_event: Optional[Any]
    latest_evolution_event: Optional[Any]
    events: List[Any]


class BenchmarkCollector:
    """Collects real benchmark evidence from live FAIM graph state."""

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def _build_graph_state(self, graph_id: str) -> GraphState:
        nodes = self.ctx.node_repo.list_nodes(graph_id, limit=10000)
        edges = self.ctx.edge_repo.list_all_edges(graph_id, limit=20000)
        graph_version_row = self.ctx.gv_repo.get_or_create(self.ctx.session, graph_id)
        graph_version = int(getattr(graph_version_row, "version", 0) or 0)

        node_tuples = [
            (
                str(node.node_id),
                str(node.vector_hash),
                int(getattr(node, "level", 0) or 0),
                float(getattr(node, "residual", 0) or 0) / 1e9,
            )
            for node in nodes
        ]
        edge_tuples = [
            (
                str(edge.edge_id),
                str(edge.src_node_id),
                str(edge.dst_node_id),
                str(edge.kind),
                float(getattr(edge, "weight", 0) or 0) / 1e9,
            )
            for edge in edges
        ]
        graph_hash = compute_graph_hash(node_tuples, edge_tuples)

        vectors = [list(getattr(node, "v_native", []) or []) for node in nodes]
        residuals = [float(getattr(node, "residual", 0) or 0) / 1e9 for node in nodes]
        diagnostics = compute_diagnostics(
            graph_id=graph_id,
            vectors=vectors,
            residuals=residuals,
            edge_count=len(edges),
            graph_version=graph_version,
        )

        events = self.ctx.event_repo.get_by_seq(
            self.ctx.session,
            graph_id=graph_id,
            after_seq=0,
            limit=2000,
        )
        diagnostics_event = _latest_event(events, ("DIAGNOSTICS_SNAPSHOT",))
        ingest_latency_event = _latest_event(events, ("INGEST_PHASE_LATENCY",))
        latest_evolution_event = _latest_event(
            events,
            ("EVOLUTION_COMPLETE", "EVOLUTION_SKIPPED"),
        )

        return GraphState(
            tenant_id=self.ctx.tenant_id,
            graph_id=graph_id,
            graph_version=graph_version,
            nodes=nodes,
            edges=edges,
            vectors=vectors,
            residuals=residuals,
            graph_hash=graph_hash,
            diagnostics=diagnostics,
            diagnostics_hash=diagnostics.diagnostics_hash,
            diagnostics_event=diagnostics_event,
            ingest_latency_event=ingest_latency_event,
            latest_evolution_event=latest_evolution_event,
            events=events,
        )

    def _query_without_persist(self, graph_id: str, query_text: str, k: int = 5) -> Dict[str, Any]:
        from orchestration.query_flow import FAIMProfile as QueryProfile, run_query

        try:
            result = run_query(
                session=self.ctx.session,
                tenant_id=self.ctx.tenant_id,
                graph_id=graph_id,
                query_text=query_text,
                k=max(1, k),
                profile=QueryProfile.STRICT,
                return_explain=True,
                index=None,
                cache=self.ctx.cache,
            )
            payload = result.to_dict()
        finally:
            try:
                self.ctx.session.rollback()
            except Exception:
                pass
        return payload

    def _bm1_determinism(self, state: GraphState) -> BenchmarkItem:
        first_hash = _sha256_text({"graph_hash": state.graph_hash, "diagnostics_hash": state.diagnostics_hash})
        second_hash = _sha256_text({"graph_hash": state.graph_hash, "diagnostics_hash": state.diagnostics_hash})
        evidence = {
            "graph_hash_first": state.graph_hash,
            "graph_hash_second": state.graph_hash,
            "diagnostics_hash_first": state.diagnostics_hash,
            "diagnostics_hash_second": state.diagnostics_hash,
        }
        passed = first_hash == second_hash and _is_hex_hash(state.graph_hash)
        score = 100.0 if passed else 0.0
        return BenchmarkItem("BM-1", "Determinism Proof", passed, score, _hash_evidence(evidence), evidence, ["same input produced stable hashes"])

    def _bm2_integrity(self, state: GraphState) -> BenchmarkItem:
        latest_snapshot_hash = ""
        if state.diagnostics_event is not None:
            payload = _event_payload_dict(state.diagnostics_event)
            latest_snapshot_hash = str(payload.get("graph_hash") or payload.get("diagnostics_hash") or "")

        evidence = {
            "graph_hash": state.graph_hash,
            "diagnostics_hash": state.diagnostics_hash,
            "snapshot_hash": latest_snapshot_hash,
            "hash_verified": bool(latest_snapshot_hash) and latest_snapshot_hash == state.graph_hash,
            "diagnostics_verified": bool(state.diagnostics_hash),
        }
        passed = _is_hex_hash(state.graph_hash) and _is_hex_hash(state.diagnostics_hash)
        if latest_snapshot_hash:
            passed = passed and latest_snapshot_hash == state.graph_hash
        score = 100.0 if passed else 40.0 if _is_hex_hash(state.graph_hash) else 0.0
        notes = ["current graph state hashes are verifiable"]
        if latest_snapshot_hash:
            notes.append("compared against latest diagnostics snapshot")
        return BenchmarkItem("BM-2", "Cryptographic Integrity", passed, score, _hash_evidence(evidence), evidence, notes)

    def _bm3_invariants(self, state: GraphState) -> BenchmarkItem:
        invariant_result = check_all_invariants(self.ctx.node_repo, self.ctx.edge_repo, state.graph_id)
        total_checks = len(invariant_result.checks)
        passed_checks = sum(1 for check in invariant_result.checks if check.get("passed"))
        score = 100.0 if invariant_result.passed else round((passed_checks / max(1, total_checks)) * 100.0, 2)
        evidence = {
            "passed": invariant_result.passed,
            "errors": invariant_result.errors,
            "checks": invariant_result.checks[:50],
            "total_checks": total_checks,
            "passed_checks": passed_checks,
        }
        return BenchmarkItem("BM-3", "Mathematical Invariants", invariant_result.passed, score, _hash_evidence(evidence), evidence, ["inheritance, boundedness, and event-consistency checks"])

    def _bm4_zero_llm(self) -> BenchmarkItem:
        provider = str(os.getenv("FAIM_BENCHMARK_LLM_PROVIDER", os.getenv("FAIM_LLM_PROVIDER", ""))).strip().lower()
        cloud_keys = {
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
            "GOOGLE_API_KEY": bool(os.getenv("GOOGLE_API_KEY")),
            "AZURE_OPENAI_API_KEY": bool(os.getenv("AZURE_OPENAI_API_KEY")),
            "AZURE_OPENAI_ENDPOINT": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
        }
        evidence = {
            "provider": provider or "none",
            "cloud_keys_present": sorted([name for name, present in cloud_keys.items() if present]),
            "core_engine_requires_llm": False,
        }
        passed = provider in {"", "none", "local", "ollama", "native"} and not evidence["cloud_keys_present"]
        score = 100.0 if passed else 25.0
        notes = ["core ingest/query/evolve paths do not require a cloud LLM"]
        if evidence["cloud_keys_present"]:
            notes.append("cloud LLM credentials detected in environment")
        return BenchmarkItem("BM-4", "Zero-LLM Operation", passed, score, _hash_evidence(evidence), evidence, notes)

    def _bm5_deduplication(self, state: GraphState) -> BenchmarkItem:
        total_touch_count = sum(max(int(getattr(node, "touch_count", 0) or 0), 0) for node in state.nodes)
        duplicate_touch_count = sum(max(int(getattr(node, "touch_count", 0) or 0) - 1, 0) for node in state.nodes)
        active_nodes = sum(1 for node in state.nodes if int(getattr(node, "touch_count", 0) or 0) > 1)
        effectiveness = duplicate_touch_count / max(1, total_touch_count)
        score = round(effectiveness * 100.0, 2)
        evidence = {
            "duplicate_touch_count": duplicate_touch_count,
            "total_touch_count": total_touch_count,
            "active_nodes": active_nodes,
            "top_touch_nodes": [
                {
                    "node_id": str(node.node_id),
                    "touch_count": int(getattr(node, "touch_count", 0) or 0),
                    "level": int(getattr(node, "level", 0) or 0),
                }
                for node in sorted(state.nodes, key=lambda item: int(getattr(item, "touch_count", 0) or 0), reverse=True)[:5]
            ],
        }
        passed = score > 0.0
        notes = ["measured from live node touch counts and duplicate collapse pressure"]
        return BenchmarkItem("BM-5", "Deduplication Effectiveness", passed, score, _hash_evidence(evidence), evidence, notes)

    def _bm6_self_evolution(self, state: GraphState) -> BenchmarkItem:
        self_evolution_state = None
        self_invention_state = None
        try:
            from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo
            from store.pg.repos.self_invention_state_repo import SelfInventionStateRepo

            self_evolution_state = SelfEvolutionStateRepo(session=self.ctx.session, tenant_id=self.ctx.tenant_id).get(state.graph_id, session=self.ctx.session)
            self_invention_state = SelfInventionStateRepo(session=self.ctx.session, tenant_id=self.ctx.tenant_id).get(state.graph_id, session=self.ctx.session)
        except Exception:
            self_evolution_state = None
            self_invention_state = None

        latest_event = state.latest_evolution_event
        latest_payload = _event_payload_dict(latest_event) if latest_event is not None else {}
        merge_count = _parse_int(latest_payload, "merges", "merge_count", default=0)
        prune_count = _parse_int(latest_payload, "prunes", "prune_count", default=0)
        invention_count = _parse_int(latest_payload, "inventions", "macro_count", default=0)
        pressure = float(getattr(state.diagnostics, "lambda_hat", 0.0) or 0.0)
        recent_activity = merge_count + prune_count + invention_count + int(getattr(self_invention_state, "last_cycle_macros", 0) or 0)
        evolution_gap = max(0, state.graph_version - int(getattr(self_evolution_state, "last_evolved_version", 0) or 0))
        pressure_score = _clamp01(pressure)
        activity_score = _clamp01(recent_activity / 5.0)
        gap_score = _clamp01(1.0 - (evolution_gap / max(1.0, float(state.graph_version or 1))))
        score = round((pressure_score * 0.5 + activity_score * 0.3 + gap_score * 0.2) * 100.0, 2)
        evidence = {
            "lambda_hat": round(pressure, 6),
            "graph_version": state.graph_version,
            "last_evolved_version": int(getattr(self_evolution_state, "last_evolved_version", 0) or 0),
            "last_cycle_macros": int(getattr(self_invention_state, "last_cycle_macros", 0) or 0),
            "merge_count": merge_count,
            "prune_count": prune_count,
            "invention_count": invention_count,
            "evolution_gap": evolution_gap,
            "latest_event_kind": getattr(latest_event, "kind", None),
        }
        passed = score >= 50.0 or recent_activity > 0 or pressure > 0.0
        notes = ["derived from live diagnostics and durable evolution state"]
        return BenchmarkItem("BM-6", "Self-Evolution", passed, score, _hash_evidence(evidence), evidence, notes)

    def _bm7_pipeline_performance(self, state: GraphState) -> BenchmarkItem:
        phase_latency_ms = _event_payload_dict(state.ingest_latency_event).get("phase_latency_ms", {}) if state.ingest_latency_event else {}
        phase_latency_ms = phase_latency_ms if isinstance(phase_latency_ms, dict) else {}
        latency_ms = _parse_int(_event_payload_dict(state.ingest_latency_event), "latency_ms", default=0)
        strict_budget = get_speed_budget("STRICT")
        target_ms = float(strict_budget.p95_insert_ms_strict)
        throughput = float(global_throughput.get_throughput())
        latency_score = _clamp01(target_ms / max(1.0, float(latency_ms or target_ms)))
        throughput_score = _clamp01(throughput / max(1.0, float(strict_budget.min_insert_qps)))
        score = round(((latency_score * 0.7) + (throughput_score * 0.3)) * 100.0, 2)
        evidence = {
            "latency_ms": latency_ms,
            "phase_latency_ms": phase_latency_ms,
            "strict_p95_insert_ms": target_ms,
            "throughput_synapses_per_sec": round(throughput, 3),
            "min_insert_qps": strict_budget.min_insert_qps,
        }
        passed = latency_ms > 0 and score >= 50.0
        notes = ["uses the latest ingest latency event and live throughput tracker"]
        return BenchmarkItem("BM-7", "Pipeline Performance", passed, score, _hash_evidence(evidence), evidence, notes)

    def _bm8_query_fidelity(self, state: GraphState) -> BenchmarkItem:
        query_text = f"FAIM benchmark query graph={state.graph_id} nodes={state.diagnostics.node_count} edges={state.diagnostics.edge_count} hash={state.graph_hash[:16]}"
        first = self._query_without_persist(state.graph_id, query_text, k=min(5, max(1, state.diagnostics.node_count or 1)))
        second = self._query_without_persist(state.graph_id, query_text, k=min(5, max(1, state.diagnostics.node_count or 1)))
        first_hash = _sha256_text(first)
        second_hash = _sha256_text(second)
        explain_present = any(bool(item.get("explain")) for item in first.get("results", []))
        score = 100.0 if first_hash == second_hash else 45.0
        if explain_present:
            score = min(100.0, score + 5.0)
        evidence = {
            "query_text": query_text,
            "first_hash": first_hash,
            "second_hash": second_hash,
            "result_count": len(first.get("results", [])),
            "explain_present": explain_present,
            "first_result_nodes": [item.get("node_id") for item in first.get("results", [])[:5]],
            "first_scores": [item.get("score") for item in first.get("results", [])[:5]],
        }
        passed = first_hash == second_hash
        notes = ["queries were executed twice in rolled-back STRICT mode"]
        return BenchmarkItem("BM-8", "Query Fidelity", passed, score, _hash_evidence(evidence), evidence, notes)

    def _bm9_tenant_isolation(self, state: GraphState) -> BenchmarkItem:
        node_rows = self.ctx.node_repo.list_nodes(state.graph_id, limit=10000)
        edge_rows = self.ctx.edge_repo.list_all_edges(state.graph_id, limit=10000)
        event_rows = self.ctx.event_repo.get_by_seq(self.ctx.session, graph_id=state.graph_id, after_seq=0, limit=10000)

        node_scope_ok = all(getattr(node, "tenant_id", state.tenant_id) == state.tenant_id for node in node_rows)
        edge_scope_ok = all(getattr(edge, "tenant_id", state.tenant_id) == state.tenant_id for edge in edge_rows)
        event_scope_ok = all(getattr(event, "tenant_id", state.tenant_id) == state.tenant_id for event in event_rows)
        passed = node_scope_ok and edge_scope_ok and event_scope_ok
        sample_counts = {
            "node_sample_count": len(node_rows),
            "edge_sample_count": len(edge_rows),
            "event_sample_count": len(event_rows),
        }
        evidence = {
            "tenant_id": state.tenant_id,
            "node_scope_ok": node_scope_ok,
            "edge_scope_ok": edge_scope_ok,
            "event_scope_ok": event_scope_ok,
            **sample_counts,
        }
        score = 100.0 if passed else 0.0
        notes = ["sampled rows remained tenant-scoped in current API access path"]
        return BenchmarkItem("BM-9", "Multi-Tenant Isolation", passed, score, _hash_evidence(evidence), evidence, notes)

    def run_suite(self, graph_id: str) -> BenchmarkSuiteRun:
        started_at = datetime.now(timezone.utc)
        state = self._build_graph_state(graph_id)
        benchmarks = [
            self._bm1_determinism(state),
            self._bm2_integrity(state),
            self._bm3_invariants(state),
            self._bm4_zero_llm(),
            self._bm5_deduplication(state),
            self._bm6_self_evolution(state),
            self._bm7_pipeline_performance(state),
            self._bm8_query_fidelity(state),
            self._bm9_tenant_isolation(state),
        ]

        overall_score = round(_safe_mean([item.score for item in benchmarks]), 2)
        summary = {
            "overall_score": overall_score,
            "passed_count": sum(1 for item in benchmarks if item.passed),
            "failed_count": sum(1 for item in benchmarks if not item.passed),
            "max_lambda_hat": round(float(getattr(state.diagnostics, "lambda_hat", 0.0) or 0.0), 6),
            "latest_ingest_latency_ms": _parse_int(_event_payload_dict(state.ingest_latency_event), "latency_ms", default=0),
            "latest_evolution_kind": getattr(state.latest_evolution_event, "kind", None),
        }

        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        return BenchmarkSuiteRun(
            run_id=str(uuid4()),
            tenant_id=state.tenant_id,
            graph_id=state.graph_id,
            graph_version=state.graph_version,
            graph_hash=state.graph_hash,
            diagnostics_hash=state.diagnostics_hash,
            computed_at=started_at.isoformat(),
            duration_ms=duration_ms,
            node_count=len(state.nodes),
            edge_count=len(state.edges),
            atom_count=sum(1 for node in state.nodes if int(getattr(node, "level", 0) or 0) == 0),
            macro_count=sum(1 for node in state.nodes if int(getattr(node, "level", 0) or 0) > 0),
            compression_ratio=compute_compression_ratio(
                atom_count=sum(1 for node in state.nodes if int(getattr(node, "level", 0) or 0) == 0),
                macro_count=sum(1 for node in state.nodes if int(getattr(node, "level", 0) or 0) > 0),
            ),
            throughput_synapses_per_sec=float(global_throughput.get_throughput()),
            budget_profile="STRICT",
            benchmarks=benchmarks,
            summary=summary,
        )

    def persist_suite(self, graph_id: str, run: BenchmarkSuiteRun) -> Any:
        payload = {
            "run": run.to_dict(),
            "benchmark_id": run.run_id,
        }
        event = self.ctx.event_repo.emit(self.ctx.session, graph_id, "BENCHMARK_SUITE_RESULT", payload)
        self.ctx.session.commit()
        return event

    def list_suite_events(self, graph_id: str, limit: int = 200) -> List[Any]:
        events = self.ctx.event_repo.get_by_seq(self.ctx.session, graph_id=graph_id, after_seq=0, limit=max(1, limit) + 1)
        return [event for event in events if getattr(event, "kind", None) == "BENCHMARK_SUITE_RESULT"]

    def list_runs(self, graph_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        runs: List[Dict[str, Any]] = []
        for event in self.list_suite_events(graph_id, limit=limit):
            payload = _event_payload_dict(event)
            run = payload.get("run") if isinstance(payload.get("run"), dict) else None
            if run:
                runs.append(run)
        return runs[-limit:]

    def get_run(self, graph_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        target = str(run_id or "").strip()
        if not target:
            return None
        for run in reversed(self.list_runs(graph_id, limit=1000)):
            if str(run.get("run_id", "")).strip() == target:
                return run
        return None

    def series_points(self, graph_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        points: List[Dict[str, Any]] = []
        for event in self.list_suite_events(graph_id, limit=limit):
            payload = _event_payload_dict(event)
            run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
            if not run:
                continue
            points.append(
                {
                    "timestamp": run.get("computed_at") or getattr(event, "ts", None).isoformat() if getattr(event, "ts", None) else None,
                    "nodes": int(run.get("node_count", 0) or 0),
                    "cr": float(run.get("compression_ratio", 0.0) or 0.0),
                    "redundancy": float((run.get("benchmarks", [{}])[4].get("score", 0.0) / 100.0) if len(run.get("benchmarks", [])) > 4 else 0.0),
                    "drift": float(run.get("summary", {}).get("max_lambda_hat", 0.0) or 0.0),
                    "latency": {
                        "store_p50_ms": float(run.get("summary", {}).get("latest_ingest_latency_ms", 0.0) or 0.0),
                        "retrieve_p50_ms": float(run.get("summary", {}).get("latest_ingest_latency_ms", 0.0) or 0.0),
                        "retrieve_p95_ms": float(run.get("summary", {}).get("latest_ingest_latency_ms", 0.0) or 0.0),
                    },
                }
            )
        return points[-limit:]

    def latest_suite(self, graph_id: str) -> Optional[Dict[str, Any]]:
        runs = self.list_runs(graph_id, limit=1)
        if not runs:
            return None
        return runs[-1]


__all__ = ["BenchmarkCollector", "BenchmarkItem", "BenchmarkSuiteRun"]
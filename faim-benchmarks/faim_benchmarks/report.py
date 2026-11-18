"""SHA-256 signed JSON artifacts and Markdown leaderboard report generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple


def compute_payload_sha256(payload: Dict[str, Any]) -> str:
    clean = {k: v for k, v in payload.items() if k != "integrity_sha256"}
    canonical = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_publication_gate(result: Dict[str, Any]) -> Dict[str, Any]:
    """Prevent partial, sampled, dirty-worktree runs from being called publishable."""
    reasons = []
    systems = result.get("systems", [])
    skipped = [row["system"] for row in systems if row.get("status") == "skipped"]
    failed = [row["system"] for row in systems if row.get("status") == "failed"]
    if skipped:
        reasons.append(f"unconfigured systems: {', '.join(skipped)}")
    if failed:
        reasons.append(f"failed systems: {', '.join(failed)}")

    dataset_metadata = result.get("dataset_metadata", {})
    sampling = dataset_metadata.get("sampling", {})
    if sampling.get("max_corpus") is not None or sampling.get("max_queries") is not None:
        reasons.append("sampled dataset; full declared split was not evaluated")
    if dataset_metadata.get("source_type") == "huggingface_datasets":
        revisions = dataset_metadata.get("revisions") or {}
        if revisions:
            unpinned = [name for name in ("corpus", "queries", "qrels") if revisions.get(name) in {None, "", "unspecified"}]
            if unpinned:
                reasons.append(f"dataset revisions are not pinned: {', '.join(unpinned)}")
        elif dataset_metadata.get("revision") in {None, "", "unspecified"}:
            reasons.append("dataset revision is not pinned")

    run_metadata = result.get("run_metadata", {})
    if run_metadata.get("git_worktree_dirty") is True:
        reasons.append("git worktree was dirty")
    if not run_metadata.get("git_commit") or run_metadata.get("git_commit") == "unavailable":
        reasons.append("git commit is unavailable")

    if result.get("suite_type") == "retrieval_beir":
        if run_metadata.get("query_traces_retained") is not True:
            reasons.append("per-query retrieval traces were not retained")
        model_provenance = run_metadata.get("model_provenance") or {}
        required_model_fields = (
            "embedding_provider_id",
            "embedding_model_id",
            "embedding_model_revision",
        )
        missing_model_fields = [
            field
            for field in required_model_fields
            if model_provenance.get(field) in {None, "", "unspecified"}
        ]
        if missing_model_fields:
            reasons.append(
                "model provenance is incomplete: " + ", ".join(missing_model_fields)
            )
        quality_gates = run_metadata.get("quality_gates") or {}
        min_ndcg = quality_gates.get("min_ndcg_at_10")
        max_p95 = quality_gates.get("max_query_p95_ms")
        require_beats_bm25 = quality_gates.get("require_faim_beats_bm25") is True
        if min_ndcg is not None and not 0.0 <= float(min_ndcg) <= 1.0:
            reasons.append("invalid quality gate: min_ndcg_at_10 must be between 0 and 1")
        if max_p95 is not None and float(max_p95) <= 0.0:
            reasons.append("invalid quality gate: max_query_p95_ms must be positive")

        completed = {
            row.get("system"): row
            for row in systems
            if row.get("status") == "completed"
        }
        faim_row = completed.get("FAIM-Native")
        bm25_row = completed.get("BM25-Baseline")
        if faim_row:
            faim_ndcg = float((faim_row.get("metrics") or {}).get("ndcg@10", 0.0))
            faim_p95 = float((faim_row.get("latency_ms") or {}).get("query_p95", 0.0))
            if min_ndcg is not None and faim_ndcg < float(min_ndcg):
                reasons.append(
                    f"FAIM-Native nDCG@10 {faim_ndcg:.4f} is below gate {float(min_ndcg):.4f}"
                )
            if max_p95 is not None and faim_p95 > float(max_p95):
                reasons.append(
                    f"FAIM-Native query p95 {faim_p95:.2f} ms exceeds gate {float(max_p95):.2f} ms"
                )
            if require_beats_bm25 and bm25_row:
                bm25_ndcg = float((bm25_row.get("metrics") or {}).get("ndcg@10", 0.0))
                if faim_ndcg <= bm25_ndcg:
                    reasons.append(
                        f"FAIM-Native nDCG@10 {faim_ndcg:.4f} does not exceed BM25 {bm25_ndcg:.4f}"
                    )
        elif min_ndcg is not None or max_p95 is not None or require_beats_bm25:
            reasons.append("quality gates require a completed FAIM-Native system")

    return {
        "ready": not reasons,
        "reasons": reasons,
        "completed_systems": [row["system"] for row in systems if row.get("status") == "completed"],
        "skipped_systems": skipped,
        "failed_systems": failed,
    }


def render_markdown_report(result: Dict[str, Any]) -> str:
    suite = result["suite_type"]
    dataset = result["dataset"]
    hp = result["hyperparameters"]
    lines = [
        f"# FAIM External Benchmark Report — `{dataset}`",
        "",
        f"- **Run ID:** `{result['run_id']}`",
        f"- **Suite:** `{suite}`",
        f"- **Created:** `{result['created_at']}`",
        f"- **Parameters:** `top_k={hp['top_k']}`, `seed={hp['seed']}`, `bootstrap={hp['bootstrap_iterations']}`, `ingest_workers={hp.get('ingest_workers', 1)}`",
        f"- **Dataset metadata:** `{json.dumps(result.get('dataset_metadata', {}), sort_keys=True)}`",
        f"- **Run metadata:** `{json.dumps(result.get('run_metadata', {}), sort_keys=True)}`",
        f"- **Publication gate:** `{('READY' if result.get('publication_gate', {}).get('ready') else 'NOT READY')}`",
        f"- **Integrity SHA-256:** `{result.get('integrity_sha256', '')}`",
        "",
    ]

    if suite == "retrieval_beir":
        lines.extend(
            [
                "| System | Status | Recall@5 | nDCG@10 | MRR | MAP | Query P50 (ms) | Query P95 (ms) |",
                "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in result["systems"]:
            if row["status"] != "completed":
                lines.append(f"| {row['system']} | {row['status']} ({row.get('reason', '')}) | — | — | — | — | — | — |")
                continue
            m = row["metrics"]
            lat = row["latency_ms"]
            lines.append(
                f"| {row['system']} | completed | {m.get('recall@5', 0):.4f} | {m.get('ndcg@10', 0):.4f} | "
                f"{m.get('mrr', 0):.4f} | {m.get('map', 0):.4f} | {lat.get('query_p50', 0):.2f} | {lat.get('query_p95', 0):.2f} |"
            )
    else:
        lines.extend(
            [
                "| System | Status | Fact Recall | Token F1 | Exact Match | Query P50 (ms) | Query P95 (ms) |",
                "| :--- | :--- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in result["systems"]:
            if row["status"] != "completed":
                lines.append(f"| {row['system']} | {row['status']} ({row.get('reason', '')}) | — | — | — | — | — |")
                continue
            m = row["metrics"]
            lat = row["latency_ms"]
            lines.append(
                f"| {row['system']} | completed | {m.get('fact_recall', 0):.4f} | {m.get('token_f1', 0):.4f} | "
                f"{m.get('exact_match', 0):.4f} | {lat.get('query_p50', 0):.2f} | {lat.get('query_p95', 0):.2f} |"
            )

    lines.append("")
    quality_gates = result.get("run_metadata", {}).get("quality_gates") or {}
    if any(value is not None and value is not False for value in quality_gates.values()):
        lines.append(f"- **Quality gates:** `{json.dumps(quality_gates, sort_keys=True)}`")
        lines.append("")
    if result.get("run_metadata", {}).get("query_traces_retained") is True:
        lines.append("Per-query retrieval traces are retained in the signed JSON artifact without query or document text.")
        lines.append("")
    gate = result.get("publication_gate", {})
    if not gate.get("ready", False):
        lines.append("**Publication blockers:** " + "; ".join(gate.get("reasons", [])))
        lines.append("")
    lines.append("95% bootstrap confidence intervals are retained in the signed JSON artifact under `confidence_intervals`; non-completed systems are not scored.")
    lines.append("")
    return "\n".join(lines)


def write_signed_artifacts(result: Dict[str, Any], out_dir: str | Path) -> Tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    signed = dict(result)
    signed["publication_gate"] = evaluate_publication_gate(signed)
    signed["integrity_sha256"] = compute_payload_sha256(signed)

    run_id = signed["run_id"]
    json_path = target / f"{run_id}.json"
    md_path = target / f"{run_id}.md"

    json_path.write_text(json.dumps(signed, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown_report(signed), encoding="utf-8")
    return json_path, md_path

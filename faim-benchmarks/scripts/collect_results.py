"""Aggregate all signed FAIM benchmark JSON reports into RESULTS.md."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_reports(results_root: Path) -> List[Tuple[str, Dict[str, Any]]]:
    reports: List[Tuple[str, Dict[str, Any]]] = []
    for json_path in sorted(results_root.rglob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "systems" not in data or "run_id" not in data:
            continue
        rel = str(json_path.relative_to(results_root))
        reports.append((rel, data))

    for zip_path in sorted(results_root.glob("*.zip")):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                for name in sorted(zf.namelist()):
                    if not name.endswith(".json"):
                        continue
                    data = json.loads(zf.read(name).decode("utf-8"))
                    if "systems" in data and "run_id" in data:
                        reports.append((f"{zip_path.name}:{name}", data))
        except Exception:
            continue
    return reports


def main() -> None:
    results_root = Path(__file__).resolve().parent.parent / "results"
    reports = _load_reports(results_root)

    lines: List[str] = [
        "# FAIM Benchmark Results Summary",
        "",
        f"Collected **{len(reports)}** signed benchmark artifact(s) from `faim-benchmarks/results/`.",
        "",
        "## Retrieval Benchmarks (BEIR)",
        "",
        "| Source | Dataset | System | Model / Provider | Status | Recall@5 | nDCG@10 | MRR | MAP | P50 (ms) | P95 (ms) | Gate |",
        "| :--- | :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]

    mem_lines: List[str] = [
        "",
        "## Conversational Memory Benchmarks",
        "",
        "| Source | Suite | System | Status | Fact Recall | Token F1 | Exact Match | P50 (ms) | P95 (ms) | Avg Tokens | Gate |",
        "| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]

    for source, data in reports:
        suite_type = data.get("suite_type", "")
        gate = "READY" if (data.get("publication_gate") or {}).get("ready") else "NOT READY"
        ds_name = (
            data.get("dataset")
            or (data.get("dataset_metadata") or {}).get("corpus_source")
            or data.get("suite")
            or source.split("/")[0]
        )
        prov = ((data.get("run_metadata") or {}).get("model_provenance") or {})
        model_label = f"{prov.get('embedding_provider_id', 'n/a')} / {prov.get('embedding_model_id', 'n/a')}"

        for sys_row in data.get("systems", []):
            status = str(sys_row.get("status", ""))
            short_status = "completed" if status == "completed" else status.split("\n")[0][:40]
            metrics = sys_row.get("metrics") or {}
            lat = sys_row.get("latency_ms") or {}
            if suite_type == "retrieval_beir":
                r5 = f"{metrics['recall@5']:.4f}" if "recall@5" in metrics else "—"
                ndcg = f"{metrics['ndcg@10']:.4f}" if "ndcg@10" in metrics else "—"
                mrr = f"{metrics['mrr']:.4f}" if "mrr" in metrics else "—"
                mp = f"{metrics['map']:.4f}" if "map" in metrics else "—"
                p50 = f"{lat['query_p50']:.2f}" if "query_p50" in lat else "—"
                p95 = f"{lat['query_p95']:.2f}" if "query_p95" in lat else "—"
                lines.append(
                    f"| `{source}` | {ds_name} | {sys_row.get('system')} | `{model_label}` | {short_status} | {r5} | {ndcg} | {mrr} | {mp} | {p50} | {p95} | {gate} |"
                )
            elif suite_type == "conversational_memory":
                fr = f"{metrics['fact_recall']:.4f}" if "fact_recall" in metrics else "—"
                f1 = f"{metrics['token_f1']:.4f}" if "token_f1" in metrics else "—"
                em = f"{metrics['exact_match']:.4f}" if "exact_match" in metrics else "—"
                p50 = f"{lat['query_p50']:.2f}" if "query_p50" in lat else "—"
                p95 = f"{lat['query_p95']:.2f}" if "query_p95" in lat else "—"
                toks = f"{metrics['avg_context_tokens']:.1f}" if "avg_context_tokens" in metrics else "—"
                mem_lines.append(
                    f"| `{source}` | {ds_name} | {sys_row.get('system')} | {short_status} | {fr} | {f1} | {em} | {p50} | {p95} | {toks} | {gate} |"
                )

    out_path = results_root / "RESULTS.md"
    out_path.write_text("\n".join(lines + mem_lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(reports)} reports)")


if __name__ == "__main__":
    main()

"""CLI entrypoint for `faim-bench`."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from faim_benchmarks.adapters import build_all_adapters
from faim_benchmarks.datasets import load_beir_split, load_locomo_split, load_longmemeval_split
from faim_benchmarks.report import write_signed_artifacts
from faim_benchmarks.runner import run_conversational_benchmark, run_retrieval_benchmark


def _load_dotenv_if_present() -> None:
    env_path = Path(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _run_metadata(argv: List[str]) -> dict:
    """Return reproducibility metadata without recording credentials."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        commit = "unavailable"
    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        dirty = "unavailable"
    return {
        "command": ["faim-bench", *argv],
        "git_commit": commit,
        "git_worktree_dirty": bool(dirty),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "faim_base_url": os.getenv("FAIM_BASE_URL", "http://localhost:8000"),
        "faim_profile": os.getenv("FAIM_PROFILE", "strict"),
        "faim_persist_mode": os.getenv("FAIM_PERSIST_MODE", "strict"),
        "faim_write_mode": os.getenv("FAIM_BENCH_FAIM_WRITE_MODE", "ingest"),
        "faim_enable_jobs": os.getenv("FAIM_ENABLE_JOBS", "unspecified"),
        "faim_self_evolve_enabled": os.getenv(
            "FAIM_SELF_EVOLVE_ENABLED", "unspecified"
        ),
        "faim_profile_persist_compat_mode": os.getenv(
            "FAIM_PROFILE_PERSIST_COMPAT_MODE", "unspecified"
        ),
        "faim_rate_limits_json": os.getenv("FAIM_RATE_LIMITS_JSON", "unspecified"),
        "faim_api_workers": os.getenv("FAIM_API_WORKERS", "unspecified"),
        "faim_batch_size": os.getenv("FAIM_BENCH_FAIM_BATCH_SIZE", "0"),
        "faim_repr_v2_enabled": os.getenv("FAIM_REPR_V2_ENABLED", "unspecified"),
        "faim_phase5_enabled": os.getenv("FAIM_PHASE5_ENABLED", "unspecified"),
        "faim_db_idle_in_transaction_timeout_ms": os.getenv(
            "FAIM_DB_IDLE_IN_TRANSACTION_TIMEOUT_MS", "unspecified"
        ),
        "faim_db_lock_timeout_ms": os.getenv(
            "FAIM_DB_LOCK_TIMEOUT_MS", "unspecified"
        ),
    }


def _select_adapters(adapters, systems: Optional[str]):
    """Select an explicit comparison scope without silently dropping systems."""
    if not systems:
        return list(adapters), None
    requested = {item.strip().lower() for item in systems.split(",") if item.strip()}
    if not requested:
        raise ValueError("--systems must contain at least one system name")
    aliases = {
        "faim": "faim-native",
        "faim-native": "faim-native",
        "bm25": "bm25-baseline",
        "bm25-baseline": "bm25-baseline",
        "mem0": "mem0",
        "zep": "zep",
        "supermemory": "supermemory",
        "letta": "letta",
        "full-context-llm": "full-context-llm",
        "full-context": "full-context-llm",
    }
    unknown = sorted(item for item in requested if item not in aliases)
    if unknown:
        raise ValueError(
            "Unknown --systems value(s): " + ", ".join(unknown)
        )
    canonical = {aliases[item] for item in requested}
    selected = [adapter for adapter in adapters if adapter.name.lower() in canonical]
    missing = sorted(canonical - {adapter.name.lower() for adapter in selected})
    if missing:
        raise ValueError("Requested systems are unavailable: " + ", ".join(missing))
    return selected, [adapter.name for adapter in selected]


def main(argv: Optional[List[str]] = None) -> int:
    _load_dotenv_if_present()
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="faim-bench", description="External benchmark runner for FAIM vs competitors")
    sub = parser.add_subparsers(dest="command", required=True)

    beir = sub.add_parser("beir", help="Run a BEIR retrieval benchmark")
    beir.add_argument("--dataset", default="scifact", help="BEIR dataset name (scifact, nfcorpus, fiqa, hotpotqa, fever, nq, msmarco)")
    beir.add_argument("--local-dir", default=None, help="Optional local BEIR directory instead of HuggingFace download")
    beir.add_argument("--max-corpus", type=int, default=None)
    beir.add_argument("--max-queries", type=int, default=None)
    beir.add_argument("--top-k", type=int, default=20)
    beir.add_argument("--seed", type=int, default=42)
    beir.add_argument("--bootstrap", type=int, default=300)
    beir.add_argument(
        "--systems",
        default=None,
        help="Comma-separated comparison scope (for example: faim,bm25); default: all adapters",
    )
    beir.add_argument(
        "--ingest-workers",
        type=int,
        default=1,
        help="Bounded concurrent HTTP ingest workers (default: 1)",
    )
    beir.add_argument("--out-dir", default="results")

    conv = sub.add_parser("memory", help="Run LoCoMo or LongMemEval conversational memory benchmark")
    conv.add_argument("--suite", choices=["locomo", "longmemeval"], required=True)
    conv.add_argument("--data-path", required=True, help="Path to LoCoMo or LongMemEval JSON file")
    conv.add_argument("--max-cases", type=int, default=None)
    conv.add_argument("--top-k", type=int, default=20)
    conv.add_argument("--seed", type=int, default=42)
    conv.add_argument("--bootstrap", type=int, default=300)
    conv.add_argument(
        "--systems",
        default=None,
        help="Comma-separated comparison scope; default: all adapters",
    )
    conv.add_argument("--out-dir", default="results")

    args = parser.parse_args(argv)
    adapters = build_all_adapters()
    try:
        adapters, selected_systems = _select_adapters(adapters, args.systems)
        run_metadata = _run_metadata(effective_argv)
        if selected_systems is not None:
            run_metadata["selected_systems"] = selected_systems
            run_metadata["comparison_scope"] = "explicit"
        if args.command == "beir":
            split = load_beir_split(
                args.dataset,
                local_dir=args.local_dir,
                max_corpus=args.max_corpus,
                max_queries=args.max_queries,
                seed=args.seed,
            )
            result = run_retrieval_benchmark(
                split=split,
                adapters=adapters,
                top_k=args.top_k,
                seed=args.seed,
                bootstrap_iterations=args.bootstrap,
                ingest_workers=args.ingest_workers,
                run_metadata=run_metadata,
            )
        else:
            split = (
                load_locomo_split(args.data_path, max_cases=args.max_cases)
                if args.suite == "locomo"
                else load_longmemeval_split(args.data_path, max_cases=args.max_cases)
            )
            result = run_conversational_benchmark(
                split=split,
                adapters=adapters,
                top_k=args.top_k,
                seed=args.seed,
                bootstrap_iterations=args.bootstrap,
                run_metadata=run_metadata,
            )

        json_path, md_path = write_signed_artifacts(result, args.out_dir)
        print(f"Benchmark complete: {json_path} | {md_path}")
        signed = json.loads(json_path.read_text(encoding="utf-8"))
        print(f"Integrity SHA-256: {signed['integrity_sha256']}")
        return 0
    finally:
        for adapter in adapters:
            adapter.close()


if __name__ == "__main__":
    raise SystemExit(main())

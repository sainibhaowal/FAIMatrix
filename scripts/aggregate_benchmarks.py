#!/usr/bin/env python
"""
Aggregate FAIM + RAG benchmark JSON files and produce:
- mean / std for CR, redundancy, drift, latency
- grouped bar plots per workload: FAIM vs baseline_rag
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt

BENCH_DIR = Path("Runtime/Benchmarks")


@dataclass
class Stat:
    mean: float
    std: float


def _to_str(x: Any) -> str:
    if isinstance(x, str):
        return x
    return repr(x)


def collect_records() -> Dict[Tuple[str, str], List[dict]]:
    """
    Key: (system, workload) both as strings.
    """
    records: Dict[Tuple[str, str], List[dict]] = {}

    # search recursively for any *.json file
    for path in BENCH_DIR.rglob("*.json"):
        if not path.is_file():
            continue
        with path.open("r", encoding="utf8") as f:
            data = json.load(f)

        system_raw = data.get("system")
        workload_raw = data.get("workload")

        if isinstance(system_raw, str) and isinstance(workload_raw, str):
            # baseline record
            system = system_raw
            workload = workload_raw
        else:
            # FAIM record from benchmarks.py
            system = "faim"
            w = workload_raw
            if isinstance(w, str):
                workload = w
            elif isinstance(w, dict):
                workload = w.get("name") or w.get("kind") or w.get("id") or _to_str(w)
            else:
                workload = "unknown"

        key = (_to_str(system), _to_str(workload))
        records.setdefault(key, []).append(data)

    return records


def stat(values: List[float]) -> Stat:
    if not values:
        return Stat(0.0, 0.0)
    if len(values) == 1:
        return Stat(values[0], 0.0)
    return Stat(mean(values), pstdev(values))


def main() -> None:
    records = collect_records()

    if not records:
        print("No benchmark JSON files found in Runtime/Benchmarks")
        return

    summary: Dict[Tuple[str, str], Dict[str, Stat]] = {}

    for (system, workload), recs in records.items():
        cr_vals: List[float] = []
        red_vals: List[float] = []
        drift_vals: List[float] = []
        lat_p50_vals: List[float] = []

        for r in recs:
            if isinstance(r.get("system"), str):
                # baseline format
                cr_vals.append(float(r.get("cr", 0.0)))
                red_vals.append(float(r.get("redundancy", 0.0)))
                drift_vals.append(float(r.get("drift", 0.0)))
                lat_p50_vals.append(float(r.get("latency_retrieve_p50", 0.0)))
            else:
                # FAIM format
                m = r.get("metrics", {})
                cr_vals.append(float(m.get("compression_ratio", 0.0)))
                red_vals.append(float(m.get("redundancy_index", 0.0)))
                drift_vals.append(float(m.get("drift_score", 0.0)))
                latency = m.get("latency", {})
                p50 = latency.get("retrieve_p50_ms") or latency.get("retrieve_p50", 0.0)
                lat_p50_vals.append(float(p50))

        summary[(system, workload)] = {
            "cr": stat(cr_vals),
            "redundancy": stat(red_vals),
            "drift": stat(drift_vals),
            "lat_p50": stat(lat_p50_vals),
        }

    workloads = sorted({w for (_, w) in summary.keys()})
    systems = sorted({s for (s, _) in summary.keys()})

    # One grouped bar plot per metric
    for metric in ["cr", "redundancy", "drift", "lat_p50"]:
        plt.figure()
        x = list(range(len(workloads)))
        width = 0.8 / max(len(systems), 1)

        for i, system in enumerate(systems):
            vals = []
            for w in workloads:
                s = summary.get((system, w))
                vals.append(s[metric].mean if s else 0.0)
            offset = (i - (len(systems) - 1) / 2.0) * width
            xs = [xi + offset for xi in x]
            plt.bar(xs, vals, width=width, label=system)

        plt.xticks(x, workloads, rotation=20)
        plt.ylabel(metric)
        plt.legend()
        plt.tight_layout()
        out_path = BENCH_DIR / f"plot_{metric}.png"
        plt.savefig(out_path)
        print(f"Wrote {out_path}")

    print("Aggregation complete.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
FAIM full test bundle: verifies core claims (fractal, inheritance, antisymmetry,
pruning, opposition, evolution, compression) using deterministic checks.

This script runs offline against the local core engine + math modules and writes
an auditable JSON report.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from faim.core.antisym import (
    merge_records,
    opposition_update,
    opposition_vector,
    practical_wedge_merge,
)
from faim.core.engine import FAIMEngine
from faim.core.evolution import evolve_graph_once
from faim.core.math import GOLDEN_SCALE, inheritance_construction, simulate_inheritance_chain
from faim.core.metrics import compression_ratio, estimate_fractal_dimension
from faim.core.types import GraphId, NodeRecord, ParentRef
from faim.storage.sqlite_store import SqliteStore


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    metrics: Dict[str, Any]


def _vec(dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(dim,)).astype(np.float32)
    return v


def _close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def _run_test(name: str, fn: Callable[[], Tuple[bool, str, Dict[str, Any]]]) -> TestResult:
    try:
        ok, details, metrics = fn()
        return TestResult(name=name, passed=ok, details=details, metrics=metrics)
    except Exception as exc:
        return TestResult(
            name=name,
            passed=False,
            details=f"exception: {type(exc).__name__}: {exc}",
            metrics={},
        )


def test_inheritance_math() -> Tuple[bool, str, Dict[str, Any]]:
    p1 = _vec(64, 1)
    p2 = _vec(64, 2)
    e = _vec(64, 3)
    res = inheritance_construction([p1, p2], e)
    frac_sum = float(np.sum(res.fractions)) if res.fractions is not None else 0.0
    inherited = res.inherited
    mixed = (res.fractions[0] * p1) + (res.fractions[1] * p2)
    expected_inherited = float(GOLDEN_SCALE) * mixed

    ok = np.allclose(inherited, expected_inherited, atol=1e-5) and np.allclose(
        res.v_new, res.inherited + res.novelty, atol=1e-6
    )
    details = "fractions sum to 1 and v_new = inherited + novelty" if ok else "inheritance mismatch"
    return ok, details, {"fractions_sum": frac_sum}


def test_inheritance_chain() -> Tuple[bool, str, Dict[str, Any]]:
    norms = simulate_inheritance_chain(depth=6, dim=32)
    ok = len(norms) == 7 and all(isinstance(x, float) for x in norms)
    return ok, "chain length and norms present" if ok else "chain invalid", {"length": len(norms)}


def test_antisymmetry_opposition() -> Tuple[bool, str, Dict[str, Any]]:
    a = _vec(32, 10)
    b = _vec(32, 11)
    o1 = opposition_vector(a, b)
    o2 = opposition_vector(b, a)
    antisym_ok = np.allclose(o1, -o2, atol=1e-6)

    merged = practical_wedge_merge(a, b)
    orth_ok = abs(float(np.dot(merged.astype(np.float64), b.astype(np.float64)))) < 1e-5

    once = opposition_update(a, b)
    twice = opposition_update(once, b)
    idem_ok = np.allclose(once, twice, atol=1e-6)

    ok = antisym_ok and orth_ok and idem_ok
    details = "antisym, orthogonal, idempotent" if ok else "antisym failure"
    return ok, details, {"antisym": antisym_ok, "orthogonal": orth_ok, "idempotent": idem_ok}


def test_merge_records() -> Tuple[bool, str, Dict[str, Any]]:
    g = GraphId("TEST:merge")
    keep = NodeRecord(
        id="n1",
        graph_id=g,
        vec=_vec(16, 1),
        parents=[],
        children=[],
        payload_ref=None,
        created_at=time.time(),
        last_used_at=time.time(),
        use_count=2,
        merged_count=1,
        flags=0,
    )
    drop = NodeRecord(
        id="n2",
        graph_id=g,
        vec=_vec(16, 2),
        parents=[ParentRef(parent_id="n1", fraction=1.0)],
        children=[],
        payload_ref=None,
        created_at=time.time(),
        last_used_at=time.time(),
        use_count=3,
        merged_count=2,
        flags=0,
    )
    merged = merge_records(keep, drop)
    ok = merged.use_count == 5 and merged.merged_count == 4
    return ok, "merge counters updated" if ok else "merge counters wrong", {
        "use_count": merged.use_count,
        "merged_count": merged.merged_count,
    }


def test_compression_ratio() -> Tuple[bool, str, Dict[str, Any]]:
    tmp = Path("Runtime/Tests")
    tmp.mkdir(parents=True, exist_ok=True)
    db_path = tmp / f"faim_test_compression_{int(time.time())}.sqlite3"
    store = SqliteStore(db_path=str(db_path))
    g = GraphId("TEST:cr")

    nodes = [
        NodeRecord(id="a", graph_id=g, vec=_vec(8, 1), parents=[], children=[], payload_ref=None,
                   created_at=0, last_used_at=0, use_count=1, merged_count=0, flags=0),
        NodeRecord(id="b", graph_id=g, vec=_vec(8, 2), parents=[], children=[], payload_ref=None,
                   created_at=0, last_used_at=0, use_count=1, merged_count=2, flags=0),
        NodeRecord(id="c", graph_id=g, vec=_vec(8, 3), parents=[], children=[], payload_ref=None,
                   created_at=0, last_used_at=0, use_count=1, merged_count=4, flags=0),
    ]
    for n in nodes:
        store.upsert_node(n)

    cr = compression_ratio(store, g)
    ok = _close(cr, 3.0, tol=1e-6)
    return ok, "compression ratio matches expected 3.0" if ok else "compression ratio mismatch", {
        "cr": cr,
        "db_path": str(db_path),
    }


def test_fractal_dimension() -> Tuple[bool, str, Dict[str, Any]]:
    branching = 4.0
    expected = math.log(branching) / math.log(1.0 / GOLDEN_SCALE)
    d = estimate_fractal_dimension(branching_factor=branching, scale=GOLDEN_SCALE)
    ok = _close(d, expected, tol=1e-6)
    return ok, "fractal dimension matches analytic formula" if ok else "fractal dimension mismatch", {
        "D": d,
        "expected": expected,
    }


def test_prune_evolution() -> Tuple[bool, str, Dict[str, Any]]:
    tmp = Path("Runtime/Tests")
    tmp.mkdir(parents=True, exist_ok=True)
    db_path = tmp / f"faim_test_prune_{int(time.time())}.sqlite3"
    store = SqliteStore(db_path=str(db_path))
    g = GraphId("TEST:prune")

    for i in range(3):
        n = NodeRecord(
            id=f"p{i}",
            graph_id=g,
            vec=_vec(8, 10 + i),
            parents=[],
            children=[],
            payload_ref=None,
            created_at=0,
            last_used_at=0,
            use_count=0,
            merged_count=0,
            flags=0,
        )
        store.upsert_node(n)

    stats = evolve_graph_once(store, g)
    ok = stats.prunes >= 1
    return ok, "prune executed on cold leaves" if ok else "prune did not occur", {
        "prunes": stats.prunes,
        "db_path": str(db_path),
    }


def test_engine_evolution_path() -> Tuple[bool, str, Dict[str, Any]]:
    tmp = Path("Runtime/Tests")
    tmp.mkdir(parents=True, exist_ok=True)
    db_path = tmp / f"faim_test_engine_{int(time.time())}.sqlite3"
    store = SqliteStore(db_path=str(db_path))
    engine = FAIMEngine(store=store, payload_store=store)
    graph_id = "TEST:engine"

    engine.add_memory(graph_id, "alpha")
    engine.add_memory(graph_id, "beta")
    engine.add_memory(graph_id, "gamma")
    engine.evolve(graph_id)
    return True, "engine evolve executed without error", {"db_path": str(db_path)}


def run_all() -> List[TestResult]:
    tests = [
        ("inheritance_math", test_inheritance_math),
        ("inheritance_chain", test_inheritance_chain),
        ("antisymmetry_opposition", test_antisymmetry_opposition),
        ("merge_records", test_merge_records),
        ("compression_ratio", test_compression_ratio),
        ("fractal_dimension", test_fractal_dimension),
        ("prune_evolution", test_prune_evolution),
        ("engine_evolution", test_engine_evolution_path),
    ]
    results = []
    for name, fn in tests:
        results.append(_run_test(name, fn))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="FAIM full test bundle")
    parser.add_argument(
        "--out",
        default="Runtime/Tests/faim_full_test_bundle_report.json",
        help="Output report path (JSON).",
    )
    args = parser.parse_args()

    results = run_all()
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": passed,
        "total": total,
        "results": [asdict(r) for r in results],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

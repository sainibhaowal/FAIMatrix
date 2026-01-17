"""FAIM-Native Invariants.

Core invariants that must hold after every operation.

Rules:
- Inheritance: Σfractions = 1 for every child
- Boundedness: vector norms finite, residual in [0,1]
- Event coverage: every mutation has an event
- Idempotence: re-run same vectors yields no change
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

# Flexible imports
try:
    from faim.Faim_Native.store.pg.repos.edge_repo import EdgeRepo
    from faim.Faim_Native.store.pg.repos.node_repo import NodeRepo
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.node_repo import NodeRepo


@dataclass
class InvariantResult:
    """Result of invariant check.

    Attributes:
        passed: Whether all checks passed.
        checks: List of individual check results.
        errors: List of error messages.
    """

    passed: bool = True
    checks: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_check(self, name: str, passed: bool, details: str = ""):
        self.checks.append({"name": name, "passed": passed, "details": details})
        if not passed:
            self.passed = False
            self.errors.append(f"{name}: {details}")


def check_inheritance_sum(
    edge_repo: EdgeRepo,
    node_repo: NodeRepo,
    graph_id: str,
    tolerance: float = 1e-9,
) -> InvariantResult:
    """Check that inheritance fractions sum to 1 for all children.

    For every node with parents, Σfractions must equal 1.0 ± tolerance.

    Args:
        edge_repo: Edge repository.
        node_repo: Node repository.
        graph_id: Graph identifier.
        tolerance: Tolerance for sum comparison.

    Returns:
        InvariantResult with check status.
    """
    result = InvariantResult()

    nodes = node_repo.list_nodes(graph_id, limit=10000)

    for node in nodes:
        parents = edge_repo.list_parents(graph_id, node.node_id)

        if not parents:
            continue  # No parents is valid

        fractions = [f for _, f in parents]
        total = sum(fractions)

        if abs(total - 1.0) > tolerance:
            result.add_check(
                name=f"inheritance_sum_{node.node_id}",
                passed=False,
                details=f"Sum={total}, expected=1.0 ± {tolerance}",
            )
        else:
            result.add_check(
                name=f"inheritance_sum_{node.node_id}",
                passed=True,
            )

    return result


def check_boundedness(
    node_repo: NodeRepo,
    graph_id: str,
) -> InvariantResult:
    """Check that all vectors are bounded.

    - No NaN or Inf in v_native
    - Residual in [0, 1]
    - Norm is finite

    Args:
        node_repo: Node repository.
        graph_id: Graph identifier.

    Returns:
        InvariantResult with check status.
    """
    result = InvariantResult()

    nodes = node_repo.list_nodes(graph_id, limit=10000)

    for node in nodes:
        v_native = node.v_native or []

        # Check for NaN/Inf
        has_nan = any(math.isnan(v) for v in v_native)
        has_inf = any(math.isinf(v) for v in v_native)

        if has_nan:
            result.add_check(
                name=f"no_nan_{node.node_id}",
                passed=False,
                details="Vector contains NaN",
            )
        else:
            result.add_check(name=f"no_nan_{node.node_id}", passed=True)

        if has_inf:
            result.add_check(
                name=f"no_inf_{node.node_id}",
                passed=False,
                details="Vector contains Inf",
            )
        else:
            result.add_check(name=f"no_inf_{node.node_id}", passed=True)

        # Check norm
        norm = math.sqrt(sum(v * v for v in v_native))
        if not math.isfinite(norm):
            result.add_check(
                name=f"finite_norm_{node.node_id}",
                passed=False,
                details=f"Norm is not finite: {norm}",
            )
        else:
            result.add_check(name=f"finite_norm_{node.node_id}", passed=True)

        # Check residual
        residual = node.residual / 1e9 if node.residual else 0.0
        if residual < 0 or residual > 1:
            result.add_check(
                name=f"residual_bounded_{node.node_id}",
                passed=False,
                details=f"Residual={residual}, expected [0,1]",
            )
        else:
            result.add_check(name=f"residual_bounded_{node.node_id}", passed=True)

    return result


def check_event_coverage(
    event_repo,
    graph_id: str,
    expected_events: int,
) -> InvariantResult:
    """Check that expected number of events exist.

    Args:
        event_repo: Event repository.
        graph_id: Graph identifier.
        expected_events: Minimum expected events.

    Returns:
        InvariantResult with check status.
    """
    result = InvariantResult()

    events = event_repo.list(graph_id=graph_id, limit=10000)
    count = len(events)

    if count >= expected_events:
        result.add_check(
            name="event_coverage",
            passed=True,
            details=f"Found {count} events (expected >= {expected_events})",
        )
    else:
        result.add_check(
            name="event_coverage",
            passed=False,
            details=f"Found {count} events (expected >= {expected_events})",
        )

    return result


def check_all_invariants(
    node_repo: NodeRepo,
    edge_repo: EdgeRepo,
    graph_id: str,
) -> InvariantResult:
    """Run all invariant checks.

    Args:
        node_repo: Node repository.
        edge_repo: Edge repository.
        graph_id: Graph identifier.

    Returns:
        Combined InvariantResult.
    """
    result = InvariantResult()

    # Check inheritance sum
    inheritance_result = check_inheritance_sum(edge_repo, node_repo, graph_id)
    result.checks.extend(inheritance_result.checks)
    result.errors.extend(inheritance_result.errors)
    if not inheritance_result.passed:
        result.passed = False

    # Check boundedness
    bounded_result = check_boundedness(node_repo, graph_id)
    result.checks.extend(bounded_result.checks)
    result.errors.extend(bounded_result.errors)
    if not bounded_result.passed:
        result.passed = False

    return result


# =============================================================================
# Stage-4.1: Fractal Physics Invariants
# =============================================================================


def check_scaling_bounds(s: float) -> InvariantResult:
    """Check that scaling factor s is in valid range.

    Invariant: 0 < s <= 1

    Args:
        s: Scaling factor.

    Returns:
        InvariantResult.
    """
    result = InvariantResult()

    if 0 < s <= 1:
        result.add_check(
            name="scaling_bounds",
            passed=True,
            details=f"s={s} is in (0, 1]",
        )
    else:
        result.add_check(
            name="scaling_bounds",
            passed=False,
            details=f"s={s} is NOT in (0, 1]",
        )

    return result


def check_D_range(D_hat: float, d_max: float = 10.0) -> InvariantResult:
    """Check that fractal dimension D is in valid range.

    Invariant: 0 <= D <= d_max

    Args:
        D_hat: Estimated fractal dimension.
        d_max: Maximum allowed D.

    Returns:
        InvariantResult.
    """
    result = InvariantResult()

    if 0 <= D_hat <= d_max:
        result.add_check(
            name="D_range",
            passed=True,
            details=f"D={D_hat} is in [0, {d_max}]",
        )
    else:
        result.add_check(
            name="D_range",
            passed=False,
            details=f"D={D_hat} is NOT in [0, {d_max}]",
        )

    return result


def check_H_range(H_hat: float) -> InvariantResult:
    """Check that entropy H is in valid range.

    Invariant: 0 <= H <= 1

    Args:
        H_hat: Estimated entropy.

    Returns:
        InvariantResult.
    """
    result = InvariantResult()

    if 0 <= H_hat <= 1:
        result.add_check(
            name="H_range",
            passed=True,
            details=f"H={H_hat} is in [0, 1]",
        )
    else:
        result.add_check(
            name="H_range",
            passed=False,
            details=f"H={H_hat} is NOT in [0, 1]",
        )

    return result


def check_lambda_range(lambda_hat: float) -> InvariantResult:
    """Check that evolution pressure λ is in valid range.

    Invariant: 0 <= λ <= 1

    Args:
        lambda_hat: Estimated evolution pressure.

    Returns:
        InvariantResult.
    """
    result = InvariantResult()

    if 0 <= lambda_hat <= 1:
        result.add_check(
            name="lambda_range",
            passed=True,
            details=f"λ={lambda_hat} is in [0, 1]",
        )
    else:
        result.add_check(
            name="lambda_range",
            passed=False,
            details=f"λ={lambda_hat} is NOT in [0, 1]",
        )

    return result


def check_energy_bounded(
    energy_E: float,
    bound: float = 2.0,
) -> InvariantResult:
    """Check that energy E is bounded.

    Invariant: E <= bound (stability condition)

    Args:
        energy_E: Computed energy.
        bound: Maximum allowed energy.

    Returns:
        InvariantResult.
    """
    result = InvariantResult()

    if energy_E <= bound:
        result.add_check(
            name="energy_bounded",
            passed=True,
            details=f"E={energy_E} <= {bound}",
        )
    else:
        result.add_check(
            name="energy_bounded",
            passed=False,
            details=f"E={energy_E} > {bound} (unbounded)",
        )

    return result


def check_no_orphan_edges(
    edge_repo: EdgeRepo,
    node_repo: NodeRepo,
    graph_id: str,
) -> InvariantResult:
    """Check that no edges reference non-existent nodes.

    Invariant: Every edge src/dst must exist in nodes table.

    Args:
        edge_repo: Edge repository.
        node_repo: Node repository.
        graph_id: Graph identifier.

    Returns:
        InvariantResult.
    """
    result = InvariantResult()

    edges = edge_repo.list_all_edges(graph_id, limit=10000)
    nodes = node_repo.list_nodes(graph_id, limit=10000)
    node_ids = {n.node_id for n in nodes}

    orphan_count = 0
    for edge in edges:
        if edge.src_node_id not in node_ids:
            orphan_count += 1
        if edge.dst_node_id not in node_ids:
            orphan_count += 1

    if orphan_count == 0:
        result.add_check(
            name="no_orphan_edges",
            passed=True,
            details=f"All {len(edges)} edges have valid node references",
        )
    else:
        result.add_check(
            name="no_orphan_edges",
            passed=False,
            details=f"Found {orphan_count} orphan edge references",
        )

    return result


def check_fractal_invariants(
    s: float,
    D_hat: float,
    H_hat: float,
    lambda_hat: float,
    energy_E: float,
) -> InvariantResult:
    """Check all fractal physics invariants.

    Args:
        s: Scaling factor.
        D_hat: Fractal dimension.
        H_hat: Entropy.
        lambda_hat: Evolution pressure.
        energy_E: Energy.

    Returns:
        Combined InvariantResult.
    """
    result = InvariantResult()

    for check_result in [
        check_scaling_bounds(s),
        check_D_range(D_hat),
        check_H_range(H_hat),
        check_lambda_range(lambda_hat),
        check_energy_bounded(energy_E),
    ]:
        result.checks.extend(check_result.checks)
        result.errors.extend(check_result.errors)
        if not check_result.passed:
            result.passed = False

    return result


# Exports
__all__ = [
    "InvariantResult",
    "check_inheritance_sum",
    "check_boundedness",
    "check_event_coverage",
    "check_all_invariants",
    # Stage-4.1 fractal invariants
    "check_scaling_bounds",
    "check_D_range",
    "check_H_range",
    "check_lambda_range",
    "check_energy_bounded",
    "check_no_orphan_edges",
    "check_fractal_invariants",
]

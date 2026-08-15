"""Evolution learning repository (Phase 0032).

Durable storage for:
- per-cycle evolution outcomes (before/after metrics + reward)
- per-graph learned policy state (bandit arms + lambda calibration)
- rolling meta-metrics (maturity proof)

All reads are fail-closed: any corruption or missing row resolves to safe
defaults so the evolution pipeline never depends on learning state.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.store.pg.models_faim import (
        EvolutionMetaMetricModel,
        EvolutionOutcomeModel,
        EvolutionPolicyStateModel,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.models_faim import (
        EvolutionMetaMetricModel,
        EvolutionOutcomeModel,
        EvolutionPolicyStateModel,
    )


# =============================================================================
# Outcome value object
# =============================================================================


@dataclass(frozen=True)
class EvolutionOutcome:
    """Snapshot of one evolution cycle for learning."""

    graph_version: int = 0
    merges: int = 0
    prunes: int = 0
    inventions: int = 0
    theories: int = 0
    lambda_before: float = 0.0
    lambda_after: float = 0.0
    r_before: float = 0.0
    r_after: float = 0.0
    n_before: float = 0.0
    n_after: float = 0.0
    d_before: float = 0.0
    d_after: float = 0.0
    h_before: float = 0.0
    h_after: float = 0.0
    e_before: float = 0.0
    e_after: float = 0.0
    retrieval_delta: Optional[float] = None
    reward: float = 0.0
    policy_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MetaMetricSnapshot:
    """One row of rolling maturity meta-metrics."""

    merge_usefulness: float = 0.0
    invention_utilization: float = 0.0
    prune_regret: float = 0.0
    d_drift: float = 0.0
    h_drift: float = 0.0
    alerts: Dict[str, Any] = field(default_factory=dict)
    detail: Dict[str, Any] = field(default_factory=dict)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class EvolutionLearningRepo:
    """Persistence for evolution learning state.

    Args:
        session: SQLAlchemy session.
        tenant_id: Tenant scope for all rows.
    """

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    # =========================================================================
    # Outcomes
    # =========================================================================

    def record_outcome(
        self,
        graph_id: str,
        outcome: EvolutionOutcome,
        session: Optional[Session] = None,
    ) -> UUID:
        """Persist one outcome row. Never raises (fail-open write)."""
        sess = session or self.session
        if sess is None:
            return UUID(int=0)
        try:
            with sess.begin_nested():
                model = EvolutionOutcomeModel(
                    id=uuid4(),
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    graph_version=max(0, int(outcome.graph_version)),
                    cycle_ts=datetime.now(timezone.utc),
                    merges=max(0, int(outcome.merges)),
                    prunes=max(0, int(outcome.prunes)),
                    inventions=max(0, int(outcome.inventions)),
                    theories=max(0, int(outcome.theories)),
                    lambda_before=float(outcome.lambda_before),
                    lambda_after=float(outcome.lambda_after),
                    r_before=float(outcome.r_before),
                    r_after=float(outcome.r_after),
                    n_before=float(outcome.n_before),
                    n_after=float(outcome.n_after),
                    d_before=float(outcome.d_before),
                    d_after=float(outcome.d_after),
                    h_before=float(outcome.h_before),
                    h_after=float(outcome.h_after),
                    e_before=float(outcome.e_before),
                    e_after=float(outcome.e_after),
                    retrieval_delta=(
                        float(outcome.retrieval_delta)
                        if outcome.retrieval_delta is not None
                        else None
                    ),
                    reward=float(outcome.reward),
                    policy_snapshot=outcome.policy_snapshot or {},
                )
                sess.add(model)
                sess.flush()
                return model.id
        except Exception:  # nosec B110 - learning is best effort
            return UUID(int=0)

    def get_outcomes(
        self,
        graph_id: str,
        limit: int = 50,
        session: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent outcome rows for a graph (newest first)."""
        sess = session or self.session
        if sess is None:
            return []
        try:
            rows = (
                sess.query(EvolutionOutcomeModel)
                .filter(
                    EvolutionOutcomeModel.tenant_id == self.tenant_id,
                    EvolutionOutcomeModel.graph_id == graph_id,
                )
                .order_by(desc(EvolutionOutcomeModel.cycle_ts))
                .limit(max(1, min(500, int(limit))))
                .all()
            )
            return [row.to_dict() for row in rows]
        except Exception:  # nosec B110
            return []

    # =========================================================================
    # Policy state
    # =========================================================================

    def load_policy_state(
        self,
        graph_id: str,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Load persisted policy state. Fail-closed to defaults on any issue."""
        from core.learning.evolution_policy import POLICY_SCHEMA

        default = {
            "schema": POLICY_SCHEMA,
            "arms": {},
            "lambda_calibration": {},
            "meta": {},
            "version": 0,
        }
        sess = session or self.session
        if sess is None:
            return default
        try:
            row = (
                sess.query(EvolutionPolicyStateModel)
                .filter(
                    EvolutionPolicyStateModel.tenant_id == self.tenant_id,
                    EvolutionPolicyStateModel.graph_id == graph_id,
                )
                .first()
            )
            if row is None:
                return default
            return {
                "schema": POLICY_SCHEMA,
                "arms": dict(row.arms or {}),
                "lambda_calibration": dict(row.lambda_calibration or {}),
                "meta": dict(row.meta or {}),
                "version": int(row.policy_version or 0),
            }
        except Exception:  # nosec B110
            return default

    def save_policy_state(
        self,
        graph_id: str,
        *,
        arms: Dict[str, Any],
        lambda_calibration: Dict[str, Any],
        meta: Dict[str, Any],
        policy_version: int,
        session: Optional[Session] = None,
    ) -> bool:
        """Upsert policy state. Never raises (best effort)."""
        sess = session or self.session
        if sess is None:
            return False
        try:
            with sess.begin_nested():
                row = (
                    sess.query(EvolutionPolicyStateModel)
                    .filter(
                        EvolutionPolicyStateModel.tenant_id == self.tenant_id,
                        EvolutionPolicyStateModel.graph_id == graph_id,
                    )
                    .first()
                )
                if row is None:
                    row = EvolutionPolicyStateModel(
                        tenant_id=self.tenant_id,
                        graph_id=graph_id,
                        policy_version=max(0, int(policy_version)),
                        arms=arms or {},
                        lambda_calibration=lambda_calibration or {},
                        meta=meta or {},
                        updated_at=datetime.now(timezone.utc),
                    )
                    sess.add(row)
                else:
                    row.policy_version = max(0, int(policy_version))
                    row.arms = arms or {}
                    row.lambda_calibration = lambda_calibration or {}
                    row.meta = meta or {}
                    row.updated_at = datetime.now(timezone.utc)
                sess.flush()
                return True
        except Exception:  # nosec B110
            return False

    # =========================================================================
    # Meta metrics
    # =========================================================================

    def record_meta_metrics(
        self,
        graph_id: str,
        snapshot: MetaMetricSnapshot,
        session: Optional[Session] = None,
    ) -> UUID:
        """Persist one meta-metric row. Never raises (best effort)."""
        sess = session or self.session
        if sess is None:
            return UUID(int=0)
        try:
            with sess.begin_nested():
                model = EvolutionMetaMetricModel(
                    id=uuid4(),
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    ts=datetime.now(timezone.utc),
                    merge_usefulness=_clamp01(snapshot.merge_usefulness),
                    invention_utilization=_clamp01(snapshot.invention_utilization),
                    prune_regret=_clamp01(snapshot.prune_regret),
                    d_drift=float(snapshot.d_drift),
                    h_drift=float(snapshot.h_drift),
                    alerts=snapshot.alerts or {},
                    detail=snapshot.detail or {},
                )
                sess.add(model)
                sess.flush()
                return model.id
        except Exception:  # nosec B110
            return UUID(int=0)

    def get_latest_meta_metrics(
        self,
        graph_id: str,
        limit: int = 20,
        session: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent meta-metric rows (newest first)."""
        sess = session or self.session
        if sess is None:
            return []
        try:
            rows = (
                sess.query(EvolutionMetaMetricModel)
                .filter(
                    EvolutionMetaMetricModel.tenant_id == self.tenant_id,
                    EvolutionMetaMetricModel.graph_id == graph_id,
                )
                .order_by(desc(EvolutionMetaMetricModel.ts))
                .limit(max(1, min(200, int(limit))))
                .all()
            )
            return [row.to_dict() for row in rows]
        except Exception:  # nosec B110
            return []


__all__ = [
    "EvolutionOutcome",
    "MetaMetricSnapshot",
    "EvolutionLearningRepo",
]

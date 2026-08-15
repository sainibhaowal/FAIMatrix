"""Evolution policy learner (Phase 0032).

Replaces fixed evolution constants with values learned per graph from
measured outcomes, using contextual bandits (LinUCB) over discrete action
grids, plus Welford rolling calibration of the lambda threshold.

Contextual features (from the graph's own pre-cycle diagnostics):
    x = [1, R, N, D, H, node_count/1000]

Design constraints:
- Pure module (no DB) — persistence happens through EvolutionLearningRepo.
- Deterministic seeds for reproducibility; epsilon-greedy exploration.
- Hard bounds on every knob — learned values can never leave safe ranges.
- Fail-closed: any missing/corrupt state resolves to today's defaults so
  existing behavior is preserved bit-for-bit when learning is disabled.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# =============================================================================
# Discrete action grids per knob (learned values always within these ranges)
# =============================================================================

KNOB_GRIDS: Dict[str, List[float]] = {
    "merge_threshold": [0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98],
    "prune_similarity_threshold": [0.93, 0.95, 0.96, 0.97, 0.98, 0.99],
    "prune_min_age_days": [3.0, 5.0, 7.0, 10.0, 14.0, 21.0],
    "lambda_threshold": [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50],
}

KNOB_DEFAULTS: Dict[str, float] = {
    "merge_threshold": 0.95,
    "prune_similarity_threshold": 0.98,
    "prune_min_age_days": 7.0,
    "lambda_threshold": 0.30,
}

# How many cycles a knob needs before its bandit is trusted over the default.
MIN_VISITS_BEFORE_LEARNED: int = 5

# Minimum lambda samples before calibration replaces the bandit value.
MIN_LAMBDA_SAMPLES: int = 10

# Exploration: probability of picking a random grid value each cycle.
EXPLORATION_RATE: float = 0.10

# LinUCB ridge prior and exploration constants.
RIDGE_LAMBDA: float = 1.0
LINUCB_ALPHA: float = 0.6

# Contextual feature dimension: [1, R, N, D, H, node_count/1000].
FEATURE_DIM: int = 6

# Schema tag so future migrations can detect stale state.
POLICY_SCHEMA: str = "v2"

# Reward blend weights.
REWARD_W_REDUCTION: float = 0.5
REWARD_W_ENERGY: float = 0.3
REWARD_W_NOVELTY: float = 0.2


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _clamp01(value: float) -> float:
    return _clamp(value, 0.0, 1.0)


def _context_features(context: Optional[Dict[str, float]]) -> List[float]:
    """Build the LinUCB feature vector from a diagnostics context.

    x = [1, R, N, D, H, node_count/1000]. Missing fields are treated as 0.
    """
    c = context or {}
    return [
        1.0,
        _clamp01(float(c.get("R", 0.0) or 0.0)),
        _clamp01(float(c.get("N", 0.0) or 0.0)),
        _clamp01(float(c.get("D", 0.0) or 0.0)),
        _clamp01(float(c.get("H", 0.0) or 0.0)),
        _clamp01(float(c.get("node_count", 0.0) or 0.0) / 1000.0),
    ]


def _mat_mul_vec(matrix: List[List[float]], vec: List[float]) -> List[float]:
    return [
        sum(row[i] * vec[i] for i in range(len(vec)))
        for row in matrix
    ]


def _mat_inverse(matrix: List[List[float]]) -> List[List[float]]:
    """Gauss-Jordan matrix inverse (deterministic, no numpy).

    d <= 6 in practice. Singular matrices fall back to the ridge prior's
    inverse (I / RIDGE_LAMBDA), which keeps LinUCB well-posed.
    """
    n = len(matrix)
    if n == 0:
        return []
    aug = [
        list(matrix[i])
        + [1.0 if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot_row][col]) < 1e-12:
            # Singular: fall back to ridge prior inverse.
            inv = [
                [1.0 / RIDGE_LAMBDA if i == j else 0.0 for j in range(n)]
                for i in range(n)
            ]
            return inv
        if pivot_row != col:
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot = aug[col][col]
        aug[col] = [v / pivot for v in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor == 0.0:
                continue
            aug[row] = [
                rv - factor * cv for rv, cv in zip(aug[row], aug[col], strict=False)
            ]
    return [row[n:] for row in aug]


def _identity(d: int) -> List[List[float]]:
    return [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]


# =============================================================================
# Bandit arm state (LinUCB)
# =============================================================================


@dataclass
class ArmState:
    """LinUCB statistics for one knob (per-value ridge regressions)."""

    visits: Dict[str, int] = field(default_factory=dict)
    rewards: Dict[str, float] = field(default_factory=dict)
    A: Dict[str, List[List[float]]] = field(default_factory=dict)
    b: Dict[str, List[float]] = field(default_factory=dict)
    n_features: int = FEATURE_DIM
    alpha: float = LINUCB_ALPHA
    _default_knob: str = field(default="merge_threshold", repr=False)

    def __post_init__(self) -> None:
        # Normalize any legacy float keys to canonical grid keys.
        for key in list(self.visits.keys()):
            self.visits[str(key)] = self.visits.pop(key)

    def _ensure(self, key: str) -> None:
        if key not in self.A:
            self.A[key] = [
                [RIDGE_LAMBDA if i == j else 0.0 for j in range(self.n_features)]
                for i in range(self.n_features)
            ]
        if key not in self.b:
            self.b[key] = [0.0] * self.n_features

    def total_visits(self) -> int:
        return sum(self.visits.values())

    def key(self, value: float) -> str:
        return _fmt_key(value)

    def mean_reward(self, value: float) -> float:
        key = self.key(value)
        n = self.visits.get(key, 0)
        if n <= 0:
            return 0.0
        return self.rewards.get(key, 0.0) / n

    def ucb(self, value: float, features: List[float]) -> float:
        """LinUCB score for a grid value under the current context."""
        key = self.key(value)
        n = self.visits.get(key, 0)
        if n <= 0:
            return float("inf")  # explore every value at least once
        self._ensure(key)
        a_inv = _mat_inverse(self.A[key])
        theta = _mat_mul_vec(a_inv, self.b[key])
        mu = sum(x * t for x, t in zip(features, theta, strict=False))
        sigma2 = sum(
            x * cov for x, cov in zip(features, _mat_mul_vec(a_inv, features), strict=False)
        )
        return mu + self.alpha * math.sqrt(max(0.0, sigma2))

    def record(self, value: float, features: List[float], reward: float) -> None:
        """Online ridge update: A += x x^T, b += r x."""
        key = self.key(value)
        self.visits[key] = self.visits.get(key, 0) + 1
        self.rewards[key] = self.rewards.get(key, 0.0) + _clamp(
            reward, -1.0, 1.0
        )
        self._ensure(key)
        for i in range(self.n_features):
            for j in range(self.n_features):
                self.A[key][i][j] += features[i] * features[j]
            self.b[key][i] += _clamp(reward, -1.0, 1.0) * features[i]

    def selected(
        self,
        rng: random.Random,
        features: List[float],
        exploration: float,
    ) -> float:
        """Pick a grid value via LinUCB with epsilon exploration."""
        grid = list(KNOB_GRIDS.get(self._default_knob, []))
        if not grid:
            return 0.0
        if exploration > 0 and rng.random() < exploration:
            return rng.choice(grid)
        best = max(grid, key=lambda v: self.ucb(v, features))
        return best

    def to_dict(self) -> Dict[str, Any]:
        return {
            "visits": dict(self.visits),
            "rewards": dict(self.rewards),
            "A": {k: [list(row) for row in v] for k, v in self.A.items()},
            "b": {k: list(v) for k, v in self.b.items()},
            "n_features": self.n_features,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ArmState":
        if not isinstance(data, dict):
            return cls()
        return cls(
            visits=dict(data.get("visits") or {}),
            rewards=dict(data.get("rewards") or {}),
            A={
                str(k): [list(map(float, row)) for row in v]
                for k, v in (data.get("A") or {}).items()
            },
            b={str(k): list(map(float, v)) for k, v in (data.get("b") or {}).items()},
            n_features=max(1, int(data.get("n_features") or FEATURE_DIM)),
        )


def _fmt_key(value: float) -> str:
    """Stable string key for a knob value (avoids float formatting drift)."""
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


# =============================================================================
# Lambda calibration (Welford rolling statistics)
# =============================================================================


@dataclass
class LambdaCalibration:
    """Rolling mean/std of lambda values (Welford's online algorithm)."""

    n: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def record(self, value: float) -> None:
        self.n += 1
        delta = float(value) - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (float(value) - self.mean)

    def std(self) -> float:
        if self.n < 2:
            return 0.0
        return math.sqrt(max(0.0, self.m2 / (self.n - 1)))

    def threshold(self, offset_stds: float = 0.5) -> Optional[float]:
        """Calibrated lambda threshold from the graph's own history.

        threshold = mean + offset_stds * std (so "high pressure" is relative
        to this graph's baseline). Returns None until enough samples exist.
        """
        if self.n < MIN_LAMBDA_SAMPLES:
            return None
        return self.mean + offset_stds * self.std()

    def to_dict(self) -> Dict[str, Any]:
        return {"n": self.n, "mean": self.mean, "m2": self.m2}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "LambdaCalibration":
        if not isinstance(data, dict):
            return cls()
        return cls(
            n=int(data.get("n") or 0),
            mean=float(data.get("mean") or 0.0),
            m2=float(data.get("m2") or 0.0),
        )


# =============================================================================
# Resolved knobs + policy
# =============================================================================


@dataclass(frozen=True)
class ResolvedKnobs:
    """Knob values a single evolution cycle should run with."""

    merge_threshold: float
    prune_similarity_threshold: float
    prune_min_age_days: float
    lambda_threshold: float
    learned: bool = False
    source: str = "defaults"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merge_threshold": self.merge_threshold,
            "prune_similarity_threshold": self.prune_similarity_threshold,
            "prune_min_age_days": self.prune_min_age_days,
            "lambda_threshold": self.lambda_threshold,
            "learned": self.learned,
            "source": self.source,
        }


class EvolutionPolicy:
    """Per-graph policy learner (LinUCB bandits + lambda calibration)."""

    def __init__(
        self,
        *,
        graph_id: str,
        seed: int = 0,
        exploration: float = EXPLORATION_RATE,
        ucb_c: float = LINUCB_ALPHA,
    ):
        self.graph_id = graph_id
        self.exploration = _clamp(exploration, 0.0, 0.5)
        self.ucb_c = max(0.0, ucb_c)
        self.rng = random.Random(seed)
        self.arms: Dict[str, ArmState] = {}
        for knob in KNOB_GRIDS:
            self.arms[knob] = ArmState(_default_knob=knob, alpha=self.ucb_c)
        self.lambda_calibration = LambdaCalibration()
        self.version = 0
        self.last_context: Optional[Dict[str, float]] = None

    # ------------------------------------------------------------------
    # Persistence helpers (pure dict <-> state)
    # ------------------------------------------------------------------

    def to_state(self) -> Dict[str, Any]:
        """Serialize for storage (JSONB)."""
        return {
            "schema": POLICY_SCHEMA,
            "version": self.version,
            "arms": {k: a.to_dict() for k, a in self.arms.items()},
            "lambda_calibration": self.lambda_calibration.to_dict(),
        }

    @classmethod
    def from_state(
        cls,
        state: Optional[Dict[str, Any]],
        *,
        graph_id: str,
        seed: int = 0,
        exploration: float = EXPLORATION_RATE,
        ucb_c: float = LINUCB_ALPHA,
    ) -> "EvolutionPolicy":
        """Deserialize stored state. Corrupt/unknown schema → fresh policy.

        v1 states (UCB1 arms without feature matrices) keep their lambda
        calibration but reset arms — v1 rewards carry no context, so they
        cannot seed LinUCB.
        """
        policy = cls(graph_id=graph_id, seed=seed, exploration=exploration, ucb_c=ucb_c)
        if not isinstance(state, dict):
            return policy
        schema = state.get("schema")
        if schema not in (POLICY_SCHEMA, "v1"):
            return policy
        # Keep lambda calibration from either schema (format-compatible).
        policy.lambda_calibration = LambdaCalibration.from_dict(
            state.get("lambda_calibration")
        )
        if schema == "v1":
            return policy
        policy.version = max(0, int(state.get("version") or 0))
        raw_arms = state.get("arms") or {}
        for knob, data in raw_arms.items():
            if knob not in policy.arms:
                continue
            restored = ArmState.from_dict(data)
            restored._default_knob = knob  # type: ignore[attr-defined]
            restored.alpha = policy.ucb_c  # type: ignore[attr-defined]
            policy.arms[knob] = restored
        return policy

    # ------------------------------------------------------------------
    # Resolve knobs for a cycle
    # ------------------------------------------------------------------

    def resolve_knobs(
        self,
        context: Optional[Dict[str, float]] = None,
    ) -> ResolvedKnobs:
        """Pick knob values for the next cycle (LinUCB + epsilon exploration).

        Args:
            context: Pre-cycle diagnostics — keys R, N, D, H, node_count.
        """
        self.last_context = dict(context) if context else None
        features = _context_features(context)
        knobs: Dict[str, float] = {}
        for knob, arm in self.arms.items():
            if arm.total_visits() == 0:
                # Untried arm: keep the legacy default so fresh graphs behave
                # exactly as before learning existed.
                knobs[knob] = KNOB_DEFAULTS[knob]
                continue
            selected = arm.selected(self.rng, features, self.exploration)
            if selected == 0.0:
                selected = KNOB_DEFAULTS[knob]
            grid = KNOB_GRIDS[knob]
            nearest = min(grid, key=lambda v: abs(v - selected))
            knobs[knob] = nearest

        calibrated = self.lambda_calibration.threshold()
        if calibrated is not None:
            knobs["lambda_threshold"] = _clamp(
                calibrated,
                min(KNOB_GRIDS["lambda_threshold"]),
                max(KNOB_GRIDS["lambda_threshold"]),
            )

        learned = any(
            arm.total_visits() >= MIN_VISITS_BEFORE_LEARNED
            for arm in self.arms.values()
        )
        return ResolvedKnobs(
            merge_threshold=knobs["merge_threshold"],
            prune_similarity_threshold=knobs["prune_similarity_threshold"],
            prune_min_age_days=knobs["prune_min_age_days"],
            lambda_threshold=knobs["lambda_threshold"],
            learned=learned,
            source="bandit" if learned else "defaults",
        )

    # ------------------------------------------------------------------
    # Learning updates
    # ------------------------------------------------------------------

    def update_from_outcome(
        self,
        knobs: ResolvedKnobs,
        *,
        merges: int,
        prunes: int,
        r_before: float,
        r_after: float,
        n_before: float,
        n_after: float,
        e_before: float,
        e_after: float,
        lambda_after: float,
        retrieval_delta: Optional[float] = None,
        context: Optional[Dict[str, float]] = None,
    ) -> float:
        """Record one cycle's outcome, update bandits, return the reward.

        Args:
            context: Pre-cycle diagnostics used as LinUCB features
                (keys R, N, D, H, node_count).
        """
        reward = compute_reward(
            merges=merges,
            prunes=prunes,
            r_before=r_before,
            r_after=r_after,
            n_before=n_before,
            n_after=n_after,
            e_before=e_before,
            e_after=e_after,
            retrieval_delta=retrieval_delta,
        )
        features = _context_features(context)
        # Only learn when the cycle actually acted (noise-free signal).
        if merges + prunes > 0:
            self.arms["merge_threshold"].record(
                knobs.merge_threshold, features, reward
            )
            self.arms["prune_similarity_threshold"].record(
                knobs.prune_similarity_threshold, features, reward
            )
            self.arms["prune_min_age_days"].record(
                knobs.prune_min_age_days, features, reward
            )
        self.arms["lambda_threshold"].record(
            knobs.lambda_threshold, features, reward
        )
        self.lambda_calibration.record(lambda_after)
        self.version += 1
        return reward


def compute_reward(
    *,
    merges: int,
    prunes: int,
    r_before: float,
    r_after: float,
    n_before: float,
    n_after: float,
    e_before: float,
    e_after: float,
    retrieval_delta: Optional[float] = None,
) -> float:
    """Composite deterministic reward in [-1, 1].

    Reward = 0.5 * redundancy reduction
           + 0.3 * boundedness (energy) improvement
           + 0.2 * novelty retention
    When a retrieval probe delta is available it replaces half the weight.
    """
    r_red = _clamp01(
        (float(r_before) - float(r_after)) / max(0.05, float(r_before))
    )
    e_gain = _clamp01(
        (float(e_before) - float(e_after)) / max(0.05, float(e_before))
    )
    n_ret = _clamp01((float(n_after) - float(n_before)) / 2.0 + 0.5)

    base = (
        REWARD_W_REDUCTION * r_red
        + REWARD_W_ENERGY * e_gain
        + REWARD_W_NOVELTY * n_ret
    )

    if retrieval_delta is not None:
        ret_component = _clamp(retrieval_delta, -1.0, 1.0)
        base = 0.6 * base + 0.4 * _clamp01((ret_component + 1.0) / 2.0)

    # Mild penalty for cycling without net redundancy improvement.
    if merges + prunes > 0 and r_red < 0.01:
        base -= 0.05
    return _clamp(base, -1.0, 1.0)


__all__ = [
    "KNOB_GRIDS",
    "KNOB_DEFAULTS",
    "MIN_VISITS_BEFORE_LEARNED",
    "MIN_LAMBDA_SAMPLES",
    "EXPLORATION_RATE",
    "RIDGE_LAMBDA",
    "LINUCB_ALPHA",
    "FEATURE_DIM",
    "POLICY_SCHEMA",
    "ArmState",
    "LambdaCalibration",
    "ResolvedKnobs",
    "EvolutionPolicy",
    "compute_reward",
    "_context_features",
]

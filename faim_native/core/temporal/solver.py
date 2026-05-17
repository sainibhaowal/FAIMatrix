"""Temporal constraint solver for reasoning.

Handles time-based reasoning: "before", "after", "during", "within".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, cast


class TemporalRelation(Enum):
    """Types of temporal relations."""

    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    OVERLAPS = "overlaps"
    CONTAINS = "contains"
    EQUALS = "equals"


@dataclass
class TemporalConstraint:
    """A temporal constraint between two events."""

    event_a: str
    event_b: str
    relation: TemporalRelation
    confidence: float = 1.0


class TemporalSolver:
    """
    Solves temporal constraints to build coherent timelines.

    Handles:
    - Event ordering
    - Duration constraints
    - Deadline checking
    - Temporal conflict detection
    """

    def __init__(self, reference_time: Optional[datetime] = None):
        self.reference_time = reference_time or datetime.utcnow()
        self.constraints: List[TemporalConstraint] = []
        self.event_times: Dict[str, datetime] = {}

    def add_constraint(
        self,
        event_a: str,
        event_b: str,
        relation: TemporalRelation,
        confidence: float = 1.0,
    ) -> None:
        """Add a temporal constraint."""
        self.constraints.append(
            TemporalConstraint(
                event_a=event_a,
                event_b=event_b,
                relation=relation,
                confidence=confidence,
            )
        )

    def set_event_time(self, event: str, time: datetime) -> None:
        """Set absolute time for an event."""
        self.event_times[event] = time

    def check_deadline(
        self,
        deadline_event: str,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Check if a deadline is approaching or passed.

        Returns:
            Status: "passed", "approaching", "distant", "unknown"
            Days remaining
        """
        if deadline_event not in self.event_times:
            return {"status": "unknown", "days_remaining": None}

        deadline = self.event_times[deadline_event]
        now = current_time or self.reference_time

        days_remaining = (deadline - now).days

        if days_remaining < 0:
            status = "passed"
        elif days_remaining <= 7:
            status = "approaching"
        else:
            status = "distant"

        return {
            "status": status,
            "days_remaining": days_remaining,
            "deadline": deadline.isoformat(),
            "urgency": (
                "high"
                if days_remaining < 3
                else "medium" if days_remaining < 7 else "low"
            ),
        }

    def infer_temporal_relationship(
        self,
        event_a: str,
        event_b: str,
    ) -> Optional[TemporalConstraint]:
        """Infer relationship between two events based on known times."""

        if event_a not in self.event_times or event_b not in self.event_times:
            return None

        time_a = self.event_times[event_a]
        time_b = self.event_times[event_b]

        if time_a < time_b:
            relation = TemporalRelation.BEFORE
        elif time_a > time_b:
            relation = TemporalRelation.AFTER
        else:
            relation = TemporalRelation.EQUALS

        return TemporalConstraint(
            event_a=event_a,
            event_b=event_b,
            relation=relation,
            confidence=1.0,
        )

    def detect_conflicts(self) -> List[Dict[str, Any]]:
        """Detect contradictions in temporal constraints."""

        conflicts = []

        # Check all constraint pairs
        for i, c1 in enumerate(self.constraints):
            for c2 in self.constraints[i + 1 :]:
                # Same events but different relations
                if c1.event_a == c2.event_a and c1.event_b == c2.event_b:
                    if c1.relation != c2.relation:
                        conflicts.append(
                            {
                                "type": "contradictory_constraints",
                                "events": (c1.event_a, c1.event_b),
                                "constraint_1": c1.relation.value,
                                "constraint_2": c2.relation.value,
                            }
                        )

                # Transitive inconsistency
                # If A before B and B before C, but A after C: conflict
                if c1.event_b == c2.event_a:
                    # c1: A->B, c2: B->C
                    # Check if there's a constraint A->C
                    implied_relation = self._get_implied_transitive(c1, c2)

                    for c3 in self.constraints:
                        if c3.event_a == c1.event_a and c3.event_b == c2.event_b:
                            if c3.relation != implied_relation:
                                conflicts.append(
                                    {
                                        "type": "transitive_inconsistency",
                                        "events": (c1.event_a, c2.event_b),
                                        "expected": implied_relation.value,
                                        "found": c3.relation.value,
                                    }
                                )

        return conflicts

    def _get_implied_transitive(
        self,
        c1: TemporalConstraint,
        c2: TemporalConstraint,
    ) -> TemporalRelation:
        """Get implied transitive relation."""
        # A before B, B before C -> A before C
        if (
            c1.relation == TemporalRelation.BEFORE
            and c2.relation == TemporalRelation.BEFORE
        ):
            return TemporalRelation.BEFORE

        # A after B, B after C -> A after C
        if (
            c1.relation == TemporalRelation.AFTER
            and c2.relation == TemporalRelation.AFTER
        ):
            return TemporalRelation.AFTER

        return TemporalRelation.OVERLAPS  # Default

    def build_timeline(self, events: List[str]) -> List[Dict[str, Any]]:
        """
        Build ordered timeline from events.

        Returns events in chronological order with inferred positions.
        """
        # Get events with times
        timed_events = []
        untimed_events = []

        for event in events:
            if event in self.event_times:
                timed_events.append(
                    {
                        "event": event,
                        "time": self.event_times[event],
                        "position": "absolute",
                    }
                )
            else:
                untimed_events.append(
                    {
                        "event": event,
                        "time": None,
                        "position": "relative",
                    }
                )

        # Sort timed events
        timed_events.sort(key=lambda e: cast(datetime, e["time"]))

        # Position untimed events relative to constraints
        for untimed in untimed_events:
            event = untimed["event"]

            # Find constraints involving this event
            before_events = []
            after_events = []

            for constraint in self.constraints:
                if (
                    constraint.event_a == event
                    and constraint.relation == TemporalRelation.BEFORE
                ):
                    after_events.append(constraint.event_b)
                elif (
                    constraint.event_b == event
                    and constraint.relation == TemporalRelation.BEFORE
                ):
                    before_events.append(constraint.event_a)

            # Position between before and after
            if before_events and after_events:
                # Find middle position
                before_max = max(
                    (e for e in timed_events if e["event"] in before_events),
                    key=lambda x: (
                        cast(datetime, x["time"]) if x.get("time") else datetime.min
                    ),
                    default=None,
                )
                after_min = min(
                    (e for e in timed_events if e["event"] in after_events),
                    key=lambda x: (
                        cast(datetime, x["time"]) if x.get("time") else datetime.max
                    ),
                    default=None,
                )

                if (
                    before_max
                    and after_min
                    and before_max["time"]
                    and after_min["time"]
                ):
                    # Position between
                    mid_time = (
                        cast(datetime, before_max["time"])
                        + (
                            cast(datetime, after_min["time"])
                            - cast(datetime, before_max["time"])
                        )
                        / 2
                    )
                    untimed["inferred_time"] = mid_time
                    untimed["position"] = (
                        f"between {before_max['event']} and {after_min['event']}"
                    )

            elif before_events:
                untimed["position"] = f"after {', '.join(before_events)}"

            elif after_events:
                untimed["position"] = f"before {', '.join(after_events)}"

        # Combine and sort
        all_events = timed_events + untimed_events

        return [
            {
                "event": e["event"],
                "time": e["time"].isoformat() if e.get("time") else None,
                "position": e.get("position", "unknown"),
                "inferred_time": (
                    e.get("inferred_time").isoformat()
                    if e.get("inferred_time")
                    else None
                ),
            }
            for e in all_events
        ]

    def validate_query_temporal(
        self,
        query_text: str,
        relevant_events: List[str],
    ) -> Dict[str, Any]:
        """
        Validate temporal aspects of a query.

        Checks:
        - Are all referenced events known?
        - Are temporal relations consistent?
        - Are there any deadline concerns?
        """
        validation = {
            "valid": True,
            "unknown_events": [],
            "conflicts": [],
            "deadlines": [],
            "warnings": [],
        }

        # Check for unknown events
        for event in relevant_events:
            if event not in self.event_times:
                validation["unknown_events"].append(event)

        # Detect conflicts
        conflicts = self.detect_conflicts()
        if conflicts:
            validation["conflicts"] = conflicts
            validation["valid"] = False

        # Check for deadlines
        deadline_keywords = ["deadline", "due", "by when", "when is"]
        if any(kw in query_text.lower() for kw in deadline_keywords):
            for event in relevant_events:
                deadline_check = self.check_deadline(event)
                if deadline_check["status"] != "unknown":
                    validation["deadlines"].append(
                        {
                            "event": event,
                            "check": deadline_check,
                        }
                    )

        return validation

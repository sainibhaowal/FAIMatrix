"""Cross-galaxy synthesis engine.

Finds connections and synthesizes insights across multiple documents/galaxies.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

# Import cognitive typing for color/semantic matching
try:
    from faim.Faim_Native.core.cognitive.cognitive_typing import CognitiveType
except (ImportError, RuntimeError, ModuleNotFoundError):
    CognitiveType = Any


@dataclass
class CrossGalaxyInsight:
    """
    An insight synthesized from multiple galaxies.

    Represents a connection or pattern found across documents.
    """

    insight_id: str
    insight_type: (
        str  # "correlation", "causal_chain", "trend", "contradiction", "synthesis"
    )

    # What we discovered
    description: str
    confidence: float

    # Source galaxies
    primary_galaxy: str
    supporting_galaxies: List[str]

    # Supporting evidence
    evidence_nodes: List[Dict[str, Any]]

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "description": self.description,
            "confidence": self.confidence,
            "primary_galaxy": self.primary_galaxy,
            "supporting_galaxies": self.supporting_galaxies,
            "evidence_nodes": self.evidence_nodes,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class CrossGalaxySynthesizer:
    """
    Synthesizes insights across multiple galaxies (documents).

    Capabilities:
    - Find correlations between facts in different documents
    - Build causal chains across document boundaries
    - Detect trends spanning multiple time periods
    - Identify contradictions across sources
    - Create unified summaries
    """

    def __init__(self, session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self._galaxy_cache: Dict[str, List[Dict]] = {}

    def synthesize(
        self,
        galaxy_ids: List[str],
        topic: Optional[str] = None,
        max_galaxies: int = 5,
    ) -> List[CrossGalaxyInsight]:
        """
        Main synthesis method: find all insights across galaxies.

        Args:
            galaxy_ids: List of galaxy (document) IDs to analyze
            topic: Optional topic to focus on
            max_galaxies: Maximum galaxies to process

        Returns:
            List of synthesized insights
        """
        # Limit galaxies for performance
        galaxy_ids = galaxy_ids[:max_galaxies]

        # Fetch all relevant nodes
        galaxy_nodes = self._fetch_galaxy_data(galaxy_ids, topic)

        insights = []

        # Run various synthesis algorithms
        insights.extend(self._find_correlations(galaxy_nodes))
        insights.extend(self._find_temporal_trends(galaxy_nodes))
        insights.extend(self._find_causal_chains(galaxy_nodes))
        insights.extend(self._find_contradictions(galaxy_nodes))
        insights.extend(self._create_unified_summary(galaxy_nodes, topic))

        # Sort by confidence
        insights.sort(key=lambda i: i.confidence, reverse=True)

        return insights

    def _fetch_galaxy_data(
        self,
        galaxy_ids: List[str],
        topic: Optional[str],
    ) -> Dict[str, List[Dict]]:
        """Fetch node data from multiple galaxies."""

        galaxy_nodes = {}

        for galaxy_id in galaxy_ids:
            if galaxy_id in self._galaxy_cache:
                nodes = self._galaxy_cache[galaxy_id]
            else:
                # Query database
                nodes = self._query_galaxy_nodes(galaxy_id, topic)
                self._galaxy_cache[galaxy_id] = nodes

            galaxy_nodes[galaxy_id] = nodes

        return galaxy_nodes

    def _query_galaxy_nodes(
        self,
        galaxy_id: str,
        topic: Optional[str],
    ) -> List[Dict]:
        """Query nodes from a specific galaxy.

        Uses the native ``nodes`` table joined to the Representation V2
        sidecar (``node_repr_v2``) for normalized text. Best effort: any
        failure yields an empty list rather than raising.
        """

        try:
            from store.pg.models_faim import NodeModel, NodeRepresentationV2Model

            query = self.session.query(NodeModel).filter(
                NodeModel.tenant_id == self.tenant_id,
                NodeModel.galaxy_id == galaxy_id,
            )

            if topic:
                # Filter by topic relevance against the representation text.
                rows = query.limit(500).all()
                node_ids = [r.node_id for r in rows]

                repr_rows = []
                if node_ids:
                    repr_rows = (
                        self.session.query(NodeRepresentationV2Model)
                        .filter(
                            NodeRepresentationV2Model.tenant_id == self.tenant_id,
                            NodeRepresentationV2Model.node_id.in_(node_ids),
                        )
                        .all()
                    )
                topic_lower = topic.lower()
                by_id = {r.node_id: r for r in rows}
                topic_nodes = set()
                for r in repr_rows:
                    if topic_lower in (r.normalized_text or "").lower():
                        topic_nodes.add(r.node_id)
                rows = [by_id[nid] for nid in node_ids if nid in topic_nodes]

                models = rows
            else:
                models = query.limit(1000).all()

            # Load representation text for every node (sidecar join).
            repr_by_id: Dict[str, str] = {}
            if models:
                try:
                    repr_rows = (
                        self.session.query(NodeRepresentationV2Model)
                        .filter(
                            NodeRepresentationV2Model.tenant_id == self.tenant_id,
                            NodeRepresentationV2Model.node_id.in_(
                                [m.node_id for m in models]
                            ),
                        )
                        .all()
                    )
                    repr_by_id = {
                        str(r.node_id): r.normalized_text or ""
                        for r in repr_rows
                    }
                except Exception:
                    repr_by_id = {}

            return [
                {
                    "node_id": str(m.node_id),
                    "text": repr_by_id.get(
                        str(m.node_id),
                        (m.anchor_json or {}).get("text", "")
                        or (m.anchor_json or {}).get("canonical", ""),
                    ),
                    "cognitive_type": getattr(m, "cognitive_type", None),
                    "galaxy_id": galaxy_id,
                    "timestamp": getattr(m, "timestamp", None),
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in models
            ]

        except Exception:
            return []

    def _find_correlations(
        self,
        galaxy_nodes: Dict[str, List[Dict]],
    ) -> List[CrossGalaxyInsight]:
        """Find correlated facts across galaxies."""

        insights = []

        # Build index of concepts by galaxy
        concept_index = defaultdict(list)

        for galaxy_id, nodes in galaxy_nodes.items():
            for node in nodes:
                # Extract key concepts (simple keyword extraction)
                concepts = self._extract_concepts(node.get("text", ""))
                for concept in concepts:
                    concept_index[concept].append(
                        {
                            "galaxy": galaxy_id,
                            "node": node,
                        }
                    )

        # Find concepts appearing in multiple galaxies
        for concept, occurrences in concept_index.items():
            galaxies = set(o["galaxy"] for o in occurrences)

            if len(galaxies) >= 2:
                # Found a correlation!
                insight = CrossGalaxyInsight(
                    insight_id=f"corr_{concept[:20]}",
                    insight_type="correlation",
                    description=f"'{concept}' appears in {len(galaxies)} different documents",
                    confidence=min(0.95, 0.5 + (len(galaxies) * 0.15)),
                    primary_galaxy=occurrences[0]["galaxy"],
                    supporting_galaxies=list(galaxies - {occurrences[0]["galaxy"]}),
                    evidence_nodes=[o["node"] for o in occurrences],
                    metadata={
                        "concept": concept,
                        "occurrence_count": len(occurrences),
                        "galaxy_count": len(galaxies),
                    },
                )
                insights.append(insight)

        return insights

    def _find_temporal_trends(
        self,
        galaxy_nodes: Dict[str, List[Dict]],
    ) -> List[CrossGalaxyInsight]:
        """Find trends across time from multiple galaxies."""

        insights = []

        # Collect temporal facts
        temporal_facts = []

        for galaxy_id, nodes in galaxy_nodes.items():
            for node in nodes:
                if node.get("timestamp"):
                    temporal_facts.append(
                        {
                            "galaxy": galaxy_id,
                            "node": node,
                            "timestamp": node["timestamp"],
                        }
                    )

        if len(temporal_facts) < 3:
            return []

        # Sort by time
        temporal_facts.sort(key=lambda x: x["timestamp"])

        # Group by concept (simplified: use text similarity)
        concept_groups = self._group_by_concept(temporal_facts)

        for concept, facts in concept_groups.items():
            if len(facts) >= 3:
                # Detect trend
                first_val = self._extract_value(facts[0]["node"]["text"])
                last_val = self._extract_value(facts[-1]["node"]["text"])

                if first_val and last_val:
                    change = self._calculate_change(first_val, last_val)

                    if change:
                        insight = CrossGalaxyInsight(
                            insight_id=f"trend_{concept[:20]}",
                            insight_type="trend",
                            description=f"{concept} shows {change['direction']} trend: {change['description']}",
                            confidence=min(0.90, 0.6 + (len(facts) * 0.1)),
                            primary_galaxy=facts[0]["galaxy"],
                            supporting_galaxies=list(
                                set(f["galaxy"] for f in facts[1:])
                            ),
                            evidence_nodes=[f["node"] for f in facts],
                            metadata={
                                "concept": concept,
                                "trend_type": change["direction"],
                                "start_value": first_val,
                                "end_value": last_val,
                                "data_points": len(facts),
                            },
                        )
                        insights.append(insight)

        return insights

    def _find_causal_chains(
        self,
        galaxy_nodes: Dict[str, List[Dict]],
    ) -> List[CrossGalaxyInsight]:
        """Find causal relationships spanning galaxies."""

        insights = []

        # Look for cause-effect patterns in different galaxies
        cause_keywords = ["caused", "led to", "resulted in", "because", "due to"]
        effect_keywords = ["impact", "effect", "consequence", "result"]

        causes: List[Dict[str, Any]] = []
        effects: List[Dict[str, Any]] = []

        for galaxy_id, nodes in galaxy_nodes.items():
            for node in nodes:
                text = node.get("text", "").lower()

                if any(kw in text for kw in cause_keywords):
                    causes.append({"galaxy": galaxy_id, "node": node})

                if any(kw in text for kw in effect_keywords):
                    effects.append({"galaxy": galaxy_id, "node": node})

        # Match causes to effects (simplified: shared concepts)
        for cause in causes:
            cause_concepts = self._extract_concepts(cause["node"]["text"])

            for effect in effects:
                if effect["galaxy"] == cause["galaxy"]:
                    continue  # Same galaxy, not cross-galaxy

                effect_concepts = self._extract_concepts(effect["node"]["text"])

                # Check for concept overlap
                overlap = cause_concepts & effect_concepts

                if overlap:
                    shared = list(overlap)[0]
                    insight = CrossGalaxyInsight(
                        insight_id=f"causal_{shared[:20]}",
                        insight_type="causal_chain",
                        description=f"'{shared}' links cause in {cause['galaxy']} to effect in {effect['galaxy']}",
                        confidence=0.70,  # Lower confidence for inferred causality
                        primary_galaxy=cause["galaxy"],
                        supporting_galaxies=[effect["galaxy"]],
                        evidence_nodes=[cause["node"], effect["node"]],
                        metadata={
                            "shared_concept": shared,
                            "cause_galaxy": cause["galaxy"],
                            "effect_galaxy": effect["galaxy"],
                        },
                    )
                    insights.append(insight)

        return insights

    def _find_contradictions(
        self,
        galaxy_nodes: Dict[str, List[Dict]],
    ) -> List[CrossGalaxyInsight]:
        """Find contradictions between galaxies."""

        insights = []

        # Group by concept
        concept_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for galaxy_id, nodes in galaxy_nodes.items():
            for node in nodes:
                # Extract the main subject
                subject = self._extract_subject(node.get("text", ""))
                if subject:
                    concept_groups[subject].append(
                        {
                            "galaxy": galaxy_id,
                            "node": node,
                        }
                    )

        # Check for contradictory values
        for concept, occurrences in concept_groups.items():
            if len(occurrences) >= 2:
                values = []
                for occ in occurrences:
                    val = self._extract_value(occ["node"]["text"])
                    if val:
                        values.append(
                            {
                                "value": val,
                                "galaxy": occ["galaxy"],
                                "node": occ["node"],
                            }
                        )

                # Check if values conflict
                if len(values) >= 2:
                    conflicts = self._detect_conflicts(values)

                    for conflict in conflicts:
                        insight = CrossGalaxyInsight(
                            insight_id=f"contra_{concept[:20]}",
                            insight_type="contradiction",
                            description=f"Conflicting values for '{concept}': {conflict['description']}",
                            confidence=0.85,
                            primary_galaxy=conflict["galaxies"][0],
                            supporting_galaxies=conflict["galaxies"][1:],
                            evidence_nodes=[v["node"] for v in conflict["values"]],
                            metadata={
                                "concept": concept,
                                "conflict_type": conflict["type"],
                                "values": [v["value"] for v in conflict["values"]],
                            },
                        )
                        insights.append(insight)

        return insights

    def _create_unified_summary(
        self,
        galaxy_nodes: Dict[str, List[Dict]],
        topic: Optional[str],
    ) -> List[CrossGalaxyInsight]:
        """Create a unified summary across all galaxies.

        Only emits an insight when at least one galaxy contributed nodes;
        an empty synthesis never fabricates a placeholder summary.
        """

        # Count cognitive types across galaxies
        type_counts = defaultdict(lambda: defaultdict(int))

        for galaxy_id, nodes in galaxy_nodes.items():
            for node in nodes:
                cog_type = node.get("cognitive_type", "unknown")
                type_counts[galaxy_id][cog_type] += 1

        # Build summary description
        total_nodes = sum(len(nodes) for nodes in galaxy_nodes.values())
        galaxy_count = len(galaxy_nodes)

        if total_nodes == 0:
            return []

        description = f"Analyzed {total_nodes} facts across {galaxy_count} documents"

        if topic:
            description += f" related to '{topic}'"

        insight = CrossGalaxyInsight(
            insight_id="summary_unified",
            insight_type="synthesis",
            description=description,
            confidence=0.90,
            primary_galaxy=list(galaxy_nodes.keys())[0] if galaxy_nodes else "",
            supporting_galaxies=(
                list(galaxy_nodes.keys())[1:] if len(galaxy_nodes) > 1 else []
            ),
            evidence_nodes=[],  # Too many to list
            metadata={
                "total_nodes": total_nodes,
                "galaxy_count": galaxy_count,
                "topic": topic,
                "cognitive_type_distribution": dict(type_counts),
            },
        )

        return [insight]

    # Helper methods
    def _extract_concepts(self, text: str) -> Set[str]:
        """Extract key concepts from text."""
        # Simple implementation: extract capitalized phrases and numbers
        import re

        # Find capitalized terms (likely entities)
        capitalized = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)

        # Find money amounts
        money = re.findall(r"\$[\d,.]+[KMB]?", text)

        # Find dates
        dates = re.findall(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b",
            text,
        )

        return set(capitalized + money + dates)

    def _extract_value(self, text: str) -> Optional[str]:
        """Extract a numeric or categorical value from text."""
        import re

        # Money values
        money_match = re.search(r"\$([\d,.]+[KMB]?)", text)
        if money_match:
            return f"${money_match.group(1)}"

        # Percentages
        percent_match = re.search(r"(\d+(?:\.\d+)?)%", text)
        if percent_match:
            return f"{percent_match.group(1)}%"

        # Numbers
        number_match = re.search(r"\b(\d+(?:,\d+)*)\b", text)
        if number_match:
            return number_match.group(1)

        return None

    def _extract_subject(self, text: str) -> Optional[str]:
        """Extract the main subject of a sentence."""
        # Simple: first noun phrase
        words = text.split()
        if words:
            # Skip stop words
            stop_words = {"the", "a", "an", "is", "are", "was", "were"}
            for word in words[:5]:
                clean = word.lower().strip(",.!?")
                if clean not in stop_words and len(clean) > 3:
                    return clean.capitalize()
        return None

    def _group_by_concept(self, facts: List[Dict]) -> Dict[str, List[Dict]]:
        """Group facts by shared concept."""
        groups = defaultdict(list)

        for fact in facts:
            concepts = self._extract_concepts(fact["node"]["text"])
            for concept in concepts:
                groups[concept].append(fact)

        return dict(groups)

    def _calculate_change(self, first: str, last: str) -> Optional[Dict]:
        """Calculate change between two values."""
        # Try to parse as numbers
        try:
            # Remove $ and %
            f_clean = first.replace("$", "").replace("%", "").replace(",", "")
            l_clean = last.replace("$", "").replace("%", "").replace(",", "")

            # Handle K/M/B suffixes
            def parse_val(v):
                v = v.upper()
                if v.endswith("K"):
                    return float(v[:-1]) * 1000
                elif v.endswith("M"):
                    return float(v[:-1]) * 1000000
                elif v.endswith("B"):
                    return float(v[:-1]) * 1000000000
                return float(v)

            f_num = parse_val(f_clean)
            l_num = parse_val(l_clean)

            if f_num == 0:
                return None

            pct_change = ((l_num - f_num) / f_num) * 100

            if pct_change > 0:
                direction = "increasing"
            elif pct_change < 0:
                direction = "decreasing"
            else:
                direction = "stable"

            return {
                "direction": direction,
                "percent_change": round(pct_change, 1),
                "description": f"{abs(pct_change):.1f}% {direction}",
            }

        except Exception:
            return None

    def _detect_conflicts(self, values: List[Dict]) -> List[Dict]:
        """Detect conflicting values."""
        conflicts = []

        # Compare all pairs
        for i, v1 in enumerate(values):
            for v2 in values[i + 1 :]:
                if v1["value"] != v2["value"]:
                    conflicts.append(
                        {
                            "type": "value_mismatch",
                            "description": f"{v1['value']} vs {v2['value']}",
                            "values": [v1, v2],
                            "galaxies": [v1["galaxy"], v2["galaxy"]],
                        }
                    )

        return conflicts

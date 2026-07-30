"""Representation V2 repository.

Additive sparse lexical-semantic sidecar storage and scoring.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from uuid import UUID

from sqlalchemy import and_, asc
from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.core.query.lexical_scorer import compute_lexical_score
    from faim.Faim_Native.encoding.representation_v2 import RepresentationV2
    from faim.Faim_Native.store.pg.models_faim import (
        GraphRepresentationStatsModel,
        NodeModel,
        NodeRepresentationV2Model,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.query.lexical_scorer import compute_lexical_score
    from encoding.representation_v2 import RepresentationV2

    from store.pg.models_faim import (
        GraphRepresentationStatsModel,
        NodeModel,
        NodeRepresentationV2Model,
    )


CHANNELS: Tuple[str, ...] = (
    "word",
    "phrase",
    "skip",
    "entity",
    "time",
    "layout",
    "semantic_phrase",
    "concept",
    "morphology",
    "alias",
    "translit",
    "stem_family",
    "relation",
    "value",
    "temporal",
)


class RepresentationRepo:
    """Repository for Representation V2 sidecar data."""

    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    def upsert_node_representation(
        self,
        graph_id: str,
        node_id: UUID,
        representation: RepresentationV2,
    ) -> str:
        """Upsert Representation V2 data for a node.

        Returns:
            "inserted", "updated", or "unchanged"
        """
        existing = (
            self.session.query(NodeRepresentationV2Model)
            .filter(
                NodeRepresentationV2Model.node_id == node_id,
                NodeRepresentationV2Model.tenant_id == self.tenant_id,
                NodeRepresentationV2Model.graph_id == graph_id,
            )
            .first()
        )
        now = datetime.now(timezone.utc)

        if existing and existing.repr_hash == representation.repr_hash:
            return "unchanged"

        if existing:
            existing.repr_hash = representation.repr_hash
            existing.normalized_text = representation.normalized_text
            existing.word_counts = dict(representation.word_counts)
            existing.phrase_counts = dict(representation.phrase_counts)
            existing.skip_counts = dict(representation.skip_counts)
            existing.entity_tokens = list(representation.entity_tokens)
            existing.time_tokens = list(representation.time_tokens)
            existing.layout_tokens = list(representation.layout_tokens)
            existing.semantic_phrase_counts = dict(
                representation.semantic_phrase_counts or {}
            )
            existing.concept_counts = dict(representation.concept_counts or {})
            existing.morphology_counts = dict(representation.morphology_counts or {})
            existing.alias_families = list(representation.alias_families or ())
            existing.transliterated_tokens = list(
                representation.transliterated_tokens or ()
            )
            existing.stem_families = list(representation.stem_families or ())
            existing.relation_cues = list(representation.relation_cues or ())
            existing.value_cues = list(representation.value_cues or ())
            existing.temporal_cues = list(representation.temporal_cues or ())
            existing.channel_lengths = dict(representation.channel_lengths)
            existing.updated_at = now
            self.session.flush()
            self.rebuild_graph_stats(graph_id)
            return "updated"

        row = NodeRepresentationV2Model(
            node_id=node_id,
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            repr_hash=representation.repr_hash,
            normalized_text=representation.normalized_text,
            word_counts=dict(representation.word_counts),
            phrase_counts=dict(representation.phrase_counts),
            skip_counts=dict(representation.skip_counts),
            entity_tokens=list(representation.entity_tokens),
            time_tokens=list(representation.time_tokens),
            layout_tokens=list(representation.layout_tokens),
            semantic_phrase_counts=dict(representation.semantic_phrase_counts or {}),
            concept_counts=dict(representation.concept_counts or {}),
            morphology_counts=dict(representation.morphology_counts or {}),
            alias_families=list(representation.alias_families or ()),
            transliterated_tokens=list(representation.transliterated_tokens or ()),
            stem_families=list(representation.stem_families or ()),
            relation_cues=list(representation.relation_cues or ()),
            value_cues=list(representation.value_cues or ()),
            temporal_cues=list(representation.temporal_cues or ()),
            channel_lengths=dict(representation.channel_lengths),
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        self.session.flush()
        self._incremental_update_graph_stats(graph_id, representation)
        return "inserted"

    def list_by_node_ids(
        self,
        graph_id: str,
        node_ids: Sequence[UUID],
    ) -> List[NodeRepresentationV2Model]:
        if not node_ids:
            return []
        return (
            self.session.query(NodeRepresentationV2Model)
            .join(
                NodeModel,
                and_(
                    NodeModel.node_id == NodeRepresentationV2Model.node_id,
                    NodeModel.tenant_id == NodeRepresentationV2Model.tenant_id,
                    NodeModel.graph_id == NodeRepresentationV2Model.graph_id,
                ),
            )
            .filter(
                NodeRepresentationV2Model.tenant_id == self.tenant_id,
                NodeRepresentationV2Model.graph_id == graph_id,
                NodeRepresentationV2Model.node_id.in_(list(node_ids)),
            )
            .order_by(asc(NodeRepresentationV2Model.node_id))
            .all()
        )

    def list_all(self, graph_id: str) -> List[NodeRepresentationV2Model]:
        return (
            self.session.query(NodeRepresentationV2Model)
            .join(
                NodeModel,
                and_(
                    NodeModel.node_id == NodeRepresentationV2Model.node_id,
                    NodeModel.tenant_id == NodeRepresentationV2Model.tenant_id,
                    NodeModel.graph_id == NodeRepresentationV2Model.graph_id,
                ),
            )
            .filter(
                NodeRepresentationV2Model.tenant_id == self.tenant_id,
                NodeRepresentationV2Model.graph_id == graph_id,
            )
            .order_by(asc(NodeRepresentationV2Model.node_id))
            .all()
        )

    def top_k_lexical(
        self,
        graph_id: str,
        query_repr: RepresentationV2,
        k: int = 200,
    ) -> List[Tuple[UUID, float]]:
        scores = self.score_all(graph_id, query_repr)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], str(item[0])))
        return ranked[:k]

    def score_all(
        self,
        graph_id: str,
        query_repr: RepresentationV2,
    ) -> Dict[UUID, float]:
        rows = self.list_all(graph_id)
        if not rows:
            return {}
        stats = self.get_graph_stats(graph_id)
        scores: Dict[UUID, float] = {}
        for row in rows:
            doc_repr = self._row_to_repr(row)
            score, _components = compute_lexical_score(query_repr, doc_repr, stats)
            scores[row.node_id] = score
        return scores

    def score_node_ids(
        self,
        graph_id: str,
        query_repr: RepresentationV2,
        node_ids: Sequence[UUID],
    ) -> Dict[UUID, Tuple[float, Dict[str, float]]]:
        rows = self.list_by_node_ids(graph_id, node_ids)
        if not rows:
            return {}
        stats = self.get_graph_stats(graph_id)
        scored: Dict[UUID, Tuple[float, Dict[str, float]]] = {}
        for row in rows:
            doc_repr = self._row_to_repr(row)
            scored[row.node_id] = compute_lexical_score(query_repr, doc_repr, stats)
        return scored

    def get_graph_stats(self, graph_id: str) -> Dict[str, Dict[str, object]]:
        rows = (
            self.session.query(GraphRepresentationStatsModel)
            .filter(
                GraphRepresentationStatsModel.tenant_id == self.tenant_id,
                GraphRepresentationStatsModel.graph_id == graph_id,
            )
            .order_by(asc(GraphRepresentationStatsModel.channel))
            .all()
        )
        if not rows:
            self.rebuild_graph_stats(graph_id)
            rows = (
                self.session.query(GraphRepresentationStatsModel)
                .filter(
                    GraphRepresentationStatsModel.tenant_id == self.tenant_id,
                    GraphRepresentationStatsModel.graph_id == graph_id,
                )
                .order_by(asc(GraphRepresentationStatsModel.channel))
                .all()
            )
        return {
            row.channel: {
                "doc_count": row.doc_count,
                "avg_len": row.avg_len,
                "df_map": row.df_map or {},
            }
            for row in rows
        }

    def rebuild_graph_stats(self, graph_id: str) -> None:
        rows = self.list_all(graph_id)
        stats: Dict[str, Dict[str, object]] = {
            channel: {"doc_count": 0, "avg_len": 0.0, "df_map": {}}
            for channel in CHANNELS
        }

        if rows:
            lengths_sum = {channel: 0 for channel in CHANNELS}
            for row in rows:
                repr_data = self._row_to_repr(row)
                for channel in CHANNELS:
                    stats[channel]["doc_count"] = int(stats[channel]["doc_count"]) + 1  # type: ignore[call-overload]
                    lengths_sum[channel] += int(
                        repr_data.channel_lengths.get(channel, 0)
                    )

                for channel, terms in self._repr_df_terms(repr_data).items():
                    df_map = dict(stats[channel]["df_map"])  # type: ignore[call-overload]
                    for term in terms:
                        df_map[term] = int(df_map.get(term, 0)) + 1
                    stats[channel]["df_map"] = dict(
                        sorted(df_map.items(), key=lambda item: item[0])
                    )

            total_docs = len(rows)
            for channel in CHANNELS:
                stats[channel]["avg_len"] = lengths_sum[channel] / max(total_docs, 1)

        (
            self.session.query(GraphRepresentationStatsModel)
            .filter(
                GraphRepresentationStatsModel.tenant_id == self.tenant_id,
                GraphRepresentationStatsModel.graph_id == graph_id,
            )
            .delete()
        )

        now = datetime.now(timezone.utc)
        for channel in CHANNELS:
            row = GraphRepresentationStatsModel(
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                channel=channel,
                doc_count=int(stats[channel]["doc_count"]),  # type: ignore[call-overload]
                avg_len=float(stats[channel]["avg_len"]),
                df_map=dict(stats[channel]["df_map"]),  # type: ignore[call-overload]
                updated_at=now,
            )
            self.session.add(row)
        self.session.flush()

    def _incremental_update_graph_stats(
        self,
        graph_id: str,
        representation: RepresentationV2,
    ) -> None:
        now = datetime.now(timezone.utc)
        df_terms = self._repr_df_terms(representation)

        for channel in CHANNELS:
            row = (
                self.session.query(GraphRepresentationStatsModel)
                .filter(
                    GraphRepresentationStatsModel.tenant_id == self.tenant_id,
                    GraphRepresentationStatsModel.graph_id == graph_id,
                    GraphRepresentationStatsModel.channel == channel,
                )
                .first()
            )
            if row is None:
                row = GraphRepresentationStatsModel(
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    channel=channel,
                    doc_count=0,
                    avg_len=0.0,
                    df_map={},
                    updated_at=now,
                )
                self.session.add(row)
                self.session.flush()

            prev_doc_count = int(row.doc_count or 0)
            next_doc_count = prev_doc_count + 1
            channel_len = int(representation.channel_lengths.get(channel, 0))
            row.avg_len = (
                (float(row.avg_len or 0.0) * prev_doc_count) + channel_len
            ) / max(next_doc_count, 1)
            row.doc_count = next_doc_count
            df_map = dict(row.df_map or {})
            for term in df_terms[channel]:
                df_map[term] = int(df_map.get(term, 0)) + 1
            row.df_map = dict(sorted(df_map.items(), key=lambda item: item[0]))
            row.updated_at = now

        self.session.flush()

    @staticmethod
    def _repr_df_terms(representation: RepresentationV2) -> Dict[str, List[str]]:
        return {
            "word": sorted(representation.word_counts.keys()),
            "phrase": sorted(representation.phrase_counts.keys()),
            "skip": sorted(representation.skip_counts.keys()),
            "entity": sorted(set(representation.entity_tokens)),
            "time": sorted(set(representation.time_tokens)),
            "layout": sorted(set(representation.layout_tokens)),
            "semantic_phrase": sorted(
                (representation.semantic_phrase_counts or {}).keys()
            ),
            "concept": sorted((representation.concept_counts or {}).keys()),
            "morphology": sorted((representation.morphology_counts or {}).keys()),
            "alias": sorted(set(representation.alias_families or ())),
            "translit": sorted(set(representation.transliterated_tokens or ())),
            "stem_family": sorted(set(representation.stem_families or ())),
            "relation": sorted(set(representation.relation_cues or ())),
            "value": sorted(set(representation.value_cues or ())),
            "temporal": sorted(set(representation.temporal_cues or ())),
        }

    @staticmethod
    def _row_to_repr(row: NodeRepresentationV2Model) -> RepresentationV2:
        return RepresentationV2.from_dict(
            {
                "repr_hash": row.repr_hash,
                "normalized_text": row.normalized_text or "",
                "word_counts": row.word_counts or {},
                "phrase_counts": row.phrase_counts or {},
                "skip_counts": row.skip_counts or {},
                "entity_tokens": row.entity_tokens or [],
                "time_tokens": row.time_tokens or [],
                "layout_tokens": row.layout_tokens or [],
                "semantic_phrase_counts": row.semantic_phrase_counts or {},
                "concept_counts": row.concept_counts or {},
                "morphology_counts": row.morphology_counts or {},
                "alias_families": row.alias_families or [],
                "transliterated_tokens": row.transliterated_tokens or [],
                "stem_families": row.stem_families or [],
                "relation_cues": row.relation_cues or [],
                "value_cues": row.value_cues or [],
                "temporal_cues": row.temporal_cues or [],
                "channel_lengths": row.channel_lengths or {},
            }
        )

"""Graph-scoped domain knowledge repository."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import asc
from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.store.pg.models_faim import (
        GraphDomainLexiconModel,
        GraphKBSourceModel,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.models_faim import GraphDomainLexiconModel, GraphKBSourceModel


class DomainKnowledgeRepo:
    """Repository for graph-scoped domain lexicon and KB sources."""

    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    @staticmethod
    def _dedupe_lexicon_rows(
        rows: Sequence[Mapping[str, object]],
    ) -> List[Mapping[str, object]]:
        merged: Dict[Tuple[str, str, str], Dict[str, object]] = {}
        for row in rows:
            key = (
                str(row["surface_form"]),
                str(row["canonical_form"]),
                str(row["kind"]),
            )
            existing = merged.get(key)
            if existing is None:
                merged[key] = {
                    "surface_form": key[0],
                    "canonical_form": key[1],
                    "kind": key[2],
                    "domain_pack": (
                        str(row["domain_pack"]) if row.get("domain_pack") else None
                    ),
                    "support_count": int(row.get("support_count", 0)),
                    "score": float(row.get("score", 0.0)),
                    "meta": dict(row.get("meta", {})),
                }
                continue
            if row.get("domain_pack") and not existing.get("domain_pack"):
                existing["domain_pack"] = str(row["domain_pack"])
            existing["support_count"] = max(
                int(existing.get("support_count", 0)),
                int(row.get("support_count", 0)),
            )
            existing["score"] = max(
                float(existing.get("score", 0.0)),
                float(row.get("score", 0.0)),
            )
            meta = dict(existing.get("meta", {}))
            meta.update(dict(row.get("meta", {})))
            existing["meta"] = meta
        return [merged[key] for key in sorted(merged)]

    def replace_lexicon(
        self,
        graph_id: str,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        deduped_rows = self._dedupe_lexicon_rows(rows)
        self.session.query(GraphDomainLexiconModel).filter(
            GraphDomainLexiconModel.tenant_id == self.tenant_id,
            GraphDomainLexiconModel.graph_id == graph_id,
        ).delete()

        now = datetime.now(timezone.utc)
        for row in deduped_rows:
            self.session.add(
                GraphDomainLexiconModel(
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    surface_form=str(row["surface_form"]),
                    canonical_form=str(row["canonical_form"]),
                    kind=str(row["kind"]),
                    domain_pack=(
                        str(row["domain_pack"]) if row.get("domain_pack") else None
                    ),
                    support_count=int(row.get("support_count", 0)),  # type: ignore[call-overload]
                    score=float(row.get("score", 0.0)),
                    meta=dict(row.get("meta", {})),  # type: ignore[call-overload]
                    updated_at=now,
                )
            )
        self.session.flush()
        return len(deduped_rows)

    def merge_lexicon(
        self,
        graph_id: str,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        deduped_rows = self._dedupe_lexicon_rows(rows)
        now = datetime.now(timezone.utc)
        existing_rows = self.list_lexicon_entries(graph_id)
        existing = {
            (row.surface_form, row.canonical_form, row.kind): row for row in existing_rows
        }
        touched = 0
        for row in deduped_rows:
            key = (
                str(row["surface_form"]),
                str(row["canonical_form"]),
                str(row["kind"]),
            )
            model = existing.get(key)
            if model is None:
                self.session.add(
                    GraphDomainLexiconModel(
                        tenant_id=self.tenant_id,
                        graph_id=graph_id,
                        surface_form=key[0],
                        canonical_form=key[1],
                        kind=key[2],
                        domain_pack=(
                            str(row["domain_pack"]) if row.get("domain_pack") else None
                        ),
                        support_count=int(row.get("support_count", 0)),
                        score=float(row.get("score", 0.0)),
                        meta=dict(row.get("meta", {})),
                        updated_at=now,
                    )
                )
            else:
                model.domain_pack = (
                    str(row["domain_pack"]) if row.get("domain_pack") else model.domain_pack
                )
                model.support_count = max(
                    int(model.support_count or 0), int(row.get("support_count", 0))
                )
                model.score = max(float(model.score or 0.0), float(row.get("score", 0.0)))
                merged_meta = dict(model.meta or {})
                merged_meta.update(dict(row.get("meta", {})))
                model.meta = merged_meta
                model.updated_at = now
            touched += 1
        self.session.flush()
        return touched

    def replace_sources(
        self,
        graph_id: str,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        self.session.query(GraphKBSourceModel).filter(
            GraphKBSourceModel.tenant_id == self.tenant_id,
            GraphKBSourceModel.graph_id == graph_id,
        ).delete()

        now = datetime.now(timezone.utc)
        for row in rows:
            self.session.add(
                GraphKBSourceModel(
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    source_id=str(row["source_id"]),
                    source_kind=str(row["source_kind"]),
                    source_hash=str(row["source_hash"]),
                    meta=dict(row.get("meta", {})),  # type: ignore[call-overload]
                    updated_at=now,
                )
            )
        self.session.flush()
        return len(rows)

    def merge_sources(
        self,
        graph_id: str,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        now = datetime.now(timezone.utc)
        existing = {
            row.source_id: row
            for row in self.session.query(GraphKBSourceModel).filter(
                GraphKBSourceModel.tenant_id == self.tenant_id,
                GraphKBSourceModel.graph_id == graph_id,
            )
        }
        touched = 0
        for row in rows:
            source_id = str(row["source_id"])
            model = existing.get(source_id)
            if model is None:
                self.session.add(
                    GraphKBSourceModel(
                        tenant_id=self.tenant_id,
                        graph_id=graph_id,
                        source_id=source_id,
                        source_kind=str(row["source_kind"]),
                        source_hash=str(row["source_hash"]),
                        meta=dict(row.get("meta", {})),
                        updated_at=now,
                    )
                )
            else:
                model.source_kind = str(row["source_kind"])
                model.source_hash = str(row["source_hash"])
                merged_meta = dict(model.meta or {})
                merged_meta.update(dict(row.get("meta", {})))
                model.meta = merged_meta
                model.updated_at = now
            touched += 1
        self.session.flush()
        return touched

    def list_lexicon_entries(
        self,
        graph_id: str,
        *,
        kinds: Optional[Sequence[str]] = None,
    ) -> List[GraphDomainLexiconModel]:
        query = self.session.query(GraphDomainLexiconModel).filter(
            GraphDomainLexiconModel.tenant_id == self.tenant_id,
            GraphDomainLexiconModel.graph_id == graph_id,
        )
        if kinds:
            query = query.filter(GraphDomainLexiconModel.kind.in_(list(kinds)))
        return query.order_by(
            asc(GraphDomainLexiconModel.surface_form),
            asc(GraphDomainLexiconModel.kind),
            GraphDomainLexiconModel.score.desc(),
            asc(GraphDomainLexiconModel.canonical_form),
        ).all()

    def get_domain_map(
        self,
        graph_id: str,
        *,
        kinds: Optional[Sequence[str]] = None,
    ) -> Dict[str, Tuple[str, ...]]:
        rows = self.list_lexicon_entries(graph_id, kinds=kinds)
        mapped: Dict[str, List[str]] = {}
        for row in rows:
            values = mapped.setdefault(row.surface_form, [])
            if row.canonical_form not in values:
                values.append(row.canonical_form)
        return {
            key: tuple(values)
            for key, values in sorted(mapped.items(), key=lambda item: item[0])
        }


__all__ = ["DomainKnowledgeRepo"]

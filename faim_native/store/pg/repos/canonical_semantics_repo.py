"""Graph-scoped canonical semantics repository."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import and_, asc
from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.store.pg.models_faim import (
        GraphCanonicalLexiconModel,
        GraphTermStatModel,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.models_faim import GraphCanonicalLexiconModel, GraphTermStatModel


class CanonicalSemanticsRepo:
    """Repository for graph-scoped canonical stats and lexicon."""

    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    def replace_term_stats(
        self,
        graph_id: str,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        self.session.query(GraphTermStatModel).filter(
            GraphTermStatModel.tenant_id == self.tenant_id,
            GraphTermStatModel.graph_id == graph_id,
        ).delete()

        now = datetime.now(timezone.utc)
        for row in rows:
            self.session.add(
                GraphTermStatModel(
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    channel=str(row["channel"]),
                    term=str(row["term"]),
                    df=int(row["df"]),
                    cf=int(row["cf"]),
                    doc_count=int(row["doc_count"]),
                    context_terms=dict(row.get("context_terms", {})),
                    updated_at=now,
                )
            )
        self.session.flush()
        return len(rows)

    def replace_lexicon(
        self,
        graph_id: str,
        rows: Sequence[Mapping[str, object]],
    ) -> int:
        self.session.query(GraphCanonicalLexiconModel).filter(
            GraphCanonicalLexiconModel.tenant_id == self.tenant_id,
            GraphCanonicalLexiconModel.graph_id == graph_id,
        ).delete()

        now = datetime.now(timezone.utc)
        for row in rows:
            self.session.add(
                GraphCanonicalLexiconModel(
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    surface_form=str(row["surface_form"]),
                    canonical_form=str(row["canonical_form"]),
                    kind=str(row["kind"]),
                    support_count=int(row.get("support_count", 0)),
                    score=float(row.get("score", 0.0)),
                    meta=dict(row.get("meta", {})),
                    updated_at=now,
                )
            )
        self.session.flush()
        return len(rows)

    def list_term_stats(
        self,
        graph_id: str,
        *,
        channel: Optional[str] = None,
    ) -> List[GraphTermStatModel]:
        query = self.session.query(GraphTermStatModel).filter(
            GraphTermStatModel.tenant_id == self.tenant_id,
            GraphTermStatModel.graph_id == graph_id,
        )
        if channel is not None:
            query = query.filter(GraphTermStatModel.channel == channel)
        return query.order_by(
            asc(GraphTermStatModel.channel),
            asc(GraphTermStatModel.term),
        ).all()

    def list_lexicon_entries(
        self,
        graph_id: str,
        *,
        kinds: Optional[Sequence[str]] = None,
    ) -> List[GraphCanonicalLexiconModel]:
        query = self.session.query(GraphCanonicalLexiconModel).filter(
            GraphCanonicalLexiconModel.tenant_id == self.tenant_id,
            GraphCanonicalLexiconModel.graph_id == graph_id,
        )
        if kinds:
            query = query.filter(GraphCanonicalLexiconModel.kind.in_(list(kinds)))
        return query.order_by(
            asc(GraphCanonicalLexiconModel.surface_form),
            asc(GraphCanonicalLexiconModel.kind),
            GraphCanonicalLexiconModel.score.desc(),
            asc(GraphCanonicalLexiconModel.canonical_form),
        ).all()

    def get_canonical_map(
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


__all__ = ["CanonicalSemanticsRepo"]

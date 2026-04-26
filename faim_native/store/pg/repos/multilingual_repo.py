"""Graph-scoped multilingual lexicon repository."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

from sqlalchemy import asc
from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.store.pg.models_faim import GraphMultilingualLexiconModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.models_faim import GraphMultilingualLexiconModel


class MultilingualRepo:
    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    def replace_lexicon(
        self, graph_id: str, rows: Sequence[Mapping[str, object]]
    ) -> int:
        self.session.query(GraphMultilingualLexiconModel).filter(
            GraphMultilingualLexiconModel.tenant_id == self.tenant_id,
            GraphMultilingualLexiconModel.graph_id == graph_id,
        ).delete()
        now = datetime.now(timezone.utc)
        for row in rows:
            self.session.add(
                GraphMultilingualLexiconModel(
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    language=str(row["language"]),
                    surface_form=str(row["surface_form"]),
                    canonical_form=str(row["canonical_form"]),
                    concept_key=str(row["concept_key"]),
                    score=float(row.get("score", 0.0)),
                    meta=dict(row.get("meta", {})),  # type: ignore[call-overload]
                    updated_at=now,
                )
            )
        self.session.flush()
        return len(rows)

    def get_language_map(self, graph_id: str) -> Dict[str, Tuple[str, ...]]:
        rows = (
            self.session.query(GraphMultilingualLexiconModel)
            .filter(
                GraphMultilingualLexiconModel.tenant_id == self.tenant_id,
                GraphMultilingualLexiconModel.graph_id == graph_id,
            )
            .order_by(
                asc(GraphMultilingualLexiconModel.language),
                asc(GraphMultilingualLexiconModel.surface_form),
                asc(GraphMultilingualLexiconModel.canonical_form),
            )
            .all()
        )
        mapped: Dict[str, List[str]] = {}
        for row in rows:
            values = mapped.setdefault(row.surface_form, [])
            for candidate in (
                row.canonical_form,
                str((row.meta or {}).get("translated_form", "")),
            ):
                if candidate and candidate not in values:
                    values.append(candidate)
        return {
            key: tuple(values)
            for key, values in sorted(mapped.items(), key=lambda item: item[0])
        }


__all__ = ["MultilingualRepo"]

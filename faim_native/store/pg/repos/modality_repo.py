"""Repository for Phase 7 multimodal sidecar data."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence
from uuid import UUID

from sqlalchemy import asc
from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.encoding.modality_features import ModalityFeatures
    from faim.Faim_Native.store.pg.models_faim import NodeModalityV1Model
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from encoding.modality_features import ModalityFeatures

    from store.pg.models_faim import NodeModalityV1Model


class ModalityRepo:
    """Repository for additive multimodal sidecars."""

    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    def upsert_node_modality(
        self,
        *,
        graph_id: str,
        node_id: UUID,
        features: ModalityFeatures,
    ) -> str:
        existing = (
            self.session.query(NodeModalityV1Model)
            .filter(
                NodeModalityV1Model.node_id == node_id,
                NodeModalityV1Model.tenant_id == self.tenant_id,
                NodeModalityV1Model.graph_id == graph_id,
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if existing and existing.modality_hash == features.modality_hash:
            return "unchanged"
        if existing:
            existing.modality_hash = features.modality_hash
            existing.ocr_text = features.ocr_text
            existing.table_text = features.table_text
            existing.layout_tokens = list(features.layout_tokens)
            existing.image_phash = features.image_phash
            existing.filename_tokens = list(features.filename_tokens)
            existing.caption_tokens = list(features.caption_tokens)
            existing.metadata_tokens = list(features.metadata_tokens)
            existing.updated_at = now
            self.session.flush()
            return "updated"

        row = NodeModalityV1Model(
            node_id=node_id,
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            modality_hash=features.modality_hash,
            ocr_text=features.ocr_text,
            table_text=features.table_text,
            layout_tokens=list(features.layout_tokens),
            image_phash=features.image_phash,
            filename_tokens=list(features.filename_tokens),
            caption_tokens=list(features.caption_tokens),
            metadata_tokens=list(features.metadata_tokens),
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        self.session.flush()
        return "inserted"

    def list_by_node_ids(
        self, *, graph_id: str, node_ids: Sequence[UUID]
    ) -> List[NodeModalityV1Model]:
        if not node_ids:
            return []
        return (
            self.session.query(NodeModalityV1Model)
            .filter(
                NodeModalityV1Model.tenant_id == self.tenant_id,
                NodeModalityV1Model.graph_id == graph_id,
                NodeModalityV1Model.node_id.in_(list(node_ids)),
            )
            .order_by(asc(NodeModalityV1Model.node_id))
            .all()
        )


__all__ = ["ModalityRepo"]

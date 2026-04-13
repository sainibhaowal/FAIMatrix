"""Multimodal sidecar backfill for existing graphs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MultimodalBackfillResult:
    graph_id: str
    files_scanned: int = 0
    files_loaded: int = 0
    files_failed: int = 0
    blocks_extracted: int = 0
    matched_nodes: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    graph_version: int = 0
    errors: List[str] = field(default_factory=list)


def _anchor_key(anchor_json: Optional[dict]) -> str:
    return json.dumps(anchor_json or {}, sort_keys=True, separators=(",", ":"))


def run_multimodal_backfill(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    raw_repo,
    storage_file_repo,
    raw_store,
    node_repo,
    gv_repo,
    event_repo=None,
    extract_fn=None,
    page_size: int = 100,
    max_errors: int = 25,
) -> MultimodalBackfillResult:
    from encoding.modality_features import build_modality_features
    from store.pg.repos.modality_repo import ModalityRepo

    if extract_fn is None:
        from perception.router import route_extraction as extract_fn

    result = MultimodalBackfillResult(graph_id=graph_id)
    repo = ModalityRepo(session=session, tenant_id=tenant_id)

    offset = 0
    while True:
        rows, _total = storage_file_repo.list_files(
            session,
            graph_id=graph_id,
            status=None,
            query=None,
            limit=page_size,
            offset=offset,
            include_delete_requested=False,
        )
        if not rows:
            break
        for row in rows:
            result.files_scanned += 1
            try:
                raw_ref = raw_repo.get_by_id(session, row.raw_id)
                if raw_ref is None:
                    raise ValueError(f"Raw reference missing for {row.raw_id}")
                file_bytes = raw_store.load(raw_ref, verify=True)
                result.files_loaded += 1
                blocks = extract_fn(file_bytes, row.filename, str(row.raw_id))
                result.blocks_extracted += len(blocks)
                if not blocks:
                    continue
                existing_nodes = node_repo.list_by_raw_id(
                    graph_id=graph_id,
                    raw_id=str(row.raw_id),
                    kind="atom",
                )
                nodes_by_anchor = {_anchor_key(node.anchor_json): node for node in existing_nodes}
                features = build_modality_features(
                    blocks=blocks,
                    filename=row.filename,
                    file_bytes=file_bytes,
                    metadata={"mime_type": getattr(row, "mime_type", "")},
                )
                for block in blocks:
                    node = nodes_by_anchor.get(_anchor_key(block.anchor.to_dict()))
                    if node is None:
                        continue
                    state = repo.upsert_node_modality(
                        graph_id=graph_id,
                        node_id=node.node_id,
                        features=features,
                    )
                    result.matched_nodes += 1
                    if state == "inserted":
                        result.inserted += 1
                    elif state == "updated":
                        result.updated += 1
                    else:
                        result.unchanged += 1
            except Exception as exc:  # nosec B110
                result.files_failed += 1
                if len(result.errors) < max_errors:
                    result.errors.append(f"{row.filename}: {exc}")
        offset += len(rows)

    if result.inserted > 0 or result.updated > 0:
        result.graph_version = gv_repo.bump(
            session=session,
            graph_id=graph_id,
            reason="multimodal_backfill",
        )
        if event_repo is not None:
            try:
                event_repo.emit(
                    session,
                    graph_id,
                    "MULTIMODAL_BACKFILL",
                    {
                        "files_scanned": result.files_scanned,
                        "matched_nodes": result.matched_nodes,
                        "inserted": result.inserted,
                        "updated": result.updated,
                        "unchanged": result.unchanged,
                    },
                )
            except Exception:
                pass

    return result


__all__ = ["MultimodalBackfillResult", "run_multimodal_backfill"]

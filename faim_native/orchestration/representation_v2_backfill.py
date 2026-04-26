"""Representation V2 backfill for existing graphs.

Rebuilds additive lexical-semantic sidecars from stored raw files without
changing the canonical 256-d FAIM vector contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RepresentationV2BackfillResult:
    """Result summary for graph-scoped Representation V2 backfill."""

    graph_id: str
    files_scanned: int = 0
    files_loaded: int = 0
    files_failed: int = 0
    blocks_extracted: int = 0
    matched_nodes: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_nodes: int = 0
    graph_version: int = 0
    errors: List[str] = field(default_factory=list)


def _anchor_key(anchor_json: Optional[dict]) -> str:
    """Build stable lookup key for anchor-based provenance matching."""
    return json.dumps(anchor_json or {}, sort_keys=True, separators=(",", ":"))


def run_representation_v2_backfill(
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
    page_size: int = 100,
    max_errors: int = 25,
) -> RepresentationV2BackfillResult:
    """Backfill Representation V2 sidecars for an existing graph."""
    from encoding.representation_v2 import build_representation_v2_for_block
    from encoding.text_vectorizer import vectorize_blocks
    from perception.router import route_extraction
    from store.pg.repos.representation_repo import RepresentationRepo

    result = RepresentationV2BackfillResult(graph_id=graph_id)
    repr_repo = RepresentationRepo(session=session, tenant_id=tenant_id)

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

                blocks = route_extraction(file_bytes, row.filename, str(row.raw_id))
                result.blocks_extracted += len(blocks)
                if not blocks:
                    continue

                existing_nodes = node_repo.list_by_raw_id(
                    graph_id=graph_id,
                    raw_id=str(row.raw_id),
                    kind="atom",
                )
                nodes_by_vector_hash = {
                    str(node.vector_hash): node
                    for node in existing_nodes
                    if node.vector_hash
                }
                nodes_by_anchor = {
                    _anchor_key(node.anchor_json): node for node in existing_nodes
                }

                vectors = vectorize_blocks(blocks)
                reprs_v2 = [
                    build_representation_v2_for_block(block) for block in blocks
                ]

                for block, vector, repr_v2 in zip(
                    blocks, vectors, reprs_v2, strict=False
                ):
                    node = nodes_by_vector_hash.get(vector.vector_hash)
                    if node is None:
                        node = nodes_by_anchor.get(_anchor_key(block.anchor.to_dict()))
                    if node is None:
                        result.skipped_nodes += 1
                        continue

                    status = repr_repo.upsert_node_representation(
                        graph_id=graph_id,
                        node_id=node.node_id,
                        representation=repr_v2,
                    )
                    result.matched_nodes += 1
                    if status == "inserted":
                        result.inserted += 1
                    elif status == "updated":
                        result.updated += 1
                    else:
                        result.unchanged += 1
            except Exception as exc:  # nosec B110
                result.files_failed += 1
                if len(result.errors) < max_errors:
                    result.errors.append(f"{row.filename}: {exc!r}")
                try:
                    session.rollback()
                except Exception:
                    pass

        offset += len(rows)

    if result.matched_nodes > 0:
        repr_repo.rebuild_graph_stats(graph_id)

    if result.inserted > 0 or result.updated > 0:
        result.graph_version = gv_repo.bump(
            session=session,
            graph_id=graph_id,
            reason="repr_v2_backfill",
        )
        if event_repo is not None:
            try:
                event_repo.emit(
                    session,
                    graph_id,
                    "REPR_V2_BACKFILL",
                    {
                        "files_scanned": result.files_scanned,
                        "matched_nodes": result.matched_nodes,
                        "inserted": result.inserted,
                        "updated": result.updated,
                        "unchanged": result.unchanged,
                        "skipped_nodes": result.skipped_nodes,
                    },
                )
            except Exception:  # nosec B110
                pass

    return result

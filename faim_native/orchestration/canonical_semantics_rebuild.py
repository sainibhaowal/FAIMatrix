"""Canonical semantics rebuild for existing graphs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CanonicalSemanticsRebuildResult:
    """Result summary for graph-scoped canonical semantics rebuild."""

    graph_id: str
    files_scanned: int = 0
    files_loaded: int = 0
    files_failed: int = 0
    blocks_extracted: int = 0
    matched_nodes: int = 0
    term_stats_written: int = 0
    lexicon_written: int = 0
    edges_written: int = 0
    graph_version: int = 0
    errors: List[str] = field(default_factory=list)


def _anchor_key(anchor_json: Optional[dict]) -> str:
    return json.dumps(anchor_json or {}, sort_keys=True, separators=(",", ":"))


def run_canonical_semantics_rebuild(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    raw_repo,
    storage_file_repo,
    raw_store,
    node_repo,
    edge_repo,
    gv_repo,
    event_repo=None,
    page_size: int = 100,
    max_errors: int = 25,
) -> CanonicalSemanticsRebuildResult:
    """Rebuild graph-scoped canonical semantics artifacts from stored raw files."""
    from core.operators.canonical_semantics import (
        build_canonical_document,
        build_canonical_semantics,
    )
    from perception.router import route_extraction
    from store.pg.repos.canonical_semantics_repo import CanonicalSemanticsRepo

    result = CanonicalSemanticsRebuildResult(graph_id=graph_id)
    canonical_repo = CanonicalSemanticsRepo(session=session, tenant_id=tenant_id)
    docs = []

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
                nodes_by_anchor = {
                    _anchor_key(node.anchor_json): node for node in existing_nodes
                }

                for block in blocks:
                    node = nodes_by_anchor.get(_anchor_key(block.anchor.to_dict()))
                    if node is None:
                        continue
                    docs.append(
                        build_canonical_document(
                            node_id=node.node_id,
                            raw_id=str(row.raw_id),
                            anchor_json=dict(node.anchor_json or {}),
                            text=block.content,
                        )
                    )
                    result.matched_nodes += 1
            except Exception as exc:  # nosec B110
                result.files_failed += 1
                if len(result.errors) < max_errors:
                    result.errors.append(f"{row.filename}: {exc}")

        offset += len(rows)

    build = build_canonical_semantics(docs)
    result.term_stats_written = canonical_repo.replace_term_stats(
        graph_id=graph_id,
        rows=build.term_stats,
    )
    result.lexicon_written = canonical_repo.replace_lexicon(
        graph_id=graph_id,
        rows=build.lexicon_entries,
    )

    deleted = edge_repo.delete_edges_by_kinds(
        graph_id=graph_id,
        kinds=["distributional_synonym", "paraphrase"],
    )
    for edge in build.edge_specs:
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=edge["src_node_id"],
            dst_node_id=edge["dst_node_id"],
            semantic_type=edge["kind"],
            semantic_weight=edge["semantic_weight"],
            meta=edge.get("meta"),
        )
        result.edges_written += 1

    if (
        result.term_stats_written > 0
        or result.lexicon_written > 0
        or result.edges_written > 0
        or deleted > 0
    ):
        result.graph_version = gv_repo.bump(
            session=session,
            graph_id=graph_id,
            reason="canonical_semantics_rebuild",
        )
        if event_repo is not None:
            try:
                event_repo.emit(
                    session,
                    graph_id,
                    "CANONICAL_SEMANTICS_REBUILD",
                    {
                        "files_scanned": result.files_scanned,
                        "files_failed": result.files_failed,
                        "matched_nodes": result.matched_nodes,
                        "term_stats_written": result.term_stats_written,
                        "lexicon_written": result.lexicon_written,
                        "edges_written": result.edges_written,
                        "edges_deleted": deleted,
                        "graph_version": result.graph_version,
                    },
                )
            except Exception:  # nosec B110
                pass

    return result


__all__ = ["CanonicalSemanticsRebuildResult", "run_canonical_semantics_rebuild"]

"""Multilingual semantics rebuild for existing graphs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MultilingualSemanticsRebuildResult:
    graph_id: str
    files_scanned: int = 0
    files_loaded: int = 0
    files_failed: int = 0
    blocks_extracted: int = 0
    matched_nodes: int = 0
    lexicon_written: int = 0
    concept_nodes_written: int = 0
    concept_edges_written: int = 0
    graph_version: int = 0
    errors: List[str] = field(default_factory=list)


def _anchor_key(anchor_json: Optional[dict]) -> str:
    return json.dumps(anchor_json or {}, sort_keys=True, separators=(",", ":"))


def run_multilingual_semantics_rebuild(
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
    extract_fn=None,
    page_size: int = 100,
    max_errors: int = 25,
) -> MultilingualSemanticsRebuildResult:
    from core.operators.multilingual_semantics import (
        build_multilingual_document,
        build_multilingual_semantics,
        concept_key_to_vector_text,
        concept_node_hash,
    )
    from encoding.text_vectorizer import vectorize_text
    from store.pg.repos.multilingual_repo import MultilingualRepo

    if extract_fn is None:
        from perception.router import route_extraction

        extract_fn = route_extraction

    result = MultilingualSemanticsRebuildResult(graph_id=graph_id)
    repo = MultilingualRepo(session=session, tenant_id=tenant_id)
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
                blocks = extract_fn(file_bytes, row.filename, str(row.raw_id))
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
                        build_multilingual_document(node.node_id, block.content)
                    )
                    result.matched_nodes += 1
            except Exception as exc:  # nosec B110
                result.files_failed += 1
                if len(result.errors) < max_errors:
                    result.errors.append(f"{row.filename}: {exc}")
        offset += len(rows)

    concept_rows, lexicon_rows, concept_members = build_multilingual_semantics(docs)
    result.lexicon_written = repo.replace_lexicon(graph_id, lexicon_rows)

    deleted = edge_repo.delete_edges_by_kinds(
        graph_id=graph_id,
        kinds=["concept_surface", "translation"],
    )

    for concept in concept_rows:
        vector_res = vectorize_text(
            concept_key_to_vector_text(str(concept["concept_key"]))
        )
        concept_node_id = node_repo.upsert_special_node(
            graph_id=graph_id,
            kind="concept",
            vector_hash=concept_node_hash(str(concept["concept_key"])),
            v_native=list(vector_res.v_native),
            opp_signature=vector_res.opp_signature,
            residual=0.0,
            level=1,
        )
        result.concept_nodes_written += 1
        for member_node_id in concept_members.get(str(concept["concept_key"]), []):
            edge_repo.add_semantic_edge(
                graph_id=graph_id,
                src_node_id=member_node_id,
                dst_node_id=concept_node_id,
                semantic_type="concept_surface",
                semantic_weight=0.70,
                meta={"concept_key": concept["concept_key"]},
            )
            edge_repo.add_semantic_edge(
                graph_id=graph_id,
                src_node_id=concept_node_id,
                dst_node_id=member_node_id,
                semantic_type="translation",
                semantic_weight=0.72,
                meta={"concept_key": concept["concept_key"]},
            )
            result.concept_edges_written += 2

    if result.lexicon_written > 0 or result.concept_edges_written > 0 or deleted > 0:
        result.graph_version = gv_repo.bump(
            session=session,
            graph_id=graph_id,
            reason="multilingual_semantics_rebuild",
        )
        if event_repo is not None:
            try:
                event_repo.emit(
                    session,
                    graph_id,
                    "MULTILINGUAL_SEMANTICS_REBUILD",
                    {
                        "files_scanned": result.files_scanned,
                        "files_failed": result.files_failed,
                        "matched_nodes": result.matched_nodes,
                        "lexicon_written": result.lexicon_written,
                        "concept_nodes_written": result.concept_nodes_written,
                        "concept_edges_written": result.concept_edges_written,
                        "edges_deleted": deleted,
                        "graph_version": result.graph_version,
                    },
                )
            except Exception:
                pass
    return result


__all__ = ["MultilingualSemanticsRebuildResult", "run_multilingual_semantics_rebuild"]

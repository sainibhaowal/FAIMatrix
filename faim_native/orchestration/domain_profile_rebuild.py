"""Domain terminology rebuild for existing graphs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DomainProfileRebuildResult:
    graph_id: str
    files_scanned: int = 0
    files_loaded: int = 0
    files_failed: int = 0
    blocks_extracted: int = 0
    matched_nodes: int = 0
    lexicon_written: int = 0
    graph_version: int = 0
    errors: List[str] = field(default_factory=list)


def _anchor_key(anchor_json: Optional[dict]) -> str:
    return json.dumps(anchor_json or {}, sort_keys=True, separators=(",", ":"))


def run_domain_profile_rebuild(
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
    domain_pack: str | None = None,
    page_size: int = 100,
    max_errors: int = 25,
) -> DomainProfileRebuildResult:
    domain_pack = None
    from core.operators.domain_knowledge import load_domain_profile_pack
    from core.operators.terminology_mining import (
        build_domain_document,
        mine_terminology,
    )
    from perception.router import route_extraction
    from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo

    repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
    result = DomainProfileRebuildResult(graph_id=graph_id)
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
                    graph_id=graph_id, raw_id=str(row.raw_id), kind="atom"
                )
                nodes_by_anchor = {
                    _anchor_key(node.anchor_json): node for node in existing_nodes
                }
                for block in blocks:
                    node = nodes_by_anchor.get(_anchor_key(block.anchor.to_dict()))
                    if node is None:
                        continue
                    docs.append(build_domain_document(node.node_id, block.content))
                    result.matched_nodes += 1
            except Exception as exc:
                result.files_failed += 1
                if len(result.errors) < max_errors:
                    result.errors.append(f"{row.filename}: {exc}")
        offset += len(rows)

    rows = mine_terminology(docs, domain_pack=domain_pack)
    rows.extend(load_domain_profile_pack(domain_pack))
    dedup = {}
    for row in rows:
        dedup[(row["surface_form"], row["canonical_form"], row["kind"])] = row
    result.lexicon_written = repo.replace_lexicon(
        graph_id=graph_id, rows=[dedup[k] for k in sorted(dedup)]
    )
    if result.lexicon_written:
        result.graph_version = gv_repo.bump(
            session=session, graph_id=graph_id, reason="domain_profile_rebuild"
        )
        if event_repo is not None:
            try:
                event_repo.emit(
                    session,
                    graph_id,
                    "DOMAIN_PROFILE_REBUILD",
                    {
                        "files_scanned": result.files_scanned,
                        "files_failed": result.files_failed,
                        "matched_nodes": result.matched_nodes,
                        "lexicon_written": result.lexicon_written,
                        "graph_version": result.graph_version,
                    },
                )
            except Exception:
                pass
    return result


__all__ = ["DomainProfileRebuildResult", "run_domain_profile_rebuild"]

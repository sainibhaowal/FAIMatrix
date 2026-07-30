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
    sources_written: int = 0
    entity_nodes_written: int = 0
    relation_nodes_written: int = 0
    fact_nodes_written: int = 0
    value_nodes_written: int = 0
    time_nodes_written: int = 0
    edges_written: int = 0
    graph_version: int = 0
    detected_packs: List[str] = field(default_factory=list)
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
    from core.operators.domain_knowledge import load_domain_profile_pack
    from core.operators.domain_knowledge import (
        KBFact,
        build_kb_lexicon_rows,
        derive_kb_rows_from_documents,
        detect_domain_profile_packs,
        entity_key,
        fact_key,
        relation_key,
        source_hash,
        time_key,
        value_key,
        vector_text_for_key,
    )
    from core.operators.terminology_mining import (
        build_domain_document,
        extract_phrase_terms,
        mine_terminology,
    )
    from domain.semantic_memory import learn_semantic_memory_bundles
    from encoding.text_vectorizer import vectorize_text
    from perception.router import route_extraction
    from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo
    from store.pg.repos.edge_repo import EdgeRepo

    repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
    edge_repo = EdgeRepo(session=session, tenant_id=tenant_id)
    result = DomainProfileRebuildResult(graph_id=graph_id)
    docs = []
    support_nodes: dict[str, list[object]] = {}

    def _remember_support(term: str, node_id: object) -> None:
        bucket = support_nodes.setdefault(term, [])
        if node_id not in bucket:
            bucket.append(node_id)

    def _merge_rows(rows):
        merged = {}
        for row in rows:
            key = (row["surface_form"], row["canonical_form"], row["kind"])
            existing = merged.get(key)
            if existing is None:
                merged[key] = dict(row)
                merged[key]["meta"] = dict(row.get("meta", {}) or {})
                continue
            existing["support_count"] = max(
                int(existing.get("support_count", 0)),
                int(row.get("support_count", 0)),
            )
            existing["score"] = max(
                float(existing.get("score", 0.0)),
                float(row.get("score", 0.0)),
            )
            if row.get("domain_pack") and not existing.get("domain_pack"):
                existing["domain_pack"] = row.get("domain_pack")
            meta = dict(existing.get("meta", {}) or {})
            meta.update(dict(row.get("meta", {}) or {}))
            existing["meta"] = meta
        return [merged[key] for key in sorted(merged)]

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
                    for term in extract_phrase_terms(block.content):
                        _remember_support(str(term), node.node_id)
                    result.matched_nodes += 1
            except Exception as exc:
                result.files_failed += 1
                if len(result.errors) < max_errors:
                    result.errors.append(f"{row.filename}: {exc}")
        offset += len(rows)

    detected_packs = detect_domain_profile_packs([doc.text for doc in docs])
    explicit_packs = [part.strip() for part in str(domain_pack or "").split(",") if part.strip()]
    result.detected_packs = list(
        dict.fromkeys([pack.lower() for pack in explicit_packs + detected_packs])
    )[:3]

    auto_domain_pack = (
        result.detected_packs[0]
        if result.detected_packs
        else (str(domain_pack).strip().lower() if domain_pack else "autonomous")
    )

    rows = mine_terminology(docs, domain_pack=auto_domain_pack)
    semantic_memory = learn_semantic_memory_bundles(
        docs,
        domain_pack=auto_domain_pack,
        support_nodes=support_nodes,
    )
    pack_rows = []
    for pack_name in result.detected_packs:
        pack_rows.extend(load_domain_profile_pack(pack_name))

    facts = [
        KBFact(
            entity=str(row.get("entity", "")),
            relation=str(row.get("relation", "")),
            value=str(row.get("value", "")),
            time_value=str(row.get("time", "")),
            aliases=tuple(row.get("aliases", []) or ()),
            source_id=str(row.get("source_id") or source_hash(row)),
            source_kind=str(row.get("source_kind", "autonomous_domain")),
            meta=dict(row.get("meta", {}) or {}),
        )
        for row in derive_kb_rows_from_documents([doc.text for doc in docs])
        if str(row.get("entity", "")).strip() and str(row.get("relation", "")).strip()
    ]

    entity_nodes = {}
    relation_nodes = {}
    value_nodes = {}
    time_nodes = {}
    if facts:
        for fact in facts:
            e_key = entity_key(fact.entity)
            r_key = relation_key(fact.relation)
            v_key = value_key(fact.value)
            t_key = time_key(fact.time_value) if fact.time_value else None

            if e_key not in entity_nodes:
                vec = vectorize_text(vector_text_for_key(e_key))
                entity_nodes[e_key] = node_repo.upsert_special_node(
                    graph_id=graph_id,
                    kind="entity",
                    vector_hash=e_key,
                    v_native=list(vec.v_native),
                    opp_signature=vec.opp_signature,
                    level=1,
                )
                result.entity_nodes_written += 1
            if r_key not in relation_nodes:
                vec = vectorize_text(vector_text_for_key(r_key))
                relation_nodes[r_key] = node_repo.upsert_special_node(
                    graph_id=graph_id,
                    kind="relation",
                    vector_hash=r_key,
                    v_native=list(vec.v_native),
                    opp_signature=vec.opp_signature,
                    level=1,
                )
                result.relation_nodes_written += 1
            if v_key not in value_nodes:
                vec = vectorize_text(vector_text_for_key(v_key))
                value_nodes[v_key] = node_repo.upsert_special_node(
                    graph_id=graph_id,
                    kind="value",
                    vector_hash=v_key,
                    v_native=list(vec.v_native),
                    opp_signature=vec.opp_signature,
                    level=0,
                )
                result.value_nodes_written += 1
            if t_key and t_key not in time_nodes:
                vec = vectorize_text(vector_text_for_key(t_key))
                time_nodes[t_key] = node_repo.upsert_special_node(
                    graph_id=graph_id,
                    kind="time",
                    vector_hash=t_key,
                    v_native=list(vec.v_native),
                    opp_signature=vec.opp_signature,
                    level=0,
                )
                result.time_nodes_written += 1

            f_key = fact_key(fact.entity, fact.relation, fact.value, fact.time_value)
            vec = vectorize_text(vector_text_for_key(f_key))
            fact_node_id = node_repo.upsert_special_node(
                graph_id=graph_id,
                kind="fact",
                vector_hash=f_key,
                v_native=list(vec.v_native),
                opp_signature=vec.opp_signature,
                level=1,
            )
            result.fact_nodes_written += 1

            edge_repo.add_semantic_edge(
                graph_id=graph_id,
                src_node_id=entity_nodes[e_key],
                dst_node_id=fact_node_id,
                semantic_type="entity_relation",
                semantic_weight=0.92,
                meta={"relation_key": r_key, "source": "autonomous_domain"},
            )
            edge_repo.add_semantic_edge(
                graph_id=graph_id,
                src_node_id=relation_nodes[r_key],
                dst_node_id=fact_node_id,
                semantic_type="entity_relation",
                semantic_weight=0.88,
                meta={"entity_key": e_key, "source": "autonomous_domain"},
            )
            edge_repo.add_semantic_edge(
                graph_id=graph_id,
                src_node_id=fact_node_id,
                dst_node_id=value_nodes[v_key],
                semantic_type="fact_value",
                semantic_weight=0.84,
                meta={"value_key": v_key, "source": "autonomous_domain"},
            )
            result.edges_written += 3
            if t_key:
                edge_repo.add_semantic_edge(
                    graph_id=graph_id,
                    src_node_id=fact_node_id,
                    dst_node_id=time_nodes[t_key],
                    semantic_type="fact_time",
                    semantic_weight=0.82,
                    meta={"time_key": t_key, "source": "autonomous_domain"},
                )
                result.edges_written += 1

        result.sources_written = repo.merge_sources(
            graph_id=graph_id,
            rows=[
                {
                    "source_id": fact.source_id,
                    "source_kind": fact.source_kind,
                    "source_hash": source_hash(
                        {
                            "entity": fact.entity,
                            "relation": fact.relation,
                            "value": fact.value,
                            "time": fact.time_value,
                            "aliases": list(fact.aliases),
                        }
                    ),
                    "meta": dict(fact.meta or {}),
                }
                for fact in facts
            ],
        )

    if semantic_memory.source_rows:
        result.sources_written += repo.merge_sources(
            graph_id=graph_id,
            rows=list(semantic_memory.source_rows),
        )

    rows.extend(pack_rows)
    rows.extend(build_kb_lexicon_rows(facts, domain_pack=auto_domain_pack))
    rows.extend(list(semantic_memory.lexicon_rows))
    merged_rows = _merge_rows(rows)

    for row in merged_rows:
        meta = dict(row.get("meta", {}) or {})
        canonical = str(row["canonical_form"])
        if canonical in entity_nodes:
            meta["node_id"] = str(entity_nodes[canonical])
            direct_node_id = entity_nodes[canonical]
        elif canonical in relation_nodes:
            meta["node_id"] = str(relation_nodes[canonical])
            direct_node_id = relation_nodes[canonical]
        elif not meta.get("node_id"):
            node_candidates = support_nodes.get(str(row["surface_form"])) or support_nodes.get(
                canonical
            )
            if node_candidates:
                meta["node_id"] = str(node_candidates[0])
                direct_node_id = node_candidates[0]
            else:
                direct_node_id = None
        else:
            direct_node_id = None
        row["meta"] = meta
        if row["kind"] == "domain_term" and direct_node_id is not None:
            try:
                edge_repo.add_semantic_edge(
                    graph_id=graph_id,
                    src_node_id=direct_node_id,
                    dst_node_id=direct_node_id,
                    semantic_type="domain_term",
                    semantic_weight=0.60,
                    meta={"surface_form": row["surface_form"], "source": "autonomous_domain"},
                )
                result.edges_written += 1
            except Exception:
                pass

    for semantic_edge in semantic_memory.semantic_edges:
        try:
            edge_repo.add_semantic_edge(
                graph_id=graph_id,
                src_node_id=semantic_edge.src_node_id,
                dst_node_id=semantic_edge.dst_node_id,
                semantic_type=semantic_edge.semantic_type,
                semantic_weight=semantic_edge.semantic_weight,
                meta=dict(semantic_edge.meta),
            )
            result.edges_written += 1
        except Exception:
            pass

    result.lexicon_written = repo.merge_lexicon(graph_id=graph_id, rows=merged_rows)
    if (
        result.lexicon_written
        or result.sources_written
        or result.entity_nodes_written
        or result.edges_written
    ):
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
                        "sources_written": result.sources_written,
                        "entity_nodes_written": result.entity_nodes_written,
                        "relation_nodes_written": result.relation_nodes_written,
                        "fact_nodes_written": result.fact_nodes_written,
                        "value_nodes_written": result.value_nodes_written,
                        "time_nodes_written": result.time_nodes_written,
                        "edges_written": result.edges_written,
                        "detected_packs": result.detected_packs,
                        "graph_version": result.graph_version,
                    },
                )
            except Exception:
                pass
    return result


__all__ = ["DomainProfileRebuildResult", "run_domain_profile_rebuild"]

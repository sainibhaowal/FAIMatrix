"""Offline KB import and domain profile rebuild for Phase 8."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping, Optional, Sequence


@dataclass
class DomainKnowledgeImportResult:
    graph_id: str
    sources_written: int = 0
    lexicon_written: int = 0
    entity_nodes_written: int = 0
    relation_nodes_written: int = 0
    fact_nodes_written: int = 0
    value_nodes_written: int = 0
    time_nodes_written: int = 0
    edges_written: int = 0
    graph_version: int = 0
    errors: List[str] = field(default_factory=list)


def run_domain_knowledge_import(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    kb_rows: Sequence[Mapping[str, object]],
    domain_pack: Optional[str],
    node_repo,
    edge_repo,
    gv_repo,
    event_repo=None,
) -> DomainKnowledgeImportResult:
    from core.operators.domain_knowledge import (
        KBFact,
        build_kb_lexicon_rows,
        entity_key,
        fact_key,
        load_domain_profile_pack,
        relation_key,
        source_hash,
        time_key,
        value_key,
        vector_text_for_key,
    )
    from encoding.text_vectorizer import vectorize_text
    from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo

    repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
    result = DomainKnowledgeImportResult(graph_id=graph_id)

    facts = [
        KBFact(
            entity=str(row.get("entity", "")),
            relation=str(row.get("relation", "")),
            value=str(row.get("value", "")),
            time_value=str(row.get("time", "")),
            aliases=tuple(row.get("aliases", []) or ()),
            source_id=str(row.get("source_id") or source_hash(row)),
            source_kind=str(row.get("source_kind", "kb")),
            meta=dict(row.get("meta", {}) or {}),  # type: ignore[call-overload]
        )
        for row in kb_rows
        if str(row.get("entity", "")).strip()
        and str(row.get("relation", "")).strip()
        and str(row.get("value", "")).strip()
    ]

    lexicon_rows = build_kb_lexicon_rows(facts, domain_pack=domain_pack)
    lexicon_rows.extend(load_domain_profile_pack(domain_pack))

    entity_nodes = {}
    relation_nodes = {}
    value_nodes = {}
    time_nodes = {}
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
            meta={"relation_key": r_key},
        )
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=relation_nodes[r_key],
            dst_node_id=fact_node_id,
            semantic_type="entity_relation",
            semantic_weight=0.88,
            meta={"entity_key": e_key},
        )
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=fact_node_id,
            dst_node_id=value_nodes[v_key],
            semantic_type="fact_value",
            semantic_weight=0.84,
            meta={"value_key": v_key},
        )
        result.edges_written += 3
        if t_key:
            edge_repo.add_semantic_edge(
                graph_id=graph_id,
                src_node_id=fact_node_id,
                dst_node_id=time_nodes[t_key],
                semantic_type="fact_time",
                semantic_weight=0.82,
                meta={"time_key": t_key},
            )
            result.edges_written += 1

        for row in lexicon_rows:
            meta = dict(row.get("meta", {}) or {})
            if row["canonical_form"] == e_key and row["kind"] == "entity_alias":
                meta["node_id"] = str(entity_nodes[e_key])
                row["meta"] = meta
            elif row["canonical_form"] == r_key and row["kind"] == "relation_alias":
                meta["node_id"] = str(relation_nodes[r_key])
                row["meta"] = meta

    repo.replace_sources(
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
    result.sources_written = len(facts)

    # Add domain-term edges for profile lexicon rows when possible.
    for row in lexicon_rows:
        if row["kind"] == "domain_term":
            canonical = str(row["canonical_form"])
            target_id = entity_nodes.get(canonical) or relation_nodes.get(canonical)
            if target_id is not None:
                meta = dict(row.get("meta", {}) or {})
                meta["node_id"] = str(target_id)
                row["meta"] = meta
                edge_repo.add_semantic_edge(
                    graph_id=graph_id,
                    src_node_id=target_id,
                    dst_node_id=target_id,
                    semantic_type="domain_term",
                    semantic_weight=0.60,
                    meta={"surface_form": row["surface_form"]},
                )
                result.edges_written += 1

    result.lexicon_written = repo.replace_lexicon(graph_id=graph_id, rows=lexicon_rows)
    if result.sources_written or result.lexicon_written or result.edges_written:
        result.graph_version = gv_repo.bump(
            session=session,
            graph_id=graph_id,
            reason="domain_knowledge_import",
        )
        if event_repo is not None:
            try:
                event_repo.emit(
                    session,
                    graph_id,
                    "DOMAIN_KNOWLEDGE_IMPORT",
                    {
                        "sources_written": result.sources_written,
                        "lexicon_written": result.lexicon_written,
                        "entity_nodes_written": result.entity_nodes_written,
                        "relation_nodes_written": result.relation_nodes_written,
                        "fact_nodes_written": result.fact_nodes_written,
                        "value_nodes_written": result.value_nodes_written,
                        "time_nodes_written": result.time_nodes_written,
                        "edges_written": result.edges_written,
                        "graph_version": result.graph_version,
                    },
                )
            except Exception:
                pass
    return result


__all__ = ["DomainKnowledgeImportResult", "run_domain_knowledge_import"]

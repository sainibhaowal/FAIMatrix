"""Focused coverage for deterministic helpers and external-service boundaries.

These tests exercise the contracts of small, high-fan-out modules without
requiring a live Redis server or a PostgreSQL ``pg_dump`` binary.  They keep
the production code unchanged while making fallback and failure behavior
observable.
"""

from __future__ import annotations

import datetime as dt
import fnmatch
import importlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest


def _hop(edge_type: str, next_node_id: str) -> SimpleNamespace:
    return SimpleNamespace(edge_type=edge_type, next_node_id=next_node_id)


def _path(
    *,
    start: str = "A",
    nodes: tuple[str, ...] = ("B",),
    confidence: float = 0.8,
    end: str | None = None,
    explanation: str = "explanation",
    path_id: str = "path-1",
    metadata: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        start_node=start,
        hops=[_hop("supports", node) for node in nodes],
        confidence=confidence,
        end_node=end or nodes[-1],
        explanation=explanation,
        path_id=path_id,
        metadata=metadata or {},
    )


def test_kmeans_helpers_and_edge_cases():
    from core.clustering.kmeans_native import (
        _centers_equal,
        _kmeans_plus_plus_init,
        _mean_vector,
        _recompute_centers,
        choose_k,
        cosine_dist,
        cosine_sim,
        nearest_cluster,
        run_kmeans,
    )

    assert cosine_sim([0.0], [1.0]) == 0.0
    assert cosine_sim([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_dist([1.0], [1.0]) == pytest.approx(0.0)
    assert _mean_vector([]) == []
    assert _mean_vector([[0.0, 0.0]]) == [0.0, 0.0]
    assert _mean_vector([[1.0, 0.0], [0.0, 1.0]]) == pytest.approx([2**-0.5, 2**-0.5])
    assert choose_k(0) == 2
    assert choose_k(3) == 2
    assert choose_k(8) == 2
    assert choose_k(2000) == 20
    assert _centers_equal([[1.0]], [[1.0 + 1e-7]])
    assert not _centers_equal([[1.0]], [[1.1]])
    assert not _centers_equal([[1.0]], [[1.0], [2.0]])
    assert not _centers_equal([[1.0, 2.0]], [[1.0]])

    vectors = [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]
    centers = _kmeans_plus_plus_init(vectors, 3, __import__("random").Random(2))
    assert len(centers) == 3
    zero_centers = _kmeans_plus_plus_init(
        [[0.0, 0.0]] * 3, 3, __import__("random").Random(2)
    )
    assert zero_centers == [[0.0, 0.0]] * 3
    recomputed = _recompute_centers(vectors, [0, 0, 0], 2)
    assert recomputed[0]
    assert recomputed[1] == []

    empty = run_kmeans([], [], "empty")
    assert empty.k == 0 and empty.assignments == {} and empty.converged
    node_ids = [uuid4(), uuid4(), uuid4()]
    first = run_kmeans(node_ids, vectors, "graph", k=2, max_iterations=1)
    second = run_kmeans(node_ids, vectors, "graph", k=2)
    assert first.assignments == second.assignments
    assert first.k == 2
    assert sum(first.cluster_sizes.values()) == 3
    assert run_kmeans(node_ids, vectors, "graph", k=99).k == 3
    assert nearest_cluster([1.0, 0.0], []) == []
    assert nearest_cluster([1.0, 0.0], [[1.0, 0.0], []], top_k=1) == [0]


def test_encoding_package_lazy_exports_and_unknown_attribute():
    encoding = importlib.import_module("encoding")
    expected = {
        "FAIMVector",
        "VECTOR_DIMENSION",
        "SCHEMA_VERSION",
        "vectorize_block",
        "vectorize_blocks",
        "get_embedding_registry",
        "get_active_embedding_provider",
        "encode_texts",
        "encode_single",
        "EmbeddingProvider",
        "BgeM3LocalProvider",
        "OpenAIEmbeddingProvider",
        "CustomEmbeddingProvider",
        "EmbeddingProviderRegistry",
        "EmbeddingModelInfo",
        "EmbeddingResult",
    }
    assert set(encoding.__all__) == expected
    for name in expected:
        assert getattr(encoding, name) is not None
    with pytest.raises(AttributeError, match="no attribute"):
        getattr(encoding, "not_an_encoding_export")  # noqa: B009


def test_qdrant_index_fallback_preserves_all_index_operations(monkeypatch):
    import index.qdrant_index as qdrant_index

    monkeypatch.setattr(qdrant_index, "_get_client", lambda: None)
    project_id = uuid4()
    index = qdrant_index.FAIMIndex(project_id)
    vector_a = (1.0,) + (0.0,) * 255
    vector_b = (0.9,) + (0.1,) + (0.0,) * 254
    index.add("graph-a", "node-a", vector_a, level=1, kind="macro")
    index.add_batch(
        "graph-a",
        [("node-b", vector_b, 0, "atom")],
    )
    assert index.dim == 256
    assert not index.uses_qdrant
    assert index.top_k("graph-a", vector_a, k=2)[0][0] == "node-a"
    assert index.radius_search("graph-a", vector_a, radius=0.5, limit=2)
    assert index.search("tenant", "graph-a", list(vector_a), k=1)[0]["id"] == "node-a"
    assert index.count("graph-a") == 2
    assert index.count() == 2
    index.remove("graph-a", "node-b")
    assert index.count("graph-a") == 1
    index.delete_graph("graph-a")
    assert index.count() == 0
    index.delete_collection()
    qdrant_index.reset_qdrant_connection()


def test_cognitive_backfill_handles_empty_and_mixed_batches(monkeypatch, capsys):
    import store.pg.backfill_cognitive as backfill

    class Result:
        def __init__(self, *, scalar=None, rows=()):
            self._scalar = scalar
            self._rows = list(rows)

        def scalar(self):
            return self._scalar

        def fetchall(self):
            return list(self._rows)

    class Session:
        def __init__(self, results):
            self.results = iter(results)
            self.commits = 0

        def execute(self, _query):
            return next(self.results)

        def commit(self):
            self.commits += 1

    empty = Session([Result(scalar=0)])
    monkeypatch.setattr(backfill, "get_session", lambda: empty)
    backfill.backfill_nodes()
    assert empty.commits == 0
    assert "No nodes to backfill." in capsys.readouterr().out

    classified = type("Classified", (), {"value": "event"})()
    monkeypatch.setattr(backfill, "extract_galaxy_title", lambda raw: f"title:{raw}")
    monkeypatch.setattr(
        backfill, "generate_galaxy_id", lambda raw, title: f"gid:{raw}:{title}"
    )
    monkeypatch.setattr(
        backfill, "classify_cognitive_type", lambda text, context: classified
    )
    mixed = Session(
        [
            Result(scalar=2),
            Result(
                rows=[
                    ("macro-node", "macro-raw", {"canonical": "macro"}, "macro"),
                    ("atom-node", "meeting-call", {"text": "2026 fact"}, "atom"),
                ]
            ),
            Result(rows=[("fact",), ("fact",), ("event",)]),
            Result(),
            Result(),
            Result(rows=[]),
        ]
    )
    monkeypatch.setattr(backfill, "get_session", lambda: mixed)
    backfill.backfill_nodes(batch_size=2)
    assert mixed.commits == 1
    output = capsys.readouterr().out
    assert "Updated 2/2 nodes" in output
    assert "Backfill complete! Updated 2 nodes." in output


def test_cognitive_backfill_uses_safe_macro_fallback_on_member_query_error(monkeypatch):
    import store.pg.backfill_cognitive as backfill

    class Result:
        def __init__(self, *, scalar=None, rows=()):
            self._scalar = scalar
            self._rows = list(rows)

        def scalar(self):
            return self._scalar

        def fetchall(self):
            return list(self._rows)

    class Session:
        def __init__(self):
            self.calls = 0
            self.commits = 0

        def execute(self, _query):
            self.calls += 1
            if self.calls == 1:
                return Result(scalar=1)
            if self.calls == 2:
                return Result(rows=[("macro-node", "macro-raw", None, "macro")])
            if self.calls == 3:
                raise RuntimeError("member query unavailable")
            if self.calls == 4:
                return Result()
            return Result(rows=[])

        def commit(self):
            self.commits += 1

    session = Session()
    monkeypatch.setattr(backfill, "get_session", lambda: session)
    monkeypatch.setattr(backfill, "extract_galaxy_title", lambda _raw: "title")
    monkeypatch.setattr(backfill, "generate_galaxy_id", lambda _raw, _title: "gid")
    backfill.backfill_nodes(batch_size=1)
    assert session.commits == 1


@pytest.mark.asyncio
async def test_node_router_details_explanations_and_failure_isolation():
    from api.routers.node import explain_node, get_node
    from fastapi import HTTPException

    timestamp = dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc)
    node = SimpleNamespace(
        node_id="node-1",
        graph_id="graph-1",
        kind="atom",
        level=2,
        vector_hash="vector-1",
        residual=1_000_000_000,
        touch_count=4,
        raw_id="raw-1",
        block_id="block-1",
        anchor_json={"text": "fact"},
        opp_signature={"opposes": "none"},
        created_at=timestamp,
        updated_at=timestamp,
    )
    parent = SimpleNamespace(kind="macro")
    edges = [
        SimpleNamespace(src_node_id="parent-1", weight=500_000_000),
        SimpleNamespace(src_node_id="parent-2", weight=0),
    ]
    events = [
        SimpleNamespace(
            seq=1,
            kind="node_write",
            ts=timestamp,
            payload={"node_id": "node-1", "extra": True},
        ),
        SimpleNamespace(
            seq=2,
            kind="node_batch",
            ts=None,
            payload={"nodes": ["node-1"]},
        ),
        SimpleNamespace(
            seq=3,
            kind="vector_update",
            ts=timestamp,
            payload={"vector_hash": "vector-1"},
        ),
        SimpleNamespace(seq=4, kind="other", ts=timestamp, payload=None),
    ]

    class NodeRepo:
        def get_by_id(self, _graph_id, node_id):
            return {"node-1": node, "parent-1": parent}.get(node_id)

    class EdgeRepo:
        def get_parents(self, _graph_id, _node_id):
            return edges

    class EventRepo:
        def get_by_seq(self, *_args, **_kwargs):
            return events

    ctx = SimpleNamespace(
        node_repo=NodeRepo(),
        edge_repo=EdgeRepo(),
        event_repo=EventRepo(),
        session=object(),
    )
    detail = await get_node("node-1", graph_id="graph-1", ctx=ctx)
    assert detail.residual == 1.0
    assert detail.created_at == timestamp.isoformat()
    assert detail.anchor == {"text": "fact"}
    explanation = await explain_node(
        "node-1", graph_id="graph-1", limit_events=2, ctx=ctx
    )
    assert [item.kind for item in explanation.parents] == ["macro", "unknown"]
    assert explanation.fractions_sum == 0.5
    assert [item["seq"] for item in explanation.recent_events] == [3, 2]

    with pytest.raises(HTTPException) as missing:
        await get_node("missing", graph_id="graph-1", ctx=ctx)
    assert getattr(missing.value, "status_code", None) == 404

    class FailingEdges:
        def get_parents(self, *_args):
            raise RuntimeError("edge backend unavailable")

    class FailingEvents:
        def get_by_seq(self, *_args, **_kwargs):
            raise RuntimeError("event backend unavailable")

    degraded = SimpleNamespace(
        node_repo=NodeRepo(),
        edge_repo=FailingEdges(),
        event_repo=FailingEvents(),
        session=object(),
    )
    result = await explain_node("node-1", graph_id="graph-1", ctx=degraded)
    assert result.parents == []
    assert result.recent_events == []
    with pytest.raises(HTTPException) as missing_explanation:
        await explain_node("missing", graph_id="graph-1", ctx=ctx)
    assert missing_explanation.value.status_code == 404


def test_node_router_import_path_bootstrap(monkeypatch):
    import api.routers.node as node_module

    parent = str(Path(node_module.__file__).parent.parent.parent)
    monkeypatch.setattr(sys, "path", [item for item in sys.path if item != parent])
    reloaded = importlib.reload(node_module)
    assert parent in sys.path
    assert reloaded.router.prefix == "/node"


def test_path_constraints_optimizer_and_merge_strategies():
    from core.reasoning.paths import PathConstraints, PathOptimizer

    valid = _path()
    assert PathConstraints().check_path(valid) == (True, "Valid")
    assert PathConstraints(min_hops=2).check_path(valid)[0] is False
    assert PathConstraints(max_hops=0).check_path(valid)[0] is False
    assert PathConstraints(min_confidence=0.9).check_path(valid)[0] is False
    assert PathConstraints(max_confidence=0.5).check_path(valid)[0] is False
    assert PathConstraints(allowed_edge_types={"causes"}).check_path(valid)[0] is False
    assert (
        PathConstraints(forbidden_edge_types={"supports"}).check_path(valid)[0] is False
    )
    assert PathConstraints(allowed_edge_types={"supports"}).check_path(valid)[0]
    cyclic = _path(nodes=("A",))
    assert PathConstraints().check_path(cyclic)[0] is False
    assert PathConstraints(allow_cycles=True).check_path(cyclic)[0]

    recent = _path(metadata={"timestamp": "2026-11-19T00:00:00+00:00"})
    optimizer = PathOptimizer()
    assert optimizer._calculate_recency(recent, None) == 0.8
    assert (
        optimizer._calculate_recency(
            _path(), {"current_time": dt.datetime.now(dt.timezone.utc)}
        )
        == 0.5
    )
    assert (
        optimizer._calculate_recency(recent, {"current_time": "2026-11-20T00:00:00Z"})
        > 0
    )
    malformed = _path(metadata={"timestamp": "not-a-date"})
    assert (
        optimizer._calculate_recency(
            malformed, {"current_time": "2026-11-20T00:00:00Z"}
        )
        == 0.5
    )
    assert optimizer.score_path(valid) > 0

    low = _path(confidence=0.2, path_id="low")
    selected = optimizer.select_best_paths(
        [low, valid], top_k=1, constraints=PathConstraints()
    )
    assert selected[0][0] is valid
    assert (
        optimizer.select_best_paths([valid], constraints=PathConstraints(min_hops=2))
        == []
    )
    assert optimizer.diversify_paths([]) == []
    other = _path(start="X", nodes=("Y",), path_id="other")
    assert (
        len(optimizer.diversify_paths([(valid, 1.0), (valid, 0.9), (other, 0.8)])) == 2
    )
    assert optimizer._calculate_path_similarity(valid, other) == 0.0

    assert optimizer.merge_paths([]) == {"conclusion": None, "confidence": 0.0}
    best = optimizer.merge_paths([low, valid], strategy="best")
    assert best["source_path"] == "path-1"
    consensus = optimizer.merge_paths(
        [valid, _path(path_id="p2")], strategy="consensus"
    )
    assert consensus["supporting_paths"] == 2
    weighted = optimizer.merge_paths([low, valid], strategy="weighted")
    assert weighted["conclusion"] == valid.explanation
    assert (
        optimizer.merge_paths([_path(confidence=0.0)], strategy="weighted")[
            "confidence"
        ]
        == 0.0
    )
    with pytest.raises(ValueError, match="Unknown merge strategy"):
        optimizer.merge_paths([valid], strategy="unknown")


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.increments: dict[str, int] = {}
        self.expiries: dict[str, int] = {}
        self.fail = False

    def get(self, key: str):
        if self.fail:
            raise RuntimeError("redis unavailable")
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        if self.fail:
            raise RuntimeError("redis unavailable")
        self.values[key] = value.encode()
        self.expiries[key] = ttl

    def delete(self, *keys: str) -> int:
        if self.fail:
            raise RuntimeError("redis unavailable")
        removed = 0
        for key in keys:
            removed += int(self.values.pop(key, None) is not None)
        return removed

    def incr(self, key: str) -> int:
        if self.fail:
            raise RuntimeError("redis unavailable")
        self.increments[key] = self.increments.get(key, 0) + 1
        self.values[key] = str(self.increments[key]).encode()
        return self.increments[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expiries[key] = seconds

    def scan_iter(self, match: str):
        return iter([key for key in self.values if fnmatch.fnmatch(key, match)])


def test_redis_cache_contracts_and_fallbacks(monkeypatch):
    import cache.redis_client as redis_module
    from cache.redis_client import GlobalRateLimiter, RedisCache

    monkeypatch.setenv("REDIS_URL", "redis://example/9")
    assert redis_module._get_redis_url() == "redis://example/9"
    fake = _FakeRedis()
    monkeypatch.setattr(redis_module, "_get_client", lambda: fake)
    cache = RedisCache(uuid4())
    assert cache.set("text", "key", "value", ttl=12)
    assert cache.get("text", "key") == "value"
    assert fake.expiries[next(iter(fake.expiries))] == 12
    assert cache.delete("text", "key")
    assert cache.get("text", "key") is None
    assert cache.set_json("json", "key", {"a": 1})
    assert cache.get_json("json", "key") == {"a": 1}
    fake.values[cache._key("json", "bad")] = b"not-json"
    assert cache.get_json("json", "bad") is None
    assert not cache.set_json("json", "bad", object())
    assert cache.cache_node("g", "n", {"x": 1})
    assert cache.get_cached_node("g", "n") == {"x": 1}
    assert cache.invalidate_node("g", "n")
    assert cache.cache_graph_stats("g", {"nodes": 2})
    assert cache.get_graph_stats("g") == {"nodes": 2}
    assert cache.invalidate_graph_stats("g")
    assert cache.check_rate_limit("endpoint", limit=1, window_seconds=5)
    assert not cache.check_rate_limit("endpoint", limit=1)
    assert cache.get_rate_limit_remaining("endpoint", limit=1) == 0
    assert cache.clear_graph_cache("g") == 0
    cache.set("any", "g:item", "v")
    assert cache.clear_graph_cache("g") == 1
    cache.set("any", "a", "v")
    assert cache.clear_project_cache() >= 1

    limiter = GlobalRateLimiter(prefix="test:")
    assert limiter.check_rate_limit("login", limit=1)
    assert not limiter.check_rate_limit("login", limit=1)

    def unavailable():
        return None

    monkeypatch.setattr(redis_module, "_get_client", unavailable)
    assert cache.get("x", "y") is None
    assert not cache.set("x", "y", "z")
    assert not cache.delete("x", "y")
    assert cache.check_rate_limit("x")
    assert cache.get_rate_limit_remaining("x") == 100
    assert cache.clear_graph_cache("g") == 0
    assert cache.clear_project_cache() == 0
    assert limiter.check_rate_limit("login")

    monkeypatch.setattr(redis_module, "_get_client", lambda: fake)
    fake.fail = True
    assert cache.get("x", "y") is None
    assert not cache.set("x", "y", "z")
    assert not cache.delete("x", "y")
    assert cache.check_rate_limit("x")
    assert cache.get_rate_limit_remaining("x") == 100
    assert cache.clear_graph_cache("g") == 0
    assert cache.clear_project_cache() == 0
    assert limiter.check_rate_limit("login")


def test_backup_success_failure_retention_and_compression(monkeypatch, tmp_path: Path):
    from orchestration.jobs import backup

    monkeypatch.setattr(backup, "DB_URL", None)
    missing = backup.perform_backup(backup_dir=tmp_path, db_url=None)
    assert missing["status"] == "error"
    assert "not configured" in (missing["message"] or "")

    def fake_run(command, **kwargs):
        output = Path(
            next(arg.split("=", 1)[1] for arg in command if arg.startswith("--file="))
        )
        output.write_text("SQL DATA", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(backup.subprocess, "run", fake_run)
    plain = backup.perform_backup(backup_dir=tmp_path, db_url="postgresql://db/test")
    assert plain["status"] == "success"
    assert Path(plain["backup_file"] or "").read_text(encoding="utf-8") == "SQL DATA"
    compressed = backup.perform_backup(
        backup_dir=tmp_path, db_url="postgresql://db/test", compress=True
    )
    assert compressed["status"] == "success"
    assert str(compressed["backup_file"]).endswith(".sql.gz")
    assert Path(compressed["backup_file"] or "").exists()

    def failed_run(_command, **_kwargs):
        raise subprocess.CalledProcessError(1, "pg_dump", stderr="bad database")

    monkeypatch.setattr(backup.subprocess, "run", failed_run)
    failed = backup.perform_backup(backup_dir=tmp_path, db_url="postgresql://db/test")
    assert failed["status"] == "error"
    assert "bad database" in (failed["message"] or "")
    monkeypatch.setattr(
        backup.subprocess,
        "run",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    unexpected = backup.perform_backup(
        backup_dir=tmp_path, db_url="postgresql://db/test"
    )
    assert unexpected["status"] == "error" and "boom" in (unexpected["message"] or "")

    assert backup.list_backups(tmp_path)
    assert backup.list_backups(tmp_path / "missing") == []
    old = tmp_path / "backup_faim_old.sql"
    old.write_text("old", encoding="utf-8")
    very_old = tmp_path / "backup_faim_very_old.sql.gz"
    very_old.write_bytes(b"old")
    now = dt.datetime.now().timestamp()
    old.touch()
    very_old.touch()
    import os

    os.utime(old, (now - 30, now - 30))
    os.utime(very_old, (now - 60, now - 60))
    assert backup.get_latest_backup(tmp_path) is not None
    deleted = backup.cleanup_old_backups(keep=1, backup_dir=tmp_path)
    assert len(deleted) >= 1


def test_user_repository_full_lifecycle(db_session):
    from store.pg.repos.user_repo import UserRepository

    user_id = uuid4()
    repo = UserRepository(db_session)
    assert repo.get_by_email("missing@example.com") is None
    assert repo.get_by_id(user_id) is None
    user = repo.create_user(user_id, "  USER@example.com ", "Initial")
    assert user.email == "user@example.com"
    assert repo.get_by_email(" USER@example.com ").id == user_id
    assert repo.get_by_id(user_id).id == user_id
    assert repo.update_profile(user_id, "Updated").full_name == "Updated"
    assert repo.update_profile(uuid4(), "Missing") is None
    assert repo.set_totp_pending(user_id, "encrypted") is user
    assert user.totp_enabled is False and user.recovery_code_hashes == []
    assert repo.enable_totp(user_id, "encrypted-2", ["hash"]) is user
    assert user.totp_enabled is True and user.recovery_code_hashes == ["hash"]
    assert repo.set_recovery_code_hashes(user_id, ["hash-2"]) is user
    assert user.recovery_code_hashes == ["hash-2"]
    assert repo.disable_totp(user_id) is user
    assert user.totp_enabled is False and user.totp_secret_encrypted is None
    for method, args in (
        (repo.set_totp_pending, (uuid4(), "secret")),
        (repo.enable_totp, (uuid4(), "secret", [])),
        (repo.disable_totp, (uuid4(),)),
        (repo.set_recovery_code_hashes, (uuid4(), [])),
    ):
        with pytest.raises(ValueError, match="User not found"):
            method(*args)


def test_implication_engine_matches_applies_chains_and_filters():
    from core.reasoning.implications import ImplicationEngine, ImplicationRule

    rule = ImplicationRule(
        rule_id="custom",
        name="custom",
        description="custom",
        conditions={"kind": ["alpha", "beta"], "text": "IMPORTANT"},
        conclusion={"derived": True},
        confidence=0.75,
    )
    assert rule.matches({"kind": "alpha", "text": "an important note"})
    assert not rule.matches({"kind": "gamma", "text": "an important note"})
    assert not rule.matches({"kind": "alpha", "text": "unrelated"})
    assert rule.matches({"missing": None}) is False
    applied = rule.apply({})
    assert applied == {"derived": True, "_rule_confidence": 0.75, "_rule_id": "custom"}

    engine = ImplicationEngine()
    engine.add_rule(rule)
    conclusions = engine.evaluate(
        {"edge_type": "causes", "kind": "alpha", "text": "important"}
    )
    assert any(item["relation_type"] == "explanation" for item in conclusions)
    assert any(item.get("derived") is True for item in conclusions)
    assert engine.get_rules_by_type("cause")
    facts = engine.chain_forward([{"edge_type": "contradicts"}], max_iterations=2)
    assert len(facts) == 2
    assert facts == engine.chain_forward(facts[:1], max_iterations=2)
    assert engine._hash_fact({"b": 2, "a": 1}) == engine._hash_fact({"a": 1, "b": 2})


def test_query_cache_and_stats_cache_with_redis_and_failures(monkeypatch):
    import cache.query_cache as query_cache_module
    from cache.query_cache import (
        QueryCache,
        StatsCache,
        make_cache_key,
        parse_cache_key,
    )

    assert query_cache_module.compute_query_hash((1.0, 2.0))
    key = make_cache_key("tenant", "graph", 4, "hash", "fast", 3)
    assert parse_cache_key(key)["graph_version"] == 4
    assert parse_cache_key("invalid") is None
    assert parse_cache_key("faim:query:tenant:graph:vbad:hash:fast:k3") is None
    assert parse_cache_key("faim:query:too:short") is None
    fake = _FakeRedis()
    monkeypatch.setattr(query_cache_module, "_get_client", lambda: fake)
    cache = QueryCache("tenant", default_ttl=11)
    values = [("node", 0.9)]
    assert cache.get("graph", 1, (1.0,), "fast", 1) is None
    assert cache.set("graph", 1, (1.0,), "fast", 1, values)
    assert cache.get("graph", 1, (1.0,), "fast", 1) == values
    assert cache.set("graph", 2, (1.0,), "fast", 1, values, ttl=22)
    assert cache.invalidate_graph("graph") == 2
    assert cache.clear() == 0
    stats = StatsCache("tenant", default_ttl=7)
    assert stats.get("graph", 1) is None
    assert stats.set("graph", 1, {"count": 1})
    assert stats.get("graph", 1) == {"count": 1}
    assert stats.invalidate("graph") == 1
    fake.fail = True
    assert cache.get("graph", 1, (1.0,), "fast", 1) is None
    assert not cache.set("graph", 1, (1.0,), "fast", 1, values)
    assert cache.invalidate_graph("graph") == 0 and cache.clear() == 0
    assert stats.get("graph", 1) is None
    assert not stats.set("graph", 1, {"count": 1})
    assert stats.invalidate("graph") == 0


def test_invariant_checks_cover_pass_and_failure_paths():
    from core.invariants import (
        check_all_invariants,
        check_boundedness,
        check_D_range,
        check_energy_bounded,
        check_event_coverage,
        check_fractal_invariants,
        check_H_range,
        check_inheritance_sum,
        check_lambda_range,
        check_no_orphan_edges,
        check_scaling_bounds,
    )

    class NodeRepo:
        def __init__(self, nodes):
            self.nodes = nodes

        def list_nodes(self, _graph_id, limit):
            assert limit == 10000
            return self.nodes

    class EdgeRepo:
        def __init__(self, parents, edges):
            self.parents = parents
            self.edges = edges

        def list_parents(self, _graph_id, node_id):
            return self.parents.get(node_id, [])

        def list_all_edges(self, _graph_id, limit):
            assert limit == 10000
            return self.edges

    good = SimpleNamespace(node_id="n1", v_native=[0.0, 1.0], residual=500_000_000)
    bad = SimpleNamespace(
        node_id="n2", v_native=[float("nan"), float("inf")], residual=2_000_000_000
    )
    node_repo = NodeRepo([good, bad])
    edge_repo = EdgeRepo(
        {"n1": [("p1", 0.4), ("p2", 0.6)], "n2": [("p1", 0.2)]},
        [
            SimpleNamespace(src_node_id="n1", dst_node_id="n2"),
            SimpleNamespace(src_node_id="orphan", dst_node_id="n1"),
        ],
    )
    inheritance = check_inheritance_sum(edge_repo, node_repo, "g")
    assert not inheritance.passed and any("n2" in error for error in inheritance.errors)
    bounded = check_boundedness(node_repo, "g")
    assert not bounded.passed
    assert check_event_coverage(
        SimpleNamespace(list=lambda **_kwargs: [1, 2]), "g", 2
    ).passed
    assert not check_event_coverage(
        SimpleNamespace(list=lambda **_kwargs: [1]), "g", 2
    ).passed
    assert not check_no_orphan_edges(edge_repo, node_repo, "g").passed
    assert not check_all_invariants(node_repo, edge_repo, "g").passed
    assert check_scaling_bounds(1.0).passed and not check_scaling_bounds(0.0).passed
    assert check_D_range(0.0).passed and not check_D_range(11.0).passed
    assert check_H_range(1.0).passed and not check_H_range(-1.0).passed
    assert check_lambda_range(0.0).passed and not check_lambda_range(2.0).passed
    assert check_energy_bounded(2.0).passed and not check_energy_bounded(3.0).passed
    assert check_fractal_invariants(1.0, 1.0, 0.5, 0.5, 1.0).passed
    assert not check_fractal_invariants(0.0, 11.0, -1.0, 2.0, 3.0).passed


def test_raw_cipher_modes_and_encrypted_store_delegation(monkeypatch):
    from store.raw.crypto import (
        EnvelopeCipher,
        FernetCipher,
        NoopCipher,
        build_cipher_from_env,
    )
    from store.raw.encrypted_payload_store import EncryptedRawStore

    assert NoopCipher().encrypt("g", b"plain") == b"plain"
    assert NoopCipher().decrypt("g", b"plain") == b"plain"
    assert NoopCipher().version() == "v2"
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    cipher = FernetCipher(default_key=key)
    ciphertext = cipher.encrypt("graph", b"secret")
    assert ciphertext != b"secret"
    assert cipher.decrypt("graph", ciphertext) == b"secret"
    assert cipher._get_fernet("graph") is cipher._get_fernet("graph")
    monkeypatch.setenv("FAIM_GRAPH_KEY_special", key.decode())
    assert (
        FernetCipher().decrypt("special", FernetCipher(key).encrypt("special", b"x"))
        == b"x"
    )
    with pytest.raises(RuntimeError, match="No Fernet key"):
        FernetCipher().encrypt("missing", b"x")

    assert isinstance(build_cipher_from_env(mode_override="none"), NoopCipher)
    assert isinstance(build_cipher_from_env(mode_override="plain"), NoopCipher)
    monkeypatch.setenv("FAIM_GRAPH_KEY_DEFAULT", key.decode())
    assert isinstance(build_cipher_from_env(mode_override="fernet"), FernetCipher)
    with pytest.raises(RuntimeError, match="requires tenant_id"):
        build_cipher_from_env(mode_override="envelope")
    with pytest.raises(RuntimeError, match="requires session_factory"):
        build_cipher_from_env(mode_override="envelope", tenant_id="tenant")
    monkeypatch.setenv("FAIM_MASTER_KEY", "55" * 32)
    envelope = build_cipher_from_env(
        mode_override="envelope", tenant_id="tenant", session_factory=lambda: None
    )
    assert isinstance(envelope, EnvelopeCipher)
    with pytest.raises(RuntimeError, match="Unknown"):
        build_cipher_from_env(mode_override="unknown")

    class Cipher:
        def __init__(self):
            self.calls: list[tuple[str, str, bytes]] = []

        def encrypt(self, graph_id, value):
            self.calls.append(("encrypt", graph_id, value))
            return b"enc:" + value

        def decrypt(self, graph_id, value):
            self.calls.append(("decrypt", graph_id, value))
            return value.removeprefix(b"enc:")

        def version(self):
            return "fake"

    class Inner:
        def __init__(self):
            self.data = b""

        def store(self, value, **_kwargs):
            self.data = value
            return SimpleNamespace(sha256="sha")

        def load(self, _ref, **_kwargs):
            return self.data

        def exists(self, _ref):
            return True

        def exists_by_sha(self, _sha):
            return True

        def load_by_sha(self, _sha, **_kwargs):
            return self.data

        def verify(self, _ref):
            return True

        def delete(self, _ref):
            return True

        def delete_by_sha(self, _sha):
            return True

        def get_stats(self):
            return {"bytes": 10}

    fake_cipher = Cipher()
    inner = Inner()
    store = EncryptedRawStore(inner, fake_cipher, graph_id="default")
    ref = store.store(b"payload", mime_type="text/plain", graph_id="graph")
    assert store.load(ref, graph_id="graph") == b"payload"
    assert store.exists(ref) and store.exists_by_sha("sha")
    assert store.load_by_sha("sha", graph_id="graph") == b"payload"
    assert store.verify(ref) and store.delete(ref) and store.delete_by_sha("sha")
    assert store.get_stats() == {
        "bytes": 10,
        "encrypted": True,
        "cipher_version": "fake",
    }
    assert store.version() == "v1+fake"

    class MinimalInner:
        def store(self, value, **_kwargs):
            self.value = value
            return ref

        def load(self, _ref, **_kwargs):
            return self.value

        def exists(self, _ref):
            return False

    minimal = EncryptedRawStore(MinimalInner(), fake_cipher)
    assert minimal.exists_by_sha("missing") is False
    with pytest.raises(AttributeError, match="load_by_sha"):
        minimal.load_by_sha("missing")
    assert minimal.verify(ref) is False
    assert minimal.delete(ref) is False
    assert minimal.delete_by_sha("missing") is False
    assert minimal.get_stats() == {"encrypted": True, "cipher_version": "fake"}


def test_deterministic_ann_and_collection_edge_cases():
    from index.deterministic_ann import (
        VectorPoint,
        build_vptree,
        exact_top_k,
        search_vptree,
    )
    from index.qdrant_collections import (
        CollectionSchema,
        collection_name,
        parse_collection_name,
        validate_payload,
    )

    node_a, node_b = uuid4(), uuid4()
    points = [
        VectorPoint(node_a, (0.0, 0.0)),
        VectorPoint(node_b, (1.0, 0.0)),
    ]
    assert build_vptree([]) is None
    assert build_vptree([points[0]]).threshold == 0
    assert exact_top_k(points, (1.0, 0.0), 0) == []
    root = build_vptree(points)
    assert search_vptree(None, (1.0, 0.0), 2) == []
    assert search_vptree(root, (1.0, 0.0), 0) == []
    assert search_vptree(root, (1.0, 0.0), 2)[0][0] == node_b

    project_id = uuid4()
    name = collection_name(project_id)
    assert parse_collection_name(name) == str(project_id).replace("-", "_")
    assert parse_collection_name("other_collection") is None
    schema = CollectionSchema("faim_test")
    assert schema.to_qdrant_config() == {"size": 256, "distance": "COSINE"}
    assert validate_payload({"graph_id": "g", "node_id": "n"}) == []
    assert validate_payload({}) == [
        "Missing required field: graph_id",
        "Missing required field: node_id",
    ]

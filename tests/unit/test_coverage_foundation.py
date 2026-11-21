"""Focused regression coverage for local SQLite, builders, and observability.

These tests intentionally exercise real behavior instead of importing modules
only to inflate the coverage number.  External downloads and WordNet are
replaced with deterministic in-memory fakes so local CI stays offline.
"""

from __future__ import annotations

import gzip
import io
import json
import logging
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_benchmark_repo_roundtrip_and_retention_on_sqlite() -> None:
    from store.pg.models_faim import BenchmarkSampleModel
    from store.pg.repos.benchmark_repo import BenchmarkRepo

    engine = create_engine("sqlite:///:memory:")
    BenchmarkSampleModel.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    repo = BenchmarkRepo()

    with factory() as session:
        latest = repo.insert_sample(
            session,
            "tenant-a",
            "graph-a",
            "query_ms",
            12.5,
            {"profile": "fast"},
        )
        session.commit()
        assert latest.metric_value == 12.5
        assert latest.labels == {"profile": "fast"}

        old = BenchmarkSampleModel(
            tenant_id="tenant-a",
            graph_id="graph-a",
            metric_name="query_ms",
            metric_value=99.0,
            labels={},
            recorded_at=datetime.now() - timedelta(days=31),
        )
        other_tenant = BenchmarkSampleModel(
            tenant_id="tenant-b",
            graph_id="graph-a",
            metric_name="query_ms",
            metric_value=77.0,
            labels={},
            recorded_at=datetime.now(),
        )
        session.add_all([old, other_tenant])
        session.commit()

        samples = repo.get_samples(
            session, "tenant-a", "graph-a", "query_ms", limit=10, hours_back=24
        )
        assert [sample.metric_value for sample in samples] == [12.5]
        assert (
            repo.get_latest(session, "tenant-a", "graph-a", "query_ms").metric_value
            == 12.5
        )
        assert (
            repo.get_latest(session, "tenant-b", "graph-a", "query_ms").metric_value
            == 77.0
        )

        assert repo.cleanup_old(session, "tenant-a", retention_days=30) == 1
        session.commit()
        assert (
            repo.get_latest(session, "tenant-a", "graph-a", "query_ms").metric_value
            == 12.5
        )


def test_conceptnet_builder_streams_and_serializes_deterministically(
    monkeypatch, tmp_path
) -> None:
    from lexical import conceptnet_builder as builder

    assert builder.clean_concept("/c/en/car/n") == "car"
    assert builder.clean_concept("/c/en/red_car/n") == "red car"
    assert builder.clean_concept("bad") == ""
    assert builder.clean_concept("/c/en/1/n") == ""

    rows = b"".join(
        [
            b"/a\t/r/Synonym\t/c/en/car/n\t/c/en/auto/n\n",
            b"/a\t/r/FormOf\t/c/en/vehicle/n\t/c/en/car/n\n",
            b"/a\t/r/RelatedTo\t/c/en/car/n\t/c/en/wheel/n\n",
            b"/a\t/r/NotUsed\t/c/en/car/n\t/c/en/unused/n\n",
            b"malformed\n",
        ]
    )

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setattr(
        builder.urllib.request,
        "urlopen",
        lambda _request: Response(gzip.compress(rows)),
    )
    result = builder.build_conceptnet_synonyms()
    assert result["car"] == ["auto", "vehicle", "wheel"]
    assert result["auto"] == ["car"]
    assert "unused" not in result

    output = tmp_path / "lexicon.json.gz"
    monkeypatch.setattr(builder, "build_conceptnet_synonyms", lambda: result)
    assert builder.write_conceptnet_data(output) == 4
    with gzip.open(output, "rt", encoding="utf-8") as handle:
        assert json.load(handle) == result


def test_multilingual_builder_helpers_and_fake_omw_pack(monkeypatch, tmp_path) -> None:
    from lexical import multilingual_lexicon_builder as builder

    assert builder._slugify("  A/B concept! ") == "a_b_concept"
    assert builder._slugify("...") == "concept"
    assert builder._normalize_form("Straße__", "de") == "strasse"
    assert builder._choose_form(["Long form" * 20, "short"], "en") == "short"
    assert builder._choose_form([], "en") == ""

    class Word:
        def __init__(self, *forms):
            self._forms = forms

        def forms(self):
            return self._forms

    class Synset:
        ili = "i1"

        def words(self):
            return [Word("Cats", "cat")]

    class English:
        def synsets(self):
            return [Synset(), Synset()]

    class Translation:
        def __init__(self, language):
            self.language = language

        def synsets(self, *, ili):
            assert ili == "i1"
            if self.language in {"es", "fr"}:
                return [SimpleNamespace(words=lambda: [Word(self.language + " form")])]
            return []

    class FakeWN:
        def Wordnet(self, spec):
            return (
                English() if spec == builder.OMW_SPECS["en"] else Translation(spec[4:6])
            )

    monkeypatch.setattr(builder, "_import_wn", lambda: FakeWN())
    rows = builder.build_omw_pack(max_rows=10)
    assert len(rows) == 1
    assert rows[0]["en"] == "cat"
    assert rows[0]["es"] == "es form"
    assert rows[0]["fr"] == "fr form"
    assert rows[0]["de"] == ""

    output = tmp_path / "omw.tsv.gz"
    assert builder.write_pack(output, rows) == 1
    with gzip.open(output, "rt", encoding="utf-8", newline="") as handle:
        lines = handle.read().splitlines()
    assert lines[0].startswith("concept_key\ten\tde")
    assert "cat" in lines[1]


def test_structured_logging_context_filter_and_exception_paths(
    monkeypatch, caplog
) -> None:
    from runtime.logging import (
        ContextLogger,
        JSONFormatter,
        RedactingFilter,
        get_logger,
        setup_logging,
    )

    filter_obj = RedactingFilter()
    dict_record = logging.LogRecord("test", logging.INFO, __file__, 1, "%s", (), None)
    dict_record.msg = "secret=%s"
    dict_record.args = {"value": "password=hidden"}
    assert filter_obj.filter(dict_record) is True
    assert "hidden" not in str(dict_record.args)

    tuple_record = logging.LogRecord("test", logging.INFO, __file__, 1, "%s", (), None)
    tuple_record.args = ("Bearer hidden-token", 42)
    filter_obj.filter(tuple_record)
    assert "hidden-token" not in tuple_record.args[0]
    assert tuple_record.args[1] == 42

    try:
        raise RuntimeError("diagnostic failure")
    except RuntimeError:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            __file__,
            1,
            "failure",
            (),
            __import__("sys").exc_info(),
        )
    for key, value in {"endpoint": "/health", "component": "api"}.items():
        setattr(record, key, value)
    payload = json.loads(JSONFormatter().format(record))
    assert payload["endpoint"] == "/health"
    assert payload["component"] == "api"
    assert "diagnostic failure" in payload["exception"]

    logger = get_logger("coverage.logging").bind(request_id="req-1")
    with caplog.at_level(logging.DEBUG):
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
    assert {record.message for record in caplog.records} >= {
        "debug",
        "info",
        "warning",
        "error",
    }
    assert isinstance(logger, ContextLogger)

    setup_logging(level="DEBUG", json_format=True)
    setup_logging(level="INFO", json_format=False)


def test_store_lazy_exports_are_resolvable() -> None:
    import store
    import store.journal
    import store.pg
    import store.pg.repos
    import store.raw

    assert store.RawStore is not None
    assert store.SessionFactory is not None
    assert store.get_engine is not None
    assert store.atomic is not None
    assert store.Base is not None
    assert store.RawRepo is not None
    assert store.EventRepo is not None
    assert store.SnapshotRepo is not None
    assert store.GraphVersionRepo is not None
    assert store.StorageFileRepo is not None
    assert store.EventJournal is not None
    assert store.raw.RawStore is not None
    assert store.raw.PayloadCipher is not None
    assert store.raw.EncryptedRawStore is not None
    assert store.pg.SessionFactory is not None
    assert store.pg.Base is not None
    assert store.pg.repos.AuthRepo is not None
    assert store.journal.EventJournal is not None

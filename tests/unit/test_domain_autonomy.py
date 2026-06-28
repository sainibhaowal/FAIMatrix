from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.core.operators.domain_knowledge import (
    detect_domain_profile_packs,
    load_domain_profile_pack,
)
from faim_native.orchestration.domain_autonomy import (
    enqueue_domain_autonomy_if_needed,
)
from faim_native.store.pg.models_faim import JobModel, create_all_tables


def _session():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_domain_pack_loading_and_detection_are_real():
    detected = detect_domain_profile_packs(
        [
            "Revenue, EBITDA margin, and cash flow improved.",
            "The API latency for the service improved after deployment.",
        ]
    )
    assert "finance" in detected
    assert "software" in detected
    assert "general" in detected

    finance_rows = load_domain_profile_pack("finance")
    assert any(row["surface_form"] == "ebitda" for row in finance_rows)
    assert any(row["kind"] == "relation_alias" for row in finance_rows)


def test_domain_pack_detection_defaults_to_general_for_broad_text():
    detected = detect_domain_profile_packs(["General project update and status review."])
    assert detected[0] == "general"


def test_domain_autonomy_enqueue_reuses_existing_active_job(monkeypatch):
    monkeypatch.setenv("FAIM_DOMAIN_AUTONOMY_ENABLED", "true")
    session = _session()
    try:
        first = enqueue_domain_autonomy_if_needed(
            session=session,
            tenant_id="tenant_domain_auto",
            graph_id="graph_domain_auto",
            source="memory_write",
            request_id="req-1",
        )
        second = enqueue_domain_autonomy_if_needed(
            session=session,
            tenant_id="tenant_domain_auto",
            graph_id="graph_domain_auto",
            source="storage_upload_worker",
            request_id="req-2",
        )

        assert first.status == "enqueued"
        assert first.job_id is not None
        assert second.status == "existing"
        assert second.job_id == first.job_id
        assert (
            session.query(JobModel)
            .filter_by(
                tenant_id="tenant_domain_auto",
                graph_id="graph_domain_auto",
                kind="domain_autonomy",
            )
            .count()
            == 1
        )
    finally:
        session.close()

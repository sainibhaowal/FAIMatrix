"""Repository for benchmark samples — time-series metric storage."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from store.pg.models_faim import BenchmarkSampleModel


class BenchmarkRepo:
    """Insert, query, and cleanup benchmark time-series data."""

    def insert_sample(
        self,
        session: Session,
        tenant_id: str,
        graph_id: str,
        metric_name: str,
        metric_value: float,
        labels: Optional[Dict] = None,
    ) -> BenchmarkSampleModel:
        """Insert a single benchmark sample."""
        sample = BenchmarkSampleModel(
            tenant_id=tenant_id,
            graph_id=graph_id,
            metric_name=metric_name,
            metric_value=metric_value,
            labels=labels or {},
            recorded_at=datetime.now(),
        )
        session.add(sample)
        session.flush()
        return sample

    def get_samples(
        self,
        session: Session,
        tenant_id: str,
        graph_id: str,
        metric_name: str,
        limit: int = 100,
        hours_back: int = 24,
    ) -> List[BenchmarkSampleModel]:
        """Query samples for a metric, newest first."""
        cutoff = datetime.now() - timedelta(hours=hours_back)
        query = select(BenchmarkSampleModel).where(
            and_(
                BenchmarkSampleModel.tenant_id == tenant_id,
                BenchmarkSampleModel.graph_id == graph_id,
                BenchmarkSampleModel.metric_name == metric_name,
                BenchmarkSampleModel.recorded_at >= cutoff,
            )
        ).order_by(desc(BenchmarkSampleModel.recorded_at)).limit(limit)
        return list(session.execute(query).scalars())

    def get_latest(
        self,
        session: Session,
        tenant_id: str,
        graph_id: str,
        metric_name: str,
    ) -> Optional[BenchmarkSampleModel]:
        """Get the single most recent sample for a metric."""
        query = select(BenchmarkSampleModel).where(
            and_(
                BenchmarkSampleModel.tenant_id == tenant_id,
                BenchmarkSampleModel.graph_id == graph_id,
                BenchmarkSampleModel.metric_name == metric_name,
            )
        ).order_by(desc(BenchmarkSampleModel.recorded_at)).limit(1)
        return session.execute(query).scalar()

    def cleanup_old(
        self,
        session: Session,
        tenant_id: str,
        retention_days: int = 30,
    ) -> int:
        """Delete samples older than retention_days. Returns count deleted."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        from sqlalchemy import delete
        stmt = delete(BenchmarkSampleModel).where(
            and_(
                BenchmarkSampleModel.tenant_id == tenant_id,
                BenchmarkSampleModel.recorded_at < cutoff,
            )
        )
        result = session.execute(stmt)
        session.flush()
        return result.rowcount or 0

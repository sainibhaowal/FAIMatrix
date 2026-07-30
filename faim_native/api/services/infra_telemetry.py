"""Infrastructure telemetry — CPU, memory, database, Redis, Docker metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import psutil
from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class ProcessMetrics:
    """Current process CPU and memory."""

    cpu_percent: float
    memory_rss_mb: float
    memory_peak_mb: float


@dataclass
class PostgresMetrics:
    """PostgreSQL health metrics."""

    active_connections: int
    max_connections: int
    db_size_mb: float
    total_tables: int


@dataclass
class RedisMetrics:
    """Redis memory and hit rate."""

    memory_used_mb: float
    connected_clients: int
    keyspace_hit_rate: float
    evicted_keys: int


@dataclass
class DockerMetrics:
    """Docker container limits and usage."""

    cpu_limit_cores: float
    memory_limit_mb: int
    cpu_utilization_percent: float
    memory_utilization_percent: float


@dataclass
class InfrastructureSnapshot:
    """Complete infrastructure telemetry."""

    process: ProcessMetrics
    postgres: PostgresMetrics
    redis: Optional[RedisMetrics]
    docker: DockerMetrics


class InfraTelemetry:
    """Collect real infrastructure metrics."""

    @staticmethod
    def get_process_metrics() -> ProcessMetrics:
        """Get process CPU and memory."""
        try:
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            mem_info = process.memory_info()
            memory_rss_mb = mem_info.rss / (1024 * 1024)
            memory_peak_mb = memory_rss_mb  # Simplified; could track peak

            return ProcessMetrics(
                cpu_percent=float(cpu_percent),
                memory_rss_mb=float(memory_rss_mb),
                memory_peak_mb=float(memory_peak_mb),
            )
        except Exception as e:
            print(f"[InfraTelemetry] process metrics failed: {e}")
            return ProcessMetrics(
                cpu_percent=0.0, memory_rss_mb=0.0, memory_peak_mb=0.0
            )

    @staticmethod
    def get_postgres_metrics(session: Session) -> PostgresMetrics:
        """Get PostgreSQL metrics from current connection."""
        try:
            # Active connections
            result = (
                session.execute(text("SELECT count(*) FROM pg_stat_activity")).scalar()
                or 0
            )
            active_connections = int(result)

            # Max connections
            result = session.execute(text("SHOW max_connections")).scalar() or "100"
            max_connections = int(result)

            # Database size in MB
            result = (
                session.execute(
                    text(
                        "SELECT sum(pg_database_size(datname)) / 1024.0 / 1024.0 FROM pg_database"
                    )
                ).scalar()
                or 0
            )
            db_size_mb = float(result)

            # Table count
            result = (
                session.execute(
                    text(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                ).scalar()
                or 0
            )
            total_tables = int(result)

            return PostgresMetrics(
                active_connections=active_connections,
                max_connections=max_connections,
                db_size_mb=db_size_mb,
                total_tables=total_tables,
            )
        except Exception as e:
            print(f"[InfraTelemetry] postgres metrics failed: {e}")
            return PostgresMetrics(
                active_connections=0,
                max_connections=100,
                db_size_mb=0.0,
                total_tables=0,
            )

    @staticmethod
    def get_redis_metrics(redis_client: Optional[Any] = None) -> Optional[RedisMetrics]:
        """Get Redis metrics if available."""
        if not redis_client:
            return None

        try:
            info = redis_client.info()
            memory_bytes = info.get("used_memory", 0)
            memory_used_mb = memory_bytes / (1024 * 1024)
            connected_clients = info.get("connected_clients", 0)
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0.0
            evicted_keys = info.get("evicted_keys", 0)

            return RedisMetrics(
                memory_used_mb=float(memory_used_mb),
                connected_clients=int(connected_clients),
                keyspace_hit_rate=float(hit_rate),
                evicted_keys=int(evicted_keys),
            )
        except Exception as e:
            print(f"[InfraTelemetry] redis metrics failed: {e}")
            return None

    @staticmethod
    def get_docker_metrics() -> DockerMetrics:
        """Get Docker container limits and usage."""
        try:
            # CPU limits from cgroup
            cpu_limit_cores = 2.0  # Default to 2 CPU (from compose)
            try:
                with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as f:
                    quota = int(f.read().strip())
                with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as f:
                    period = int(f.read().strip())
                if quota > 0 and period > 0:
                    cpu_limit_cores = quota / period
            except Exception:
                pass

            # Memory limit from cgroup
            memory_limit_mb = 1024  # Default to 1GB (from compose)
            try:
                with open("/sys/fs/cgroup/memory/memory.limit_in_bytes") as f:
                    limit = int(f.read().strip())
                memory_limit_mb = limit // (1024 * 1024)
            except Exception:
                pass

            # Current process usage
            process_metrics = InfraTelemetry.get_process_metrics()
            cpu_utilization = min(100.0, process_metrics.cpu_percent)
            memory_utilization = min(
                100.0, (process_metrics.memory_rss_mb / memory_limit_mb) * 100
            )

            return DockerMetrics(
                cpu_limit_cores=float(cpu_limit_cores),
                memory_limit_mb=int(memory_limit_mb),
                cpu_utilization_percent=float(cpu_utilization),
                memory_utilization_percent=float(memory_utilization),
            )
        except Exception as e:
            print(f"[InfraTelemetry] docker metrics failed: {e}")
            return DockerMetrics(
                cpu_limit_cores=2.0,
                memory_limit_mb=1024,
                cpu_utilization_percent=0.0,
                memory_utilization_percent=0.0,
            )

    @staticmethod
    def get_snapshot(
        session: Session, redis_client: Optional[Any] = None
    ) -> InfrastructureSnapshot:
        """Get complete infrastructure snapshot."""
        return InfrastructureSnapshot(
            process=InfraTelemetry.get_process_metrics(),
            postgres=InfraTelemetry.get_postgres_metrics(session),
            redis=InfraTelemetry.get_redis_metrics(redis_client),
            docker=InfraTelemetry.get_docker_metrics(),
        )

    @staticmethod
    def to_dict(snapshot: InfrastructureSnapshot) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "process": {
                "cpu_percent": snapshot.process.cpu_percent,
                "memory_rss_mb": snapshot.process.memory_rss_mb,
                "memory_peak_mb": snapshot.process.memory_peak_mb,
            },
            "postgres": {
                "active_connections": snapshot.postgres.active_connections,
                "max_connections": snapshot.postgres.max_connections,
                "db_size_mb": snapshot.postgres.db_size_mb,
                "total_tables": snapshot.postgres.total_tables,
            },
            "redis": (
                {
                    "memory_used_mb": snapshot.redis.memory_used_mb,
                    "connected_clients": snapshot.redis.connected_clients,
                    "keyspace_hit_rate": snapshot.redis.keyspace_hit_rate,
                    "evicted_keys": snapshot.redis.evicted_keys,
                }
                if snapshot.redis
                else None
            ),
            "docker": {
                "cpu_limit_cores": snapshot.docker.cpu_limit_cores,
                "memory_limit_mb": snapshot.docker.memory_limit_mb,
                "cpu_utilization_percent": snapshot.docker.cpu_utilization_percent,
                "memory_utilization_percent": snapshot.docker.memory_utilization_percent,
            },
        }

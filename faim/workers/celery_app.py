"""
FAIM Workers - Celery Configuration

This module configures Celery for background task processing.
Tasks include:
- Document ingestion
- Graph reindexing
- Memory pruning/cleanup
- Usage aggregation
"""
import os
from celery import Celery

# Redis URL (same as rate limiting)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "faim_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["faim.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        "prune-old-memory": {
            "task": "faim.workers.tasks.prune_old_memory",
            "schedule": 3600.0,  # Every hour
        },
        "aggregate-usage": {
            "task": "faim.workers.tasks.aggregate_usage",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)

# Optional: Configure task queues
celery_app.conf.task_routes = {
    "faim.workers.tasks.ingest_document": {"queue": "ingestion"},
    "faim.workers.tasks.reindex_graph": {"queue": "indexing"},
    "faim.workers.tasks.prune_old_memory": {"queue": "maintenance"},
}

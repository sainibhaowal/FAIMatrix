"""FAIM-Native API Application.

FastAPI app with all routers and middleware.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Flexible imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# =============================================================================
# Create FastAPI App
# =============================================================================


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="FAIM-Native API",
        description="FAIM memory graph API with SSE event stream",
        version="0.10.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ==========================================================================
    # Stage-9: Setup JSON logging
    # ==========================================================================
    try:
        import os

        from runtime.logging import setup_logging

        log_level = os.getenv("FAIM_LOG_LEVEL", "INFO")
        # Use JSON format in production (when not DEBUG)
        json_format = log_level.upper() != "DEBUG"
        setup_logging(level=log_level, json_format=json_format)
        logger.info(f"FAIM logging configured: level={log_level}, json={json_format}")
    except Exception as e:
        logger.warning(f"Failed to setup JSON logging (using default): {e}")

    # ==========================================================================
    # Middleware (order matters: first added = last executed)
    # ==========================================================================

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID
    from api.middleware.request_id import RequestIdMiddleware

    app.add_middleware(RequestIdMiddleware)

    # Stage-9: Rate Limiting
    try:
        import json

        # Configure rate limiter from env
        import os

        from api.middleware.ratelimit import RateLimitMiddleware, get_rate_limiter

        rate_limits_json = os.getenv("FAIM_RATE_LIMITS_JSON", "{}")
        try:
            rate_limits = json.loads(rate_limits_json)
            if rate_limits:
                get_rate_limiter().set_limits(rate_limits)
                logger.info(f"Rate limits configured: {rate_limits}")
        except json.JSONDecodeError:
            pass

        app.add_middleware(RateLimitMiddleware)
        logger.info("RateLimitMiddleware registered")
    except Exception as e:
        logger.warning(f"Failed to register RateLimitMiddleware: {e}")

    # Tenant Auth
    from api.middleware.auth import TenantAuthMiddleware

    app.add_middleware(TenantAuthMiddleware)

    # ==========================================================================
    # Routers
    # ==========================================================================

    from api.routers import (
        admin_router,
        events_router,
        evolve_router,
        health_router,
        ingest_router,
        metrics_router,
        node_router,
        query_router,
    )

    # Health routes (no prefix)
    app.include_router(health_router)

    # API v1 routes
    app.include_router(events_router)
    app.include_router(ingest_router)
    app.include_router(query_router)
    app.include_router(node_router)
    app.include_router(evolve_router)
    app.include_router(metrics_router)
    app.include_router(admin_router)

    # ==========================================================================
    # Startup/Shutdown Events
    # ==========================================================================

    @app.on_event("startup")
    async def startup_event():
        logger.info("FAIM-Native API starting up...")

        # Stage-10: Auto-migrate if enabled (default=false)
        import os

        from store.pg.migrate import run_up

        if os.getenv("FAIM_AUTO_MIGRATE", "false").lower() == "true":
            logger.info("FAIM_AUTO_MIGRATE=true. Running migrations...")
            try:
                run_up()
            except Exception as e:
                logger.critical(f"Auto-migration failed: {e}")
                # We don't exit here to allow /ready to report the failure

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("FAIM-Native API shutting down...")

    return app


# Create app instance
app = create_app()


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=True,
    )

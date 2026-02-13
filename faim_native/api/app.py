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
class SecureLogFilter(logging.Filter):
    """Filter to redact sensitive information from logs."""

    SENSITIVE_PATTERNS = [
        "X-Api-Key",
        "Authorization",
        "accessToken",
        "NEXTAUTH_SECRET",
        "REDIS_PASSWORD",
        "POSTGRES_PASSWORD",
        "QDRANT_API_KEY",
        "X-Tenant-Id",
        "tenant_id",
    ]

    def filter(self, record):
        msg = str(record.msg)
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in msg:
                # Simple redaction
                record.msg = f"[REDACTED SENSITIVE {pattern}]"
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
for handler in logging.root.handlers:
    handler.addFilter(SecureLogFilter())

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

    # JWT Auth (Stage-12: NextAuth token verification)
    # Runs BEFORE TenantAuth - if Bearer token present, uses JWT claims
    # Otherwise falls through to API key auth
    try:
        from api.middleware.jwt import JWTAuthMiddleware

        app.add_middleware(JWTAuthMiddleware)
        logger.info("JWTAuthMiddleware registered")
    except Exception as e:
        logger.warning(f"Failed to register JWTAuthMiddleware: {e}")

    # Security Headers
    from api.middleware.security import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("SecurityHeadersMiddleware registered")

    # ==========================================================================
    # Routers
    # ==========================================================================

    from api.routers import (
        admin_router,
        api_keys_router,
        auth_router,
        events_router,
        evolve_router,
        health_router,
        ingest_router,
        metrics_router,
        node_router,
        query_router,
        storage_router,
    )

    # Health routes (no prefix - for external status checks)
    app.include_router(health_router)

    # API v1 routes (consistent /api/v1 prefix)
    prefix = "/api/v1"
    app.include_router(auth_router, prefix=prefix)
    app.include_router(events_router, prefix=prefix)
    app.include_router(ingest_router, prefix=prefix)
    app.include_router(query_router, prefix=prefix)
    app.include_router(node_router, prefix=prefix)
    app.include_router(evolve_router, prefix=prefix)
    app.include_router(metrics_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)
    app.include_router(api_keys_router, prefix=prefix)
    app.include_router(storage_router, prefix=prefix)

    # ==========================================================================
    # Startup/Shutdown Events
    # ==========================================================================

    @app.on_event("startup")
    async def startup_event():
        logger.info("FAIM-Native API starting up...")

        # Phase A: feature-flag guardrails + contract freeze checks
        try:
            from api.contracts.storage_contract import validate_storage_router_contract
            from runtime.feature_flags import get_feature_flags, validate_feature_flags

            flags = get_feature_flags()
            errors, warnings = validate_feature_flags(flags)
            for warning in warnings:
                logger.warning(f"Feature flag warning: {warning}")

            if errors:
                for err in errors:
                    logger.critical(f"Feature flag validation error: {err}")
                raise RuntimeError("Feature flag validation failed")

            contract = validate_storage_router_contract(storage_router.routes)
            if not contract.ok:
                for err in contract.errors:
                    logger.critical(f"Storage contract violation: {err}")
                if flags.storage_contract_strict:
                    raise RuntimeError("Storage contract validation failed")
            else:
                logger.info(f"Storage contract validated (v={contract.version})")
        except Exception as e:
            logger.critical(f"Startup contract/flag validation failed: {e}")
            raise

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

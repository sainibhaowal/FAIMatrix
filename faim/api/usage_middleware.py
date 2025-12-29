"""
FAIM Usage Tracking Middleware

Logs every API request to the usage_events table for billing and metrics.
Uses async background insert to avoid blocking requests.
"""
import os
import time
import logging
import asyncio
from typing import Optional, Callable
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Configuration
USAGE_TRACKING_ENABLED = os.getenv("USAGE_TRACKING_ENABLED", "true").lower() in ("1", "true", "yes")
EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs API usage to the database.
    
    Records:
    - Endpoint and method
    - Response status and latency
    - User/API key identity
    - Request/response sizes
    """
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled and USAGE_TRACKING_ENABLED
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        # Skip excluded paths
        path = request.url.path
        if path in EXCLUDED_PATHS or path.startswith("/api/v1/stream"):
            return await call_next(request)
        
        start_time = time.time()
        
        # Get request size
        content_length = request.headers.get("content-length")
        bytes_in = int(content_length) if content_length else 0
        
        # Call the actual endpoint
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Get response size
        bytes_out = 0
        if hasattr(response, "headers"):
            resp_length = response.headers.get("content-length")
            if resp_length:
                bytes_out = int(resp_length)
        
        # Extract identity from request state
        user_id = getattr(request.state, "user_id", None)
        user_sub = getattr(request.state, "user_sub", None)
        api_key_id = getattr(request.state, "api_key_id", None)
        project_id = getattr(request.state, "project_id", None)
        graph_id = request.path_params.get("graph_id")
        
        # Log usage asynchronously (don't block response)
        asyncio.create_task(
            self._log_usage(
                endpoint=path,
                method=request.method,
                status_code=response.status_code,
                latency_ms=latency_ms,
                bytes_in=bytes_in,
                bytes_out=bytes_out,
                user_id=user_id,
                user_sub=user_sub,
                api_key_id=api_key_id,
                project_id=project_id,
                graph_id=graph_id,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from headers or connection."""
        # Check X-Forwarded-For first (behind proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to connection IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _log_usage(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: int,
        bytes_in: int,
        bytes_out: int,
        user_id: Optional[str] = None,
        user_sub: Optional[str] = None,
        api_key_id: Optional[str] = None,
        project_id: Optional[str] = None,
        graph_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Insert usage event into database."""
        try:
            from faim.db import SessionLocal
            from faim.models_sql import UsageEvent, User
            
            db = SessionLocal()
            try:
                # Resolve user_id from keycloak_sub if needed
                actor_user_id = None
                if user_id:
                    try:
                        actor_user_id = UUID(user_id)
                    except ValueError:
                        pass
                elif user_sub:
                    # Look up user by keycloak_sub
                    user = db.query(User).filter(User.keycloak_sub == user_sub).first()
                    if user:
                        actor_user_id = user.id
                
                # Resolve IDs
                actor_key_id = UUID(api_key_id) if api_key_id else None
                proj_id = UUID(project_id) if project_id else None
                
                # Create usage event
                event = UsageEvent(
                    project_id=proj_id,
                    graph_id=graph_id,
                    actor_user_id=actor_user_id,
                    actor_key_id=actor_key_id,
                    endpoint=endpoint,
                    method=method,
                    bytes_in=bytes_in,
                    bytes_out=bytes_out,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    ip_address=ip_address,
                    user_agent=user_agent[:500] if user_agent else None,
                )
                db.add(event)
                db.commit()
            finally:
                db.close()
                
        except Exception as e:
            # Never fail the request due to logging errors
            logger.warning(f"Failed to log usage event: {e}")


def get_usage_stats(project_id: str, days: int = 30) -> dict:
    """
    Get aggregated usage statistics for a project.
    
    Returns:
        Dict with total requests, bytes, latency stats
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        from faim.db import SessionLocal
        from faim.models_sql import UsageEvent
        
        db = SessionLocal()
        try:
            since = datetime.utcnow() - timedelta(days=days)
            proj_uuid = UUID(project_id)
            
            stats = db.query(
                func.count(UsageEvent.id).label("total_requests"),
                func.sum(UsageEvent.bytes_in).label("total_bytes_in"),
                func.sum(UsageEvent.bytes_out).label("total_bytes_out"),
                func.avg(UsageEvent.latency_ms).label("avg_latency_ms"),
            ).filter(
                UsageEvent.project_id == proj_uuid,
                UsageEvent.ts >= since,
            ).first()
            
            return {
                "project_id": project_id,
                "period_days": days,
                "total_requests": stats.total_requests or 0,
                "total_bytes_in": stats.total_bytes_in or 0,
                "total_bytes_out": stats.total_bytes_out or 0,
                "avg_latency_ms": round(stats.avg_latency_ms or 0, 2),
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        return {}

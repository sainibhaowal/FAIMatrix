"""
FAIM Real-Time Token Tracking

Tracks token usage on every memory operation:
- /store: counts tokens stored
- /retrieve: counts tokens retrieved
- Updates usage in database
- Enforces plan limits
- Broadcasts usage updates via SSE
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Set
from collections import defaultdict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# =============================================================================
# SSE CONNECTION MANAGER (for real-time updates)
# =============================================================================

class UsageSSEManager:
    """
    Manages Server-Sent Events connections for real-time usage updates.
    Clients connect via /api/v1/usage/stream
    """
    
    def __init__(self):
        # project_id -> set of asyncio.Queue objects
        self._connections: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()
    
    async def connect(self, project_id: str) -> asyncio.Queue:
        """Register a new SSE connection for a project."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._connections[project_id].add(queue)
        logger.info(f"[SSE] Client connected for project {project_id}")
        return queue
    
    async def disconnect(self, project_id: str, queue: asyncio.Queue):
        """Remove an SSE connection."""
        async with self._lock:
            self._connections[project_id].discard(queue)
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info(f"[SSE] Client disconnected from project {project_id}")
    
    async def broadcast(self, project_id: str, data: Dict[str, Any]):
        """Send usage update to all connected clients for a project."""
        async with self._lock:
            queues = list(self._connections.get(project_id, []))
        
        if not queues:
            return
        
        message = json.dumps(data)
        for queue in queues:
            try:
                await queue.put(message)
            except Exception as e:
                logger.warning(f"[SSE] Failed to broadcast: {e}")


# Global SSE manager instance
usage_sse_manager = UsageSSEManager()


# =============================================================================
# TOKEN COUNTING
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.
    Simple approximation: ~4 characters per token for English text.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def count_request_tokens(body: bytes) -> int:
    """Count tokens in request body (for /store)."""
    try:
        data = json.loads(body)
        total = 0
        
        # Count content field
        if "content" in data:
            total += estimate_tokens(str(data["content"]))
        
        # Count metadata
        if "metadata" in data:
            total += estimate_tokens(json.dumps(data["metadata"]))
        
        return total
    except Exception:
        # Fallback: estimate from raw bytes
        return max(1, len(body) // 4)


def count_response_tokens(body: bytes) -> int:
    """Count tokens in response body (for /retrieve)."""
    try:
        data = json.loads(body)
        total = 0
        
        # Handle list of results
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if "content" in item:
                        total += estimate_tokens(str(item["content"]))
                    if "metadata" in item:
                        total += estimate_tokens(json.dumps(item["metadata"]))
        elif isinstance(data, dict):
            if "content" in data:
                total += estimate_tokens(str(data["content"]))
            if "results" in data:
                total += count_response_tokens(json.dumps(data["results"]).encode())
        
        return total
    except Exception:
        return max(1, len(body) // 4)


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def get_project_for_graph(graph_id: str) -> Optional[str]:
    """Get project_id for a graph from GraphOwnership table."""
    try:
        from faim.db import SessionLocal
        from faim.models_sql import GraphOwnership
        
        db = SessionLocal()
        try:
            ownership = db.query(GraphOwnership).filter(
                GraphOwnership.graph_id == graph_id
            ).first()
            return str(ownership.project_id) if ownership else None
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[TokenTracker] Failed to get project for graph: {e}")
        return None


def update_token_usage(project_id: str, tokens: int) -> Dict[str, Any]:
    """
    Update token usage for a project.
    Returns updated usage stats.
    """
    try:
        from faim.db import SessionLocal
        from faim.models_sql import Project
        from faim.api.plan_limits import get_plan_limits
        
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {}
            
            # Get current usage
            plan_limits = project.plan_limits or {}
            tokens_used = plan_limits.get("tokens_used", 0)
            
            # Update usage
            tokens_used += tokens
            plan_limits["tokens_used"] = tokens_used
            plan_limits["last_updated"] = datetime.utcnow().isoformat()
            
            project.plan_limits = plan_limits
            db.commit()
            
            # Get plan limits
            limits = get_plan_limits(project.plan)
            
            return {
                "project_id": project_id,
                "plan": project.plan,
                "tokens_used": tokens_used,
                "tokens_max": limits["tokens"],
                "tokens_added": tokens,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"[TokenTracker] Failed to update usage: {e}")
        return {}


def check_token_limit(project_id: str, tokens_to_add: int = 0) -> tuple[bool, str]:
    """
    Check if project has capacity for more tokens.
    Returns (allowed, message)
    """
    try:
        from faim.db import SessionLocal
        from faim.models_sql import Project
        from faim.api.plan_limits import get_plan_limits
        
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return True, "OK"
            
            limits = get_plan_limits(project.plan)
            max_tokens = limits["tokens"]
            
            plan_limits = project.plan_limits or {}
            current_tokens = plan_limits.get("tokens_used", 0)
            
            if current_tokens + tokens_to_add > max_tokens:
                return False, f"Token limit exceeded ({current_tokens:,}/{max_tokens:,}). Upgrade your plan at /billing"
            
            return True, "OK"
            
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"[TokenTracker] Limit check failed: {e}")
        return True, "OK"  # Fail open


# =============================================================================
# TOKEN TRACKING MIDDLEWARE
# =============================================================================

class TokenTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks token usage on /store and /retrieve endpoints.
    - Counts tokens in requests/responses
    - Updates database
    - Enforces limits
    - Broadcasts updates via SSE
    """
    
    # Endpoints to track
    TRACK_ENDPOINTS = {
        "/api/v1/store": "store",
        "/api/v1/retrieve": "retrieve",
        "/store": "store",
        "/retrieve": "retrieve",
    }
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Only track specific endpoints
        operation = None
        for endpoint, op in self.TRACK_ENDPOINTS.items():
            if path.endswith(endpoint) or endpoint in path:
                operation = op
                break
        
        if not operation:
            return await call_next(request)
        
        # Get graph_id from query params
        graph_id = request.query_params.get("graph_id")
        if not graph_id:
            return await call_next(request)
        
        # Get project for this graph
        project_id = get_project_for_graph(graph_id)
        if not project_id:
            # If no project ownership, allow request (dev mode)
            return await call_next(request)
        
        tokens_to_track = 0
        
        # For store operations, count tokens BEFORE the request
        if operation == "store" and request.method == "POST":
            body = await request.body()
            tokens_to_track = count_request_tokens(body)
            
            # Check limit BEFORE processing
            allowed, message = check_token_limit(project_id, tokens_to_track)
            if not allowed:
                raise HTTPException(status_code=402, detail=message)
            
            # Reconstruct request with body (since we consumed it)
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        
        # Process the request
        response = await call_next(request)
        
        # For retrieve operations, count tokens in response
        if operation == "retrieve" and response.status_code == 200:
            # We need to read the response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            tokens_to_track = count_response_tokens(response_body)
            
            # Rebuild response
            from starlette.responses import Response as StarletteResponse
            response = StarletteResponse(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        # Update usage if we tracked tokens
        if tokens_to_track > 0:
            usage = update_token_usage(project_id, tokens_to_track)
            
            # Broadcast to SSE clients
            if usage:
                asyncio.create_task(
                    usage_sse_manager.broadcast(project_id, {
                        "type": "usage_update",
                        "data": usage
                    })
                )
                logger.info(f"[TokenTracker] {operation}: {tokens_to_track} tokens for project {project_id}")
        
        return response

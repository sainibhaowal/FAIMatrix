"""
FAIM Real-Time Usage SSE Endpoints

Provides Server-Sent Events for real-time usage updates:
- /api/v1/usage/stream - SSE stream for usage updates
- /api/v1/usage/current - Get current usage stats
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from faim.api.plan_limits import PLAN_LIMITS, get_plan_limits
from faim.api.token_tracker import usage_sse_manager

router = APIRouter(prefix="/usage", tags=["Usage"])


def get_project_usage(project_id: str) -> dict:
    """Get current usage stats for a project."""
    try:
        from faim.db import SessionLocal
        from faim.models_sql import Project
        
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"error": "Project not found"}
            
            limits = get_plan_limits(project.plan)
            plan_data = project.plan_limits or {}
            
            return {
                "project_id": project_id,
                "plan": project.plan,
                "tokens_used": plan_data.get("tokens_used", 0),
                "tokens_max": limits["tokens"],
                "storage_mb_max": limits["storage_mb"],
                "price_monthly": limits["price_monthly"],
                "last_updated": plan_data.get("last_updated"),
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


@router.get("/current")
async def get_current_usage(project_id: str = Query(...)):
    """
    Get current usage statistics for a project.
    """
    usage = get_project_usage(project_id)
    if "error" in usage:
        raise HTTPException(status_code=404, detail=usage["error"])
    return usage


@router.get("/stream")
async def usage_stream(request: Request, project_id: str = Query(...)):
    """
    Server-Sent Events stream for real-time usage updates.
    
    Connect to receive usage updates whenever tokens are used:
    - Each event includes tokens_used, tokens_max, tokens_added
    - Updates sent immediately after each /store or /retrieve call
    
    Example client:
    ```javascript
    const eventSource = new EventSource('/api/v1/usage/stream?project_id=xxx');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUsageBar(data.tokens_used, data.tokens_max);
    };
    ```
    """
    
    async def event_generator():
        # Connect to SSE manager
        queue = await usage_sse_manager.connect(project_id)
        
        try:
            # Send initial usage data
            initial = get_project_usage(project_id)
            yield f"data: {json.dumps({'type': 'initial', 'data': initial})}\n\n"
            
            # Send heartbeat and updates
            while True:
                try:
                    # Wait for message with timeout (heartbeat every 30s)
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield ": heartbeat\n\n"
                except asyncio.CancelledError:
                    break
                
        finally:
            await usage_sse_manager.disconnect(project_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )


@router.get("/plans")
async def get_available_plans():
    """
    Get available plan tiers and their limits.
    """
    plans = []
    for plan_id, limits in PLAN_LIMITS.items():
        plans.append({
            "id": plan_id,
            "tokens": limits["tokens"],
            "storage_mb": limits["storage_mb"],
            "price_monthly": limits["price_monthly"],
            "features": limits["features"],
        })
    return {"plans": plans}

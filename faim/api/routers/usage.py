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

from faim.api.services.usage_service import PLAN_LIMITS, get_plan_limits, usage_sse_manager

router = APIRouter(prefix="/usage", tags=["Usage"])


def get_user_usage(user_id: str) -> dict:
    """Get current usage stats for a user."""
    try:
        from faim.config.database import SessionLocal
        from faim.config.models import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}

            limits = get_plan_limits(user.plan)

            return {
                "user_id": str(user.id),
                "plan": user.plan,
                # Memories
                "memories_count": user.memories_count or 0,
                "memories_max": user.memories_max or limits["memories"],
                # Storage
                "storage_used_bytes": user.storage_used_bytes or 0,
                "storage_max_bytes": user.storage_max_bytes or limits["storage_bytes"],
                # API Calls
                "api_calls_count": user.api_calls_count or 0,
                "api_calls_max": user.api_calls_max or limits["api_calls_month"],
                # Pricing
                "price_monthly": limits["price_monthly"],
                "last_updated": getattr(user, "last_usage_update", None),
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


@router.get("/current")
async def get_current_usage(user_id: str = Query(...)):
    """
    Get current usage statistics.
    """
    usage = get_user_usage(user_id)
    if "error" in usage:
        raise HTTPException(status_code=404, detail=usage["error"])
    return usage


@router.get("/summary")
async def get_usage_summary(user_id: str = Query(...)):
    """Get summarized usage stats for dashboard."""
    from datetime import datetime

    from sqlalchemy import func

    from faim.config.database import SessionLocal
    from faim.config.models import Document, UsageEvent

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        month_start = datetime(now.year, now.month, 1)

        # API Calls
        calls_today = (
            db.query(func.count(UsageEvent.id))
            .filter(UsageEvent.user_id == user_id, UsageEvent.ts >= today_start)
            .scalar()
            or 0
        )

        calls_month = (
            db.query(func.count(UsageEvent.id))
            .filter(UsageEvent.user_id == user_id, UsageEvent.ts >= month_start)
            .scalar()
            or 0
        )

        # Documents & Storage
        doc_stats = (
            db.query(func.count(Document.id), func.sum(Document.file_size_bytes))
            .filter(Document.user_id == user_id)
            .first()
        )

        doc_count = doc_stats[0] or 0
        # Check if sum returns None (if no docs)
        storage_bytes = doc_stats[1] or 0

        return {
            "api_calls_today": calls_today,
            "api_calls_month": calls_month,
            "storage_bytes": storage_bytes,
            "documents_count": doc_count,
        }
    finally:
        db.close()


@router.get("/stream")
async def usage_stream(request: Request, user_id: str = Query(...)):
    """
    Server-Sent Events stream for real-time usage updates.

    Connect to receive usage updates whenever tokens are used:
    - Each event includes tokens_used, tokens_max, tokens_added
    - Updates sent immediately after each /store or /retrieve call

    Example client:
    ```javascript
    const eventSource = new EventSource('/api/v1/usage/stream?user_id=xxx');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUsageBar(data.tokens_used, data.tokens_max);
    };
    ```
    """

    async def event_generator():
        # Connect to SSE manager
        queue = await usage_sse_manager.connect(user_id)

        try:
            # Send initial usage data
            initial = get_user_usage(user_id)
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
            await usage_sse_manager.disconnect(user_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@router.get("/plans")
async def get_available_plans():
    """
    Get available plan tiers and their limits.
    """
    plans = []
    for plan_id, limits in PLAN_LIMITS.items():
        plans.append(
            {
                "id": plan_id,
                "tokens": limits["tokens"],
                "storage_mb": limits["storage_mb"],
                "price_monthly": limits["price_monthly"],
                "features": limits["features"],
            }
        )
    return {"plans": plans}


# =============================================================================
# ACTIVITY ENDPOINTS (for dashboard)
# =============================================================================


@router.get("/activity/recent")
async def get_recent_activity(limit: int = Query(10, ge=1, le=50)):
    """
    Get recent activity items for dashboard.
    """
    from datetime import datetime

    from faim.config.database import SessionLocal
    from faim.config.models import UsageEvent

    db = SessionLocal()
    try:
        events = db.query(UsageEvent).order_by(UsageEvent.ts.desc()).limit(limit).all()
        return [
            {
                "id": str(e.id),
                "type": e.event_type or "chat",
                "title": f"{e.event_type or 'Activity'}: {e.input_tokens or 0} tokens",
                "timestamp": e.ts.isoformat() if e.ts else datetime.utcnow().isoformat(),
                "metadata": {
                    "tokens": (e.input_tokens or 0) + (e.output_tokens or 0),
                },
            }
            for e in events
        ]
    except Exception:
        # Return empty list if no activity table exists
        return []
    finally:
        db.close()


@router.get("/activity/daily")
async def get_daily_activity(days: int = Query(7, ge=1, le=30)):
    """
    Get daily activity counts for chart.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import Date, cast, func

    from faim.config.database import SessionLocal
    from faim.config.models import UsageEvent

    db = SessionLocal()
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Group by date
        results = (
            db.query(cast(UsageEvent.ts, Date).label("date"), func.count(UsageEvent.id).label("count"))
            .filter(UsageEvent.ts >= start)
            .group_by(cast(UsageEvent.ts, Date))
            .order_by(cast(UsageEvent.ts, Date))
            .all()
        )

        # Build result with all dates
        date_counts = {str(r.date): r.count for r in results}
        output = []
        for i in range(days):
            d = (start + timedelta(days=i)).date()
            output.append({"date": str(d), "count": date_counts.get(str(d), 0)})

        return output
    except Exception:
        # Return empty list if query fails
        return []
    finally:
        db.close()

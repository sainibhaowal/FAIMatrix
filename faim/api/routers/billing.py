# =============================================================================
# FAIM Billing Router - User-Level Billing
# =============================================================================
# Returns real-time usage data from User table.
# Metrics: Memories, Storage, API Calls
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from faim.api.middleware.auth_middleware import get_current_user_oidc
from faim.api.services.usage_service import PLAN_LIMITS, upgrade_user_plan
from faim.config.database import get_db
from faim.config.models import User

router = APIRouter(prefix="/billing", tags=["Billing"])


# =============================================================================
# Response Models
# =============================================================================


class BillingStatus(BaseModel):
    user_id: str
    plan: str
    # Memories
    memories_count: int
    memories_max: int
    # Storage
    storage_used_bytes: int
    storage_max_bytes: int
    # API Calls
    api_calls_count: int
    api_calls_max: int
    # Status
    status: str


class UpgradePlanRequest(BaseModel):
    plan: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=BillingStatus)
def get_billing_status(
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Get current user's billing status with real usage data.

    Returns memories_count, storage_used, and api_calls_count.
    """
    plan = current_user.plan or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    return BillingStatus(
        user_id=str(current_user.id),
        plan=plan,
        memories_count=current_user.memories_count or 0,
        memories_max=limits["memories"],
        storage_used_bytes=current_user.storage_used_bytes or 0,
        storage_max_bytes=limits["storage_bytes"],
        api_calls_count=current_user.api_calls_count or 0,
        api_calls_max=limits["api_calls_month"],
        status="active",
    )


@router.post("/upgrade")
def upgrade_plan(
    request: UpgradePlanRequest,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Upgrade user's plan.

    In production, this would redirect to Stripe checkout.
    For now, just updates the plan directly.
    """
    valid_plans = ["free", "starter", "custom"]
    if request.plan not in valid_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose from: {valid_plans}")

    return upgrade_user_plan(db, str(current_user.id), request.plan)


@router.post("/reset-usage")
def reset_usage(
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Reset usage counters (for testing/admin use).
    """
    current_user.memories_count = 0
    current_user.storage_used_bytes = 0
    current_user.api_calls_count = 0
    db.commit()

    return {
        "status": "reset",
        "memories_count": 0,
        "storage_used_bytes": 0,
        "api_calls_count": 0,
    }


@router.get("/plans")
def get_plans():
    """Get available billing plans and their limits."""
    plans = []
    for plan_id, limits in PLAN_LIMITS.items():
        plans.append(
            {
                "id": plan_id,
                "memories_max": limits["memories"],
                "storage_max_bytes": limits["storage_bytes"],
                "api_calls_max": limits["api_calls_month"],
            }
        )
    return {"plans": plans}

"""
FAIM Plan Limits - Token-Based Billing

Simple pricing model:
- Free: 1M tokens (on signup)
- Starter: $9/mo - 3M tokens
- Pro: $15/mo - 10M tokens (or custom)

Each user gets ONE permanent Universe graph.
Billing is based on token storage, not number of graphs.
"""
import os
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException


# =============================================================================
# PLAN DEFINITIONS - Simple Token-Based Billing
# =============================================================================

PLAN_LIMITS = {
    "free": {
        "tokens": 1_000_000,       # 1M tokens
        "storage_mb": 100,
        "price_monthly": 0,
        "stripe_price_id": None,
        "features": ["basic_store", "basic_retrieve", "api_key"],
    },
    "starter": {
        "tokens": 3_000_000,       # 3M tokens
        "storage_mb": 500,
        "price_monthly": 9,
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", "price_starter_monthly"),
        "features": ["basic_store", "basic_retrieve", "api_key", "priority_support"],
    },
    "pro": {
        "tokens": 10_000_000,      # 10M tokens
        "storage_mb": 2000,
        "price_monthly": 15,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_pro_monthly"),
        "features": ["basic_store", "basic_retrieve", "api_key", "priority_support", "advanced_search", "export"],
    },
}

def get_plan_limits(plan: str) -> Dict:
    """Get limits for a plan tier."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def get_plan_by_stripe_price(price_id: str) -> Optional[str]:
    """Get plan name by Stripe price ID."""
    for plan_name, plan_data in PLAN_LIMITS.items():
        if plan_data.get("stripe_price_id") == price_id:
            return plan_name
    return None


# =============================================================================
# TOKEN-BASED LIMIT CHECKING
# =============================================================================

def check_token_limit(user_id: str, additional_tokens: int = 0) -> Tuple[bool, str]:
    """
    Check if user has token capacity remaining.
    Returns (allowed, message)
    """
    try:
        from faim.db import SessionLocal
        from faim.models_sql import User, Project, OrgMember
        
        db = SessionLocal()
        try:
            # Get user's project (each user has one main project)
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return True, "OK"  # Fail open for unknown users in dev
            
            # Get user's project through org membership
            membership = db.query(OrgMember).filter(OrgMember.user_id == user_id).first()
            if not membership:
                return True, "OK"
            
            project = db.query(Project).filter(Project.org_id == membership.org_id).first()
            if not project:
                return True, "OK"
            
            limits = get_plan_limits(project.plan)
            max_tokens = limits["tokens"]
            
            # Get current token usage (stored in project.plan_limits as JSON)
            current_usage = project.plan_limits or {}
            current_tokens = current_usage.get("tokens_used", 0)
            
            if current_tokens + additional_tokens > max_tokens:
                return False, f"Token limit reached ({max_tokens:,} for {project.plan} plan). Upgrade at /settings/billing"
            
            return True, "OK"
            
        finally:
            db.close()
            
    except Exception as e:
        return True, f"OK (check failed: {e})"


def check_storage_limit(user_id: str, new_bytes: int = 0) -> Tuple[bool, str]:
    """
    Check if user has storage capacity for new_bytes.
    Returns (allowed, message)
    """
    try:
        from faim.db import SessionLocal
        from faim.models_sql import User, Project, OrgMember, Document
        from sqlalchemy import func
        
        db = SessionLocal()
        try:
            # Get user's project
            membership = db.query(OrgMember).filter(OrgMember.user_id == user_id).first()
            if not membership:
                return True, "OK"
            
            project = db.query(Project).filter(Project.org_id == membership.org_id).first()
            if not project:
                return True, "OK"
            
            limits = get_plan_limits(project.plan)
            max_mb = limits["storage_mb"]
            
            # Calculate current storage
            current_bytes = db.query(func.sum(Document.file_size)).filter(
                Document.project_id == project.id,
                Document.status != "deleted"
            ).scalar() or 0
            
            total_mb = (current_bytes + new_bytes) / (1024 * 1024)
            
            if total_mb > max_mb:
                return False, f"Storage limit exceeded ({max_mb}MB for {project.plan} plan)"
            
            return True, "OK"
            
        finally:
            db.close()
            
    except Exception as e:
        return True, f"OK (check failed: {e})"


# =============================================================================
# PLAN UPGRADE FUNCTIONS
# =============================================================================

def upgrade_user_plan(user_id: str, new_plan: str) -> Tuple[bool, str]:
    """
    Upgrade a user's plan. Called after successful Stripe payment.
    Returns (success, message)
    """
    try:
        from faim.db import SessionLocal
        from faim.models_sql import User, Project, OrgMember
        
        if new_plan not in PLAN_LIMITS:
            return False, f"Invalid plan: {new_plan}"
        
        db = SessionLocal()
        try:
            # Find user's project
            membership = db.query(OrgMember).filter(OrgMember.user_id == user_id).first()
            if not membership:
                return False, "User has no organization"
            
            project = db.query(Project).filter(Project.org_id == membership.org_id).first()
            if not project:
                return False, "User has no project"
            
            # Update plan
            old_plan = project.plan
            project.plan = new_plan
            project.subscription_status = "active"
            
            # Update plan limits in JSON field
            limits = get_plan_limits(new_plan)
            project.plan_limits = {
                "tokens_max": limits["tokens"],
                "storage_mb_max": limits["storage_mb"],
                "tokens_used": (project.plan_limits or {}).get("tokens_used", 0),
            }
            
            db.commit()
            
            return True, f"Plan upgraded from {old_plan} to {new_plan}"
            
        finally:
            db.close()
            
    except Exception as e:
        return False, f"Upgrade failed: {e}"


def get_user_usage(user_id: str) -> Dict:
    """
    Get user's current usage stats.
    Returns dict with tokens_used, tokens_max, storage_used_mb, storage_max_mb
    """
    try:
        from faim.db import SessionLocal
        from faim.models_sql import Project, OrgMember, Document
        from sqlalchemy import func
        
        db = SessionLocal()
        try:
            membership = db.query(OrgMember).filter(OrgMember.user_id == user_id).first()
            if not membership:
                return {"error": "No organization found"}
            
            project = db.query(Project).filter(Project.org_id == membership.org_id).first()
            if not project:
                return {"error": "No project found"}
            
            limits = get_plan_limits(project.plan)
            plan_data = project.plan_limits or {}
            
            # Get storage used
            storage_bytes = db.query(func.sum(Document.file_size)).filter(
                Document.project_id == project.id,
                Document.status != "deleted"
            ).scalar() or 0
            
            return {
                "plan": project.plan,
                "tokens_used": plan_data.get("tokens_used", 0),
                "tokens_max": limits["tokens"],
                "storage_used_mb": round(storage_bytes / (1024 * 1024), 2),
                "storage_max_mb": limits["storage_mb"],
                "price_monthly": limits["price_monthly"],
            }
            
        finally:
            db.close()
            
    except Exception as e:
        return {"error": str(e)}


def enforce_token_limit(user_id: str, tokens: int = 0):
    """
    FastAPI dependency to enforce token limits.
    Raises HTTPException if limit exceeded.
    """
    allowed, msg = check_token_limit(user_id, tokens)
    if not allowed:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "token_limit_exceeded",
                "message": msg,
                "upgrade_url": "/settings/billing"
            }
        )


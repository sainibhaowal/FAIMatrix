"""
FAIM Stripe Billing Integration

Handles:
- Checkout session creation
- Subscription management
- Webhook events (payment success/failure)
- Plan upgrades/downgrades
"""
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

# Stripe configuration from environment
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "price_pro_monthly")
STRIPE_PRICE_ID_ENTERPRISE = os.getenv("STRIPE_PRICE_ID_ENTERPRISE", "price_enterprise_monthly")

# Initialize Stripe (lazy)
_stripe = None

def get_stripe():
    """Get Stripe module, initializing if needed."""
    global _stripe
    if _stripe is None:
        if not STRIPE_SECRET_KEY:
            return None
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            _stripe = stripe
        except ImportError:
            logger.warning("Stripe library not installed. Run: pip install stripe")
            return None
    return _stripe


# --- Request/Response Models ---

class CreateCheckoutRequest(BaseModel):
    project_id: str
    plan: str  # "pro" or "enterprise"
    success_url: str
    cancel_url: str

class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str

class SubscriptionStatus(BaseModel):
    project_id: str
    plan: str
    status: str
    current_period_end: Optional[str]
    cancel_at_period_end: bool


# --- Endpoints ---

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(payload: CreateCheckoutRequest):
    """
    Create a Stripe Checkout session for plan upgrade.
    Requires Stripe to be configured.
    """
    from faim.api.plan_limits import PLAN_LIMITS
    
    # Validate plan
    if payload.plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {payload.plan}")
    
    plan_config = PLAN_LIMITS[payload.plan]
    
    if not plan_config.get("stripe_price_id") or plan_config.get("price_monthly", 0) == 0:
        raise HTTPException(status_code=400, detail=f"Plan '{payload.plan}' is free (no checkout needed)")
    
    stripe = get_stripe()
    
    # PRODUCTION: Require Stripe to be configured
    if not stripe:
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Please set STRIPE_SECRET_KEY environment variable."
        )
    
    # Get price ID from plan config
    price_id = plan_config.get("stripe_price_id")
    
    try:
        # Get or create Stripe customer
        customer_id = await _get_or_create_customer(payload.project_id)
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=payload.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=payload.cancel_url,
            metadata={"project_id": payload.project_id, "plan": payload.plan},
        )
        
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id
        )
        
    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/subscription/{project_id}", response_model=SubscriptionStatus)
async def get_subscription_status(project_id: str):
    """
    Get current subscription status for a project.
    """
    try:
        from faim.db import SessionLocal
        from faim.models_sql import Project
        
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            return SubscriptionStatus(
                project_id=project_id,
                plan=project.plan,
                status=project.subscription_status or "active",
                current_period_end=None,  # Would be fetched from Stripe
                cancel_at_period_end=False
            )
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription status")


@router.post("/portal/{project_id}")
async def create_portal_session(project_id: str, return_url: str):
    """
    Create a Stripe Customer Portal session for managing subscription.
    """
    stripe = get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Billing not configured")
    
    try:
        customer_id = await _get_customer_id(project_id)
        if not customer_id:
            raise HTTPException(status_code=400, detail="No billing account found")
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        
        return {"portal_url": session.url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portal session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    
    Events handled:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    """
    stripe = get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Billing not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle events
    event_type = event["type"]
    data = event["data"]["object"]
    
    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(data)
        else:
            logger.info(f"Unhandled event type: {event_type}")
    except Exception as e:
        logger.error(f"Webhook handler failed for {event_type}: {e}")
        # Return 200 to acknowledge receipt even on handler errors
    
    return {"status": "ok"}


# --- Helper Functions ---

async def _get_or_create_customer(project_id: str) -> str:
    """Get existing Stripe customer or create new one."""
    from faim.db import SessionLocal
    from faim.models_sql import Org, Project, User
    
    stripe = get_stripe()
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Return existing customer if we have one
        if project.stripe_customer_id:
            return project.stripe_customer_id
        
        # Get org owner for email
        org = db.query(Org).filter(Org.id == project.org_id).first()
        owner = db.query(User).filter(User.id == org.owner_user_id).first() if org else None
        email = owner.email if owner else None
        
        # Create new customer
        customer = stripe.Customer.create(
            email=email,
            metadata={"project_id": project_id, "org_id": str(project.org_id)}
        )
        
        # Save customer ID
        project.stripe_customer_id = customer.id
        db.commit()
        
        return customer.id
        
    finally:
        db.close()


async def _get_customer_id(project_id: str) -> Optional[str]:
    """Get Stripe customer ID for a project."""
    from faim.db import SessionLocal
    from faim.models_sql import Project
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        return project.stripe_customer_id if project else None
    finally:
        db.close()


async def _handle_checkout_completed(session: dict):
    """Handle successful checkout - upgrade plan IMMEDIATELY."""
    project_id = session.get("metadata", {}).get("project_id")
    plan = session.get("metadata", {}).get("plan")
    subscription_id = session.get("subscription")
    
    if not project_id or not plan:
        logger.warning("Checkout completed but missing metadata")
        return
    
    from faim.api.plan_limits import get_plan_limits
    from faim.db import SessionLocal
    from faim.models_sql import Project
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            old_plan = project.plan
            
            # Update plan
            project.plan = plan
            project.stripe_subscription_id = subscription_id
            project.subscription_status = "active"
            
            # Update plan limits in JSON field
            limits = get_plan_limits(plan)
            project.plan_limits = {
                "tokens_max": limits["tokens"],
                "storage_mb_max": limits["storage_mb"],
                "tokens_used": (project.plan_limits or {}).get("tokens_used", 0),
                "upgraded_at": str(datetime.now()),
            }
            
            db.commit()
            logger.info(f"✅ Project {project_id} upgraded from {old_plan} to {plan} - {limits['tokens']:,} tokens now available")
    finally:
        db.close()


async def _handle_subscription_updated(subscription: dict):
    """Handle subscription updates (plan changes, renewals)."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    from faim.db import SessionLocal
    from faim.models_sql import Project
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(
            Project.stripe_customer_id == customer_id
        ).first()
        if project:
            project.subscription_status = status
            db.commit()
    finally:
        db.close()


async def _handle_subscription_deleted(subscription: dict):
    """Handle subscription cancellation - downgrade to free."""
    customer_id = subscription.get("customer")
    
    from faim.db import SessionLocal
    from faim.models_sql import Project
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(
            Project.stripe_customer_id == customer_id
        ).first()
        if project:
            project.plan = "free"
            project.subscription_status = "canceled"
            project.stripe_subscription_id = None
            db.commit()
            logger.info(f"Project {project.id} downgraded to free")
    finally:
        db.close()


async def _handle_payment_failed(invoice: dict):
    """Handle failed payment - mark subscription as past due."""
    customer_id = invoice.get("customer")
    
    from faim.db import SessionLocal
    from faim.models_sql import Project
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(
            Project.stripe_customer_id == customer_id
        ).first()
        if project:
            project.subscription_status = "past_due"
            db.commit()
            logger.warning(f"Payment failed for project {project.id}")
    finally:
        db.close()

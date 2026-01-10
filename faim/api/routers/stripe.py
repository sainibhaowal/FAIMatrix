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
    user_id: str
    plan: str  # "starter" or "custom"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionStatus(BaseModel):
    user_id: str
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
    from faim.api.services.usage_service import PLAN_LIMITS

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
            status_code=503, detail="Billing not configured. Please set STRIPE_SECRET_KEY environment variable."
        )

    # Get price ID from plan config
    price_id = plan_config.get("stripe_price_id")

    try:
        # Get or create Stripe customer
        customer_id = await _get_or_create_customer(payload.user_id)

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=payload.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=payload.cancel_url,
            metadata={"user_id": payload.user_id, "plan": payload.plan},
        )

        return CheckoutResponse(checkout_url=session.url, session_id=session.id)

    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/subscription/{user_id}", response_model=SubscriptionStatus)
async def get_subscription_status(user_id: str):
    """
    Get current subscription status for a user.
    """
    try:
        from faim.config.database import SessionLocal
        from faim.config.models import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # In new model, subscription status isn't explicitly stored on user
            # We derive it from plan and stripe_customer_id
            status = "active" if user.plan in ["starter", "custom"] else "free"

            return SubscriptionStatus(
                user_id=user_id,
                plan=user.plan,
                status=status,
                current_period_end=None,
                cancel_at_period_end=False,
            )
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription status")


@router.post("/portal/{user_id}")
async def create_portal_session(user_id: str, return_url: str):
    """
    Create a Stripe Customer Portal session for managing subscription.
    """
    stripe = get_stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="Billing not configured")

    try:
        customer_id = await _get_customer_id(user_id)
        if not customer_id:
            raise HTTPException(status_code=400, detail="No billing account found")

        session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)

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
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
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


async def _get_or_create_customer(user_id: str) -> str:
    """Get existing Stripe customer or create new one."""
    from faim.config.database import SessionLocal
    from faim.config.models import User

    stripe = get_stripe()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Return existing customer if we have one
        if user.stripe_customer_id:
            return user.stripe_customer_id

        # Create new customer
        customer = stripe.Customer.create(email=user.email, name=user.full_name, metadata={"user_id": user_id})

        # Save customer ID
        user.stripe_customer_id = customer.id
        db.commit()

        return customer.id

    finally:
        db.close()


async def _get_customer_id(user_id: str) -> Optional[str]:
    """Get Stripe customer ID for a user."""
    from faim.config.database import SessionLocal
    from faim.config.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user.stripe_customer_id if user else None
    finally:
        db.close()


async def _handle_checkout_completed(session: dict):
    """Handle successful checkout - upgrade plan IMMEDIATELY."""
    user_id = session.get("metadata", {}).get("user_id")
    plan = session.get("metadata", {}).get("plan")

    if not user_id or not plan:
        logger.warning("Checkout completed but missing metadata")
        return

    from faim.api.services.usage_service import get_plan_limits
    from faim.config.database import SessionLocal
    from faim.config.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            old_plan = user.plan

            # Update plan
            user.plan = plan
            # Note: We don't store subscription_id or status on user model currently
            # but we could add them if needed. For now, plan is the source of truth.

            # Update limits
            limits = get_plan_limits(plan)
            user.memories_max = limits["memories"]
            user.storage_max_bytes = limits["storage_bytes"]
            user.api_calls_max = limits["api_calls_month"]

            db.commit()
            logger.info(f"✅ User {user_id} upgraded from {old_plan} to {plan}")
    finally:
        db.close()


async def _handle_subscription_updated(subscription: dict):
    """Handle subscription updates (plan changes, renewals)."""
    # customer_id = subscription.get("customer")
    # status = subscription.get("status")

    # We don't act on updates yet, relying on checkout completion
    # In future, could downgrade if status != active
    pass


async def _handle_subscription_deleted(subscription: dict):
    """Handle subscription cancellation - downgrade to free."""
    customer_id = subscription.get("customer")

    from faim.api.services.usage_service import get_plan_limits
    from faim.config.database import SessionLocal
    from faim.config.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.plan = "free"

            # Reset limits to free
            limits = get_plan_limits("free")
            user.memories_max = limits["memories"]
            user.storage_max_bytes = limits["storage_bytes"]
            user.api_calls_max = limits["api_calls_month"]

            db.commit()
            logger.info(f"User {user.id} downgraded to free")
    finally:
        db.close()


async def _handle_payment_failed(invoice: dict):
    """Handle failed payment."""
    customer_id = invoice.get("customer")
    # Log warning, maybe notify user via email later
    logger.warning(f"Payment failed for customer {customer_id}")

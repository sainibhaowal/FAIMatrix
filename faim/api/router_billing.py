import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from faim.db import get_db
from faim.api.auth_middleware import get_current_user_oidc
from faim.models_sql import User, Project, Org, OrgMember

router = APIRouter(prefix="/billing", tags=["Billing"])

# --- Config ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

stripe.api_key = STRIPE_SECRET_KEY

# Plan Valid IDs (Prod/Test mismatch handled via env vars in real app)
PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "price_12345")

# --- Schemas ---
class CheckoutRequest(BaseModel):
    project_id: str
    price_id: Optional[str] = PRICE_ID_PRO

class PortalRequest(BaseModel):
    project_id: str

# --- Endpoints ---

@router.post("/checkout")
async def create_checkout_session(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_oidc)
):
    # Verify Admin/Owner Access
    member = (
        db.query(OrgMember)
        .join(Org)
        .join(Project)
        .filter(Project.id == payload.project_id)
        .filter(OrgMember.user_id == current_user.id)
        .filter(OrgMember.role.in_(["owner", "admin"]))
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    
    project = db.query(Project).get(payload.project_id)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': payload.price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=FRONTEND_URL + '/billing?success=true&session_id={CHECKOUT_SESSION_ID}',
            cancel_url=FRONTEND_URL + '/billing?canceled=true',
            client_reference_id=str(project.id),
            # If user already has stripe_customer_id, pass it to avoid dupes
            customer=project.stripe_customer_id if project.stripe_customer_id else None
        )
        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/portal")
async def create_portal_session(
    payload: PortalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_oidc)
):
    member = (
        db.query(OrgMember)
        .join(Org)
        .join(Project)
        .filter(Project.id == payload.project_id)
        .filter(OrgMember.user_id == current_user.id)
        .filter(OrgMember.role.in_(["owner", "admin"]))
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")

    project = db.query(Project).get(payload.project_id)
    if not project.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    try:
        session = stripe.billing_portal.Session.create(
            customer=project.stripe_customer_id,
            return_url=FRONTEND_URL + '/billing'
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle Events
    db = next(get_db()) # Manual session for webhook
    
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            project_id = session.get('client_reference_id')
            customer_id = session.get('customer')
            sub_id = session.get('subscription')
            
            if project_id:
                proj = db.query(Project).filter(Project.id == project_id).first()
                if proj:
                    proj.stripe_customer_id = customer_id
                    proj.stripe_subscription_id = sub_id
                    proj.plan = "pro" 
                    proj.subscription_status = "active"
                    # Update Limits
                    proj.plan_limits = {"graphs": 10, "storage_mb": 10240} # 10GB
                    db.commit()

        elif event['type'] == 'customer.subscription.deleted':
            sub = event['data']['object']
            # Find project by sub ID
            proj = db.query(Project).filter(Project.stripe_subscription_id == sub['id']).first()
            if proj:
                proj.plan = "free"
                proj.subscription_status = "canceled"
                proj.plan_limits = {"graphs": 1, "storage_mb": 100}
                db.commit()
                
    except Exception as e:
        print(f"Webhook Error: {e}")
        # Don't fail the webhook response, just log
    finally:
        db.close()

    return {"status": "success"}

import os
from datetime import datetime

import stripe
from fastapi import Request, Header, HTTPException, APIRouter

from support import database, models
from support.logger_config import logger

stripe_router = APIRouter()

stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:9000")


# -- API Endpoints for Stripe Integration --
@stripe_router.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    body = await request.json()
    user_id = body.get('user_id')

    if not user_id or not body.get("price_id"):
        raise HTTPException(status_code=404, detail="Missing required parameters")

    try:
        customer_id = database.create_or_fetch_customer(user_id)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": body['price_id'],
                "quantity": 1
            }],
            success_url=f"{FRONTEND_BASE_URL}/post",
            cancel_url=f"{FRONTEND_BASE_URL}/pricing",
        )
        return {"id": session.id}
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=400, detail="Error creating checkout session")
# End of create_checkout_session


@stripe_router.post("/create-customer-portal-session")
async def create_customer_portal_session(request: models.PortalSessionRequest):
    session = stripe.billing_portal.Session.create(
        customer=request.customer_id,
        return_url=f"{FRONTEND_BASE_URL}/settings/subscription",
    )
    return {"url": session.url}
# End of create_customer_portal_session


@stripe_router.post("/stripe-webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, stripe_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        logger.error("Invalid Stripe webhook payload or signature")
        raise HTTPException(status_code=400, detail="Invalid payload or signature")

    event_type = event.get("type")
    sub = event["data"]["object"]
    customer_id = sub.get("customer")

    # Load customer data
    res = database.supabase.table("subscriptions").select().eq("stripe_customer_id", customer_id).execute()
    if not res.data:
        logger.warning(f"No subscription found for customer_id: {customer_id}")
        raise HTTPException(status_code=404, detail="No subscription found")

    row_id = res.data[0]["id"]
    user_id = res.data[0].get("user_id")

    # Handle the event
    if event_type in ["customer.subscription.created", "customer.subscription.updated"]:
        status = sub["status"]
        price_id = sub["items"]["data"][0]["price"]["id"]
        ends_at = sub["items"]["data"][0]["current_period_end"]
        ends_at_datetime = datetime.utcfromtimestamp(ends_at)
        plan = sub["plan"]["metadata"]["tier"]

        if event_type == "customer.subscription.updated" and status == "canceled":
            return {"status": "canceled plan"}

        database.update_subscription(row_id, plan, status, price_id, ends_at_datetime)
        if event_type == "customer.subscription.updated":
            database.update_user_limits(user_id, plan)

    elif event_type == "customer.subscription.deleted":
        database.update_subscription(row_id, 'free', 'cancelled', 0, None)
        database.update_user_limits(user_id)

    return {"status": "success"}
# End of stripe_webhook

import asyncio
from datetime import datetime

from fastapi.encoders import isoformat

from env_tools import load_env_from_envvar
import os

import models
import bluesky
import mastodonapi
import lemmyapi
import pixelfedapi
import database

import stripe
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --- Constants ---
allowed_image_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
allowed_video_types = {"video/mp4", "video/webm"}

# Initialize the API and CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["https://yourfrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Decrypt secrets
load_env_from_envvar(".env.enc")
stripe.api_key = os.getenv("STRIPE_API_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# --- Posts ---
@app.post("/create_post/")
async def text_post(metadata: models.Post):
    if metadata.media_filenames:
        metadata.media_filenames = \
            await database.load_images(metadata.media_filenames, metadata.user_id)

    response = []
    if metadata.connected_accounts:
        tasks = []
        for account in metadata.connected_accounts:
            if account.platform == 'bluesky':
                tasks.append(bluesky.create_post(metadata, account))
            elif account.platform == 'mastodon':
                tasks.append(mastodonapi.create_post(metadata, account))
            elif account.platform == 'lemmy':
                tasks.append(lemmyapi.create_post(metadata, account))
            elif account.platform == 'pixelfed':
                tasks.append(pixelfedapi.create_post(metadata, account))

        if tasks:
            response = await asyncio.gather(*tasks, return_exceptions=True)

    if metadata.media_filenames:
        database.delete_images(metadata.media_filenames)

    database.upload_post_history(metadata, response)

    return response
# End of text_post

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    body = await request.json()
    user_id = body.get('user_id')
    print(f"Creating checkout session for user_id: {user_id}")

    if not user_id or not body.get("price_id"):
        return {"error": "Missing user_id or price_id"}

    try:
        customer_id = await database.create_or_fetch_customer(user_id)
        print(f"Customer ID: {customer_id}")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": body['price_id'],  # your price ID from Stripe dashboard
                "quantity": 1
            }],
            success_url="http://localhost:9000/post",  # your frontend success page
            cancel_url="http://localhost:9000/pricing",    # cancel page
        )
        return {"id": session.id}
    except Exception as e:
        return {"error": str(e)}
# End of create_checkout_session

@app.post("/create-customer-portal-session")
async def create_customer_portal_session(req: models.PortalSessionRequest):
    session = stripe.billing_portal.Session.create(
        customer=req.customer_id,
        return_url="http://localhost:9000/settings/subscription",
    )
    return {"url": session.url}
# End of create_customer_portal_session

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 🔄 Handle different subscription events
    # Subscription created
    if event["type"] == "customer.subscription.created":
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        status = sub["status"]
        price_id = sub["items"]["data"][0]["price"]["id"]
        ends_at = sub["items"]["data"][0]["current_period_end"]  # Unix timestamp
        ends_at_datetime = datetime.utcfromtimestamp(ends_at)
        plan = sub["plan"]["metadata"]["tier"]

        res = database.supabase.table("subscriptions").select("id").eq("stripe_customer_id", customer_id).execute()
        if res.data:
            user_id = res.data[0]["id"]

            # Update user’s subscription info
            database.supabase.table("subscriptions").update({
                "plan_name": plan,
                "subscription_status": status,
                "subscription_price_id": price_id,
                "subscription_ends_at": ends_at_datetime.isoformat()
            }).eq("id", user_id).execute()

    # Subscription updated
    elif event["type"] == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub["customer"]

        # ⛔ Skip if this update is just reflecting a scheduled cancellation
        if sub["status"] == "canceled":
            return {"status": "canceled plan"}

        status = sub["status"]
        price_id = sub["items"]["data"][0]["price"]["id"]
        ends_at = sub["items"]["data"][0]["current_period_end"]  # Unix timestamp
        ends_at_datetime = datetime.utcfromtimestamp(ends_at)
        plan = sub["plan"]["metadata"]["tier"]

        res = database.supabase.table("subscriptions").select("id").eq("stripe_customer_id", customer_id).execute()
        if res.data:
            user_id = res.data[0]["id"]

            # Update user’s subscription info
            database.supabase.table("subscriptions").update({
                "plan_name": plan,
                "subscription_status": status,
                "subscription_price_id": price_id,
                "subscription_ends_at": ends_at_datetime.isoformat()
            }).eq("id", user_id).execute()

    # Subscription cancelled
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]
        # Update user’s subscription info

        res = database.supabase.table("subscriptions").select("id").eq("stripe_customer_id", customer_id).execute()
        if res.data:
            user_id = res.data[0]["id"]

            # Set subscription to cancelled
            database.supabase.table("subscriptions").update({
                "plan_name": 'free',
                "subscription_status": 'cancelled',
                "subscription_price_id": 0,
                "subscription_ends_at": None
            }).eq("id", user_id).execute()

    return {"status": "success"}
# End of stripe_webhook
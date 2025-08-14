import os

import aiofiles
import stripe
from supabase import create_client, Client

from support import models
from support.logger_config import logger


url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

stripe.api_key = os.getenv("STRIPE_API_KEY")

async def load_images(img_list: list[str], folder_path: str):
    os.makedirs("../temp_images", exist_ok=True)
    paths = []

    # List all files in the given folder
    files = supabase.storage.from_('images').list(folder_path)

    for img_name in img_list:
        # Look for a file with the given base name and any extension
        match = next((f for f in files if f['name'] == img_name), None)
        if not match:
            logger.warn(f"❌ No file found in '{'images'}/{folder_path}' starting with '{img_name}'")
            continue

        # Construct full remote path and local path
        remote_path = os.path.join(folder_path, match['name'])
        local_path = os.path.join('../temp_images', match['name'])

        # Download image
        try:
            response = supabase.storage.from_('images').download(remote_path)
            async with aiofiles.open(local_path, "wb") as f:
                await f.write(response)
            paths.append(local_path)

            # Delete the Image
            supabase.storage.from_('images').remove([remote_path])
        except Exception as error:
            logger.error(f'Failed to delete image: {error}')
            continue

    return paths


def delete_images(local_paths: list[str]) -> None:
    if len(local_paths) == 0:
        return
    for x in range(min(len(local_paths), 4)):
        try:
            os.remove(local_paths[x])
        except Exception as error:
            logger.error(f"Warning: Could not delete {local_paths[x]}: {error}")


def upload_post_history(metadata: models.Post, platforms):
    try:
        result = supabase.table('posts').insert({
            'user_id': metadata.user_id,
            'content': metadata.message,
            'status': 'Success',
        }).execute()

        post_id = result.data[0]['id']

        if all(p.get('status') == 'success' for p in platforms):
            overall_status = 'Success'
        elif any(p.get('status') == 'success' for p in platforms):
            overall_status = 'Partial'
        else:
            overall_status = 'Failed'

        rows = []
        for platform in platforms:
            row = {
                'post_id': post_id,
                'user_id': metadata.user_id,
                'platform': platform.get('platform'),
                'instance': platform.get('instance'),
                'handle': platform.get('handle'),
                'status': overall_status,
                'message': platform.get('message'),
                'post_url': platform.get('post_url'),
                'external_post_id': str(platform.get('external_post_id')) if platform.get('external_post_id') else None,
            }
            rows.append(row)

        # Insert all rows in one call
        response = supabase.table('account_posts').insert(rows).execute()
        return response
    except Exception as error:
        logger.error(f'Failed to upload post history: {error}')
        return {"status": "error", "message": "Failed to upload post history"}


# End of upload_post_history

def update_subscription(row_id, plan, status, price_id, ends_at_datetime):
    supabase.table("subscriptions").update({
        "plan_name": plan,
        "subscription_status": status,
        "subscription_price_id": price_id,
        "subscription_ends_at": ends_at_datetime.isoformat() if ends_at_datetime else None
    }).eq("id", row_id).execute()
# End of update_subscription

def update_user_limits(user_id: str, plan: str = "free"):
    try:
        # Step 1: Get all users and their plan/account_limit
        account_limit = (supabase.table("plans")
                         .select("account_limit")
                         .eq("name", plan)
                         .single()
                         .execute()
                         .data)['account_limit']

        # Step 2: Get all connected accounts (enabled ones first)
        accounts = (supabase.table("linked_accounts")
                    .select()
                    .eq("user_id", user_id)
                    .execute()
                    .data)

        count: int = 0
        for account in accounts:
            count += 1
            if account['enabled'] and count > account_limit:
                account['enabled'] = False
        # End of for loop

        # Step 3: Update the accounts in Supabase
        for account in accounts:
            (supabase.table("linked_accounts")
             .update({"enabled": account['enabled']})
             .eq("id", account['id'])
             .execute())
        # End of for loop

        return {"status": "User downgraded successfully", "plan": plan}

    except Exception as error:
        logger.error(f"Error updating user limits: {error}")
        return {"status": "error", "message": "Failed to update user limits"}
# End of downgrade_user

def create_or_fetch_customer(user_id):
    # Lookup user from Supabase
    try:
        user = (supabase.table("subscriptions")
                .select("stripe_customer_id", "email")
                .eq("user_id", user_id)
                .single()
                .execute()
                .data)

        if user and user["stripe_customer_id"]:
            return user["stripe_customer_id"]

        # If no customer yet, create it in Stripe
        customer = stripe.Customer.create(email=user["email"], metadata={"user_id": user_id})
        # Store the customer ID in Supabase
        (supabase.table("subscriptions")
         .update({
            "stripe_customer_id": customer.id
        })
         .eq("user_id", user_id)
         .execute())

        return customer.id
    except Exception as e:
        logger.error(f"Error creating stripe customer: {e}")
        return {"status": "error", "message": "Failed to create or fetch customer"}
# End of create_or_fetch_customer


def delete_user(user_id: str):
    try:
        # Delete user from Supabase
        supabase.auth.admin.delete_user(user_id)
        user = (supabase.table("subscriptions")
                .select("stripe_customer_id", "email")
                .eq("user_id", user_id)
                .single()
                .execute()
                .data)
        if user and user["stripe_customer_id"]:
            stripe.Customer.delete(user["stripe_customer_id"])
        return {"status": "User deleted successfully"}
    except Exception as error:
        logger.error(f"Error deleting user {user_id}: {error}")
        return {"status": "error", "message": "Failed to delete user"}
# End of delete_user
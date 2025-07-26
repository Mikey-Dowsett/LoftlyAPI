import os
from dotenv import load_dotenv
from supabase import create_client, Client
import aiofiles
import stripe

import models

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
stripe.api_key = os.getenv("STRIPE_API_KEY")

async def load_images(img_list: list[str], folder_path: str):
    os.makedirs("temp_images", exist_ok=True)
    paths = []

    # List all files in the given folder
    files = supabase.storage.from_('images').list(folder_path)

    for img_name in img_list:
        # Look for a file with the given base name and any extension
        match = next((f for f in files if f['name'] == img_name), None)
        if not match:
            print(f"❌ No file found in '{'images'}/{folder_path}' starting with '{img_name}'")
            continue

        # Construct full remote path and local path
        remote_path = os.path.join(folder_path, match['name'])
        local_path = os.path.join('temp_images', match['name'])

        #Download image
        try:
            response = supabase.storage.from_('images').download(remote_path)
            async with aiofiles.open(local_path, "wb") as f:
                await f.write(response)
            paths.append(local_path)

            #Delete the Image
            supabase.storage.from_('images').remove([remote_path])
        except Exception as e:
            print(e)

    return paths

def delete_images(local_paths: list[str]) -> None:
    if len(local_paths) == 0:
        return
    for x in range(min(len(local_paths), 4)):
        try:
            os.remove(local_paths[x])
        except Exception as e:
            print(f"Warning: Could not delete {local_paths[x]}: {e}")


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
    except Exception as e:
        print(f'Error {e}')
        return None

async def create_or_fetch_customer(user_id):
    # Lookup user from Supabase
    try:
        print("Fetching user from Supabase...")
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
        print(f"Created Stripe customer: {customer.id}")
        # Store the customer ID in Supabase
        (supabase.table("subscriptions")
         .update({
            "stripe_customer_id": customer.id
            })
         .eq("user_id", user_id)
         .execute())

        return customer.id
    except Exception as e:
        return {"error": str(e)}
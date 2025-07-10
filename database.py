import os
from dotenv import load_dotenv
from supabase import create_client, Client
import aiofiles
import asyncio

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

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
import asyncio
from env_tools import load_env_from_envvar
import os

import models
import bluesky
import mastodonapi
import lemmyapi
import pixelfedapi
import database

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Constants ---
allowed_image_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
allowed_video_types = {"video/mp4", "video/webm"}

#Initialize the API and CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["https://yourfrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Decrypt secrets
load_env_from_envvar(".env.enc")

# Now your secrets are available as usual:
print(os.getenv("SUPABASE_KEY"))

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
#End of text_post
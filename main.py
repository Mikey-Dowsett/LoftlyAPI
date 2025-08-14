import asyncio
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from support import database, models, stripe_api
from support.logger_config import logger
from platforms import mastodonapi, bluesky, lemmyapi, pixelfedapi

# --- Constants ---
allowed_image_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
allowed_video_types = {"video/mp4", "video/webm"}

# Initialize the API and CORS
app = FastAPI()
app.include_router(stripe_api.stripe_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Endpoints ---
@app.post("/create-post/")
async def text_post(metadata: models.Post):
    try:
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
    except Exception as error:
        logger.error(f"Error creating post: {error}")
        raise HTTPException(status_code=500, detail="Error creating post")
# End of text_post

@app.post("/delete-user")
async def delete_user(request: models.DeleteUserRequest):
    try:
        return database.delete_user(request.user_id)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"Error deleting user")
# End of delete_user
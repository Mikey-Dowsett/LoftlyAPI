import models
import bluesky
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

# --- Posts ---
@app.post("/create_post/")
async def text_post(metadata: models.Post):
    response = []
    if metadata.connected_accounts:
        for account in metadata.connected_accounts:
            if account.platform == 'bluesky':
                response.append(await bluesky.create_post(metadata, account))

    return response
#End of text_post

# --- Data Base Interactions ---
@app.get("/load_image")
async def load_image():
    return database.load_images(
        ['Fire', 'Ghibli'],
        'testing')
import asyncio
import mimetypes

from atproto import Client
from atproto_client.models.app.bsky import embed

import image_handler
import models

client = Client()


# --- Upload Functions ---
async def create_post(metadata: models.Post, account: models.ConnectedAccount) -> dict:
    try:
        client.login(account.handle, account.app_password)
    except Exception as e:
        return models.BuildPostResponse(
            account, 'error', f"Failed to initialize client: {e}")

    # Create the message
    upload_responses = []
    local_paths = []

    # Download any images
    if metadata.media_filenames and len(metadata.media_filenames) > 0:
        local_paths = metadata.media_filenames
        # Compress Images
        for i in range(min(len(local_paths), 4)):
            mime_type, _ = mimetypes.guess_type(local_paths[i])
            image_bytes = image_handler.compress_image(local_paths[i], mime_type)
            for attempt in range(2):
                try:
                    response = client.com.atproto.repo.upload_blob(image_bytes)
                    upload_responses.append(response)
                    break
                except Exception as e:
                    print(f'Attempt {attempt + 1} failed uploading {local_paths[i]}: {type(e).__name__}: {e}')
                    await asyncio.sleep(1)
            else:
                return models.BuildPostResponse(
                    account, 'error', f"Upload failed for {local_paths[i]}")

    # Upload the post
    try:
        # Upload Images
        if len(upload_responses) > 0:
            images = [
                embed.images.Image(
                    alt=local_paths[i] or "image",
                    image=upload_responses[i].blob
                ) for i in range(len(upload_responses))
            ]
            image_embed = embed.images.Main(images=images)
            post = client.send_post(text=metadata.message, embed=image_embed)
        # Or a plain text message
        else:
            post = client.send_post(text=metadata.message)

        return models.BuildPostResponse(
            account, 'success', 'Successfully posted', post.uri, post.cid)
    except Exception as e:
        return models.BuildPostResponse(
            account, 'error', str(e))
# End of create_post

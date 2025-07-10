import mimetypes
import time
import os
import asyncio

from atproto_client.utils import TextBuilder

import image_handler
import models
import database
from atproto import Client, client_utils
from urllib.parse import urlparse
from atproto_client.models.app.bsky import embed

client = Client()

# --- Upload Functions ---
async def create_post(metadata: models.Post, account: models.ConnectedAccount) -> dict:
    try:
        client.login(account.handle, account.app_password)
    except Exception as e:
        return {'status': 'error',
                'platform': 'Bluesky',
                'message': f"Validation for account failed: {e}"}
    #Create the message
    message = ''
    if metadata.message:
        message = create_message(metadata)
    upload_responses = []
    local_paths = []

    #Download any images
    if metadata.media_filenames and len(metadata.media_filenames) > 0:
        local_paths = await database.load_images(metadata.media_filenames, metadata.author_id)
        #Compress Images
        for x in range(min(len(local_paths), 4)):
            mime_type, _ = mimetypes.guess_type(local_paths[x])
            image_bytes = image_handler.compress_image(local_paths[x], mime_type)
            for attempt in range(2):
                try:
                    response = client.com.atproto.repo.upload_blob(image_bytes)
                    upload_responses.append(response)
                    break
                except Exception as e:
                    print(f'Attempt {attempt + 1} failed uploading {local_paths[x]}: {type(e).__name__}: {e}')
                    await asyncio.sleep(1)
            else:
                return {'status': 'error',
                        'platform': 'Bluesky',
                        'message': f"Bluesky upload of {local_paths[x]} timed out after retries."}

    #Upload the post
    try:
        #Upload Images
        if len(upload_responses) > 0:
            images = [
                embed.images.Image(
                    alt=local_paths[i] or "image",
                    image=upload_responses[i].blob
                ) for i in range(len(upload_responses))
            ]
            image_embed = embed.images.Main(images=images)
            post = client.send_post(text=message, embed=image_embed)
        #Or a plain text message
        else:
            post = client.send_post(text=message)

        delete_images(local_paths)
        return {'status': 'success',
                'platform': 'Bluesky',
                'post_uri': post.uri}
    except Exception as e:
        delete_images(local_paths)
        return {'status': 'error',
                'platform': 'Bluesky',
                'message': str(e)}
# End of create_post

# --- Support Functions ---
def create_message(metadata: models.Post) -> TextBuilder:
    message = client_utils.TextBuilder()
    message.text(metadata.message)
    return message
# End of create_message

def is_valid_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    return all([parsed.scheme in ("http", "https", "at", "did"), parsed.netloc or parsed.path])
# End of is_valid_uri

def delete_images(local_paths: list[str]) -> None:
    if len(local_paths) == 0:
        return
    for x in range(min(len(local_paths), 4)):
        try:
            os.remove(local_paths[x])
        except Exception as e:
            print(f"Warning: Could not delete {local_paths[x]}: {e}")
# End of delete_images
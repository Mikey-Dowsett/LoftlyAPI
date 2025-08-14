import asyncio
import mimetypes
from typing import List

from atproto import Client
from atproto_client.models.app.bsky import embed

from support import image_handler, models
from support.logger_config import logger

client = Client()


# --- Upload Functions ---
async def create_post(metadata: models.Post, account: models.ConnectedAccount) -> dict:
    """
    Create and upload a post with optional images to Bluesky.

    Args:
        metadata: Post metadata including message and media filenames.
        account: ConnectedAccount with handle and app_password.

    Returns:
        BuildPostResponse with status and details.
    """
    try:
        client.login(account.handle, account.app_password)
    except Exception as error:
        logger.error(f'Failed to initialize Bluesky client: {error}')
        return models.BuildPostResponse(
            account, 'error', "Failed to initialize Bluesky client")

    # Create the message
    image_responses: List = []
    local_paths: List[str] = []

    # Download and compress any images
    if metadata.media_filenames and len(metadata.media_filenames) > 0:
        local_paths = metadata.media_filenames

        # Compress Images
        for i, path in enumerate(local_paths[:4]):
            mime_type, _ = mimetypes.guess_type(path)
            try:
                image_bytes = image_handler.compress_image(path, mime_type)
            except Exception as error:
                logger.error(f'Failed to compress image {path}: {error}')
                return models.BuildPostResponse(
                    account, 'error', f"Failed to compress image {path}")

            for attempt in range(2):
                try:
                    response = client.com.atproto.repo.upload_blob(image_bytes)
                    image_responses.append(response)
                    break
                except Exception as error:
                    logger.warning(f'Attempt {attempt + 1} failed uploading {path}: {type(error).__name__}: {error}')
                    await asyncio.sleep(1)
            else:
                logger.error(f"Upload failed for {path}")
                return models.BuildPostResponse(
                    account, 'error', f"Upload failed for {path}")

    # Upload the post
    try:
        if len(image_responses) > 0:
            # Upload Images
            images = [
                embed.images.Image(
                    alt=local_paths[i] or "image",
                    image=image_responses[i].blob
                ) for i in range(len(image_responses))
            ]
            image_embed = embed.images.Main(images=images)
            post = client.send_post(text=metadata.message, embed=image_embed)
        else:
            # Or a plain text message
            post = client.send_post(text=metadata.message)

        return models.BuildPostResponse(
            account, 'success', 'Successfully posted', post.uri, post.cid)
    except Exception as error:
        logger.error(f'Failed to post {metadata.message}: {error}')
        return models.BuildPostResponse(
            account, 'error', f'Failed to post: {metadata.message} to Bluesky')
# End of create_post
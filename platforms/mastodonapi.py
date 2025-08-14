import mimetypes
import os

from mastodon import Mastodon, MastodonError

from support import image_handler, models
from support.logger_config import logger


# --- Upload Functions ---
async def create_post(metadata: models.Post, account: models.ConnectedAccount) -> dict:
    """
    Create and upload a post to Mastodon, with optional images.

    Args:
        metadata: Post metadata including message and media filenames.
        account: ConnectedAccount with access_token and instance.

    Returns:
        BuildPostResponse with status and details.
    """
    try:
        mastodon = Mastodon(
            access_token=account.access_token,
            api_base_url=account.instance,
        )
    except Exception as error:
        logger.error(f'Failed to initialize Mastodon client: {error}')
        return models.BuildPostResponse(
            account, 'error', f"Failed to initialize Mastodon client")

    message = metadata.message or ""
    media_ids = []

    # Download and upload media (max 4 images)
    if metadata.media_filenames and len(metadata.media_filenames) > 0:
        local_paths = metadata.media_filenames

        for i, file in enumerate(local_paths[:4]):
            mime_type, _ = mimetypes.guess_type(file)

            try:
                image_bytes = image_handler.compress_image(file, mime_type)
            except Exception as error:
                logger.error(f'Failed to compress image {file}: {error}')
                return models.BuildPostResponse(
                    account, 'error', f"Failed to compress image {file}")

            try:
                media = mastodon.media_post(
                    media_file=image_bytes,
                    mime_type=mime_type,
                    description=os.path.basename(file) or "Image"
                )
                media_ids.append(media['id'])
            except MastodonError as error:
                logger.error(f'Failed to upload image {file}: {error}')
                return models.BuildPostResponse(
                    account, 'error', f"Upload failed for {file}")

    # Try to post
    try:
        post = mastodon.status_post(status=message, media_ids=media_ids or None)

        return models.BuildPostResponse(
            account, 'success', 'Successfully posted', post.url, post.id)
    except MastodonError as error:
        logger.error(f'Failed to post: {metadata.message} to Mastodon: {error}')
        return models.BuildPostResponse(
            account, 'error', f'Failed to post: {metadata.message} to Mastodon')

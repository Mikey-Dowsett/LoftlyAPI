import mimetypes
import os

from mastodon import Mastodon, MastodonError

from support import image_handler, models
from support.logger_config import logger


# --- Upload to Pixelfed ---
async def create_post(metadata: models.Post, account: models.ConnectedAccount) -> dict:
    """
    Create and upload a post to Pixelfed, with required images.

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
        logger.error(f'Failed to initialize Pixelfed client: {error}')
        return models.BuildPostResponse(
            account, 'error', f"Failed to initialize Pixelfed client")

    message = metadata.message or ""
    local_paths = metadata.media_filenames or []
    media_ids = []

    if not local_paths:
        logger.error(f'No media filenames provided.')
        return models.BuildPostResponse(
            account, 'error', "Pixelfed requires at least one image.")

    for i, path in enumerate(local_paths[:10]):
        mime_type, _ = mimetypes.guess_type(path)

        try:
            image_bytes = image_handler.compress_image(path, mime_type)
        except Exception as error:
            logger.error(f"Image compression failed for {path}: {error}")
            return models.BuildPostResponse(
                account, 'error', f"Image compression failed for {path}: {error}")

        try:
            media = mastodon.media_post(
                media_file=image_bytes,
                mime_type=mime_type,
                description=os.path.basename(path) or "Image"
            )
            media_ids.append(media['id'])
        except MastodonError as error:
            logger.error(f"Failed to upload image {path} to Pixelfed: {error}")
            return models.BuildPostResponse(
                account, 'error', f"Failed to upload image {path} to Pixelfed")

    try:
        post = mastodon.status_post(
            status=message,
            media_ids=media_ids,
            visibility='public'
        )

        return models.BuildPostResponse(
            account, 'success', 'Successfully posted', post.url, post.id)
    except MastodonError as error:
        logger.error(f"Failed to post: {metadata.message} to Pixelfed: {error}")
        return models.BuildPostResponse(
            account, 'error', f'Failed to post: {metadata.message} to Pixelfed')

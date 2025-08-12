import mimetypes
import os

from mastodon import Mastodon, MastodonError

import image_handler
import models


# --- Upload to Pixelfed ---
async def create_post(metadata: models.Post, account: models.ConnectedAccount) -> dict:
    try:
        mastodon = Mastodon(
            access_token=account.access_token,
            api_base_url=account.instance,
        )
    except Exception as e:
        return models.BuildPostResponse(
            account, 'error', f"Failed to initialize client: {e}")

    message = metadata.message or ""
    local_paths = metadata.media_filenames or []
    media_ids = []

    if not local_paths:
        return models.BuildPostResponse(
            account, 'error', "Pixelfed requires at least one image.")

    for i in range(min(len(local_paths), 10)):
        mime_type, _ = mimetypes.guess_type(local_paths[i])
        image_bytes = image_handler.compress_image(local_paths[i], mime_type)

        try:
            media = mastodon.media_post(
                media_file=image_bytes,
                mime_type=mime_type,
                description=os.path.basename(local_paths[i]) or "Image"
            )
            media_ids.append(media['id'])
        except MastodonError as e:
            return models.BuildPostResponse(
                account, 'error', f"Upload failed for {local_paths[i]}: {e}")

    try:
        post = mastodon.status_post(
            status=message,
            media_ids=media_ids,
            visibility='public'  # Pixelfed requires this; 'public' is safest default
        )

        return models.BuildPostResponse(
            account, 'success', 'Successfully posted', post.url, post.id)
    except MastodonError as e:
        return models.BuildPostResponse(
            account, 'error', str(e))

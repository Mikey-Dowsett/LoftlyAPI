import mimetypes
from urllib.parse import urljoin

import requests

import models
from image_handler import compress_image
from models import Post, ConnectedAccount


# -- LEMMY POST CREATION --
async def create_post(metadata: Post, account: ConnectedAccount):
    headers = {
        'Authorization': f'Bearer {account.access_token}',
        'Content-Type': 'application/json'
    }

    # Determine post type: link (with image), or self-text
    is_image_post = metadata.media_filenames and len(metadata.media_filenames) > 0
    post_type = 'link' if is_image_post else 'self'

    # If it's an image post, you need to upload or host image and pass the URL
    if is_image_post:
        # Only use first image (Lemmy supports only one link)
        image_path = metadata.media_filenames[0]
        mime_type, _ = mimetypes.guess_type(image_path)
        image_bytes = compress_image(image_path, mime_type)
        image_url = upload_image_to_your_host(image_path, image_bytes)
        if not image_url:
            return models.BuildPostResponse(
                account, 'error', 'Image upload failed or hosting unavailable.')

    results = []

    print(account.lemmy_communities)

    for community in account.lemmy_communities:
        print(community.instance)
        base_url = 'https://' + community.instance
        endpoint = urljoin(base_url, '/api/v3/post')

        post_data = {
            'name': metadata.title or 'Untitled Post',
            'community_id': community.community_id,
            'nsfw': metadata.nsfw or False,
            'language_id': 0,
            'body': metadata.message,
            'url': metadata.lemmy_image_url or None,
        }

        try:
            response = requests.post(endpoint, headers=headers, json=post_data)
            response.raise_for_status()
            post_info = response.json()

            post_id = post_info['post_view']['post']['id']
            post_url = urljoin(base_url, f"post/{post_id}")

            results.append(
                models.BuildPostResponse(
                    account, 'success', f'Successfully posted to {community.community_name}', post_url, post_id))
        except requests.HTTPError as e:
            results.append(
                models.BuildPostResponse(
                    account, 'error', f'HTTP {e.response.status_code}: {e.response.text}'))
        except Exception as e:
            results.append(
                models.BuildPostResponse(
                    account, 'error', str(e)))

    return results


# -- IMAGE HOSTING PLACEHOLDER --
def upload_image_to_your_host(image_path: str, image_bytes: bytes) -> str:
    """
    Uploads image to a public host and returns the URL.
    This function is a stub. You must implement it to fit your infrastructure.
    """
    # Options: Imgur, Cloudflare R2, local server, IPFS, etc.
    # For now return None or a dummy URL for testing
    return None  # or e.g. "https://yourcdn.com/uploads/" + os.path.basename(image_path)

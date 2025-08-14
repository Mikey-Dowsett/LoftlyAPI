from urllib.parse import urljoin
from typing import List

import requests

from support import models
from support.models import Post, ConnectedAccount
from support.logger_config import logger


# -- LEMMY POST CREATION --
async def create_post(metadata: Post, account: ConnectedAccount) -> List[models.BuildPostResponse]:
    """
    Create and upload a post to Lemmy.

    Args:
        metadata: Post metadata including title, message, and media filenames.
        account: ConnectedAccount with access_token and communities.

    Returns:
        List of BuildPostResponse objects for each community.
    """
    headers = {
        'Authorization': f'Bearer {account.access_token}',
        'Content-Type': 'application/json'
    }

    results = []

    for community in account.lemmy_communities:
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
        except requests.HTTPError as error:
            logger.error(f'Failed to post to {community.community_name}: {error}')
            results.append(
                models.BuildPostResponse(
                    account, 'error', f'Failed to post to {community.community_name}'))
        except Exception as error:
            logger.error(f'Failed to post to {community.community_name}: {error}')
            results.append(
                models.BuildPostResponse(
                    account, 'error', f'Failed to post to {community.community_name}'))

    return results

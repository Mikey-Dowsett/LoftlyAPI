from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


# --- Enums ---
class PostType(str, Enum):
    TEXT = "text"
    MEDIA = "media"
    VIDEO = "video"
    POLL = "poll"


# End of PostType

class PostVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    FOLLOWERS = "followers"


# End of PostVisibility

# --- Support Models ---
class LemmyCommunity(BaseModel):
    instance: Optional[str] = None
    community_name: Optional[str] = None
    community_id: Optional[int] = None


# End of LemmyCommunity

class PollOption(BaseModel):
    option_text: Optional[str] = None
    vote_count: Optional[int] = 0


# End of PollOption

class PollData(BaseModel):
    question: Optional[str] = None
    options: Optional[List[PollOption]] = None
    expires_at: Optional[datetime] = None


# End of PollData

class ConnectedAccount(BaseModel):
    platform: Optional[str] = None
    handle: Optional[str] = None
    account_url: Optional[str] = None
    did: Optional[str] = None
    app_password: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    instance: Optional[str] = None
    lemmy_communities: Optional[List[LemmyCommunity]] = None


# End of Connected Account

class PortalSessionRequest(BaseModel):
    customer_id: str


# End of PortalSessionRequest

class DeleteUserRequest(BaseModel):
    user_id: str


# End of DeleteUserRequest

# --- Main Post Model ---
class Post(BaseModel):
    # Core Content
    title: Optional[str] = None
    message: Optional[str] = Field(None, description="Main text content")
    language: Optional[str] = None
    nsfw: Optional[bool] = None

    # Accounts
    connected_accounts: Optional[List[ConnectedAccount]] = None

    # Media
    media_filenames: Optional[List[str]] = None
    lemmy_image_url: Optional[str] = None
    video_filename: Optional[str] = None

    # Polls
    poll: Optional[PollData] = None

    # Metadata
    type: Optional[PostType] = Field(default=PostType.TEXT)
    visibility: Optional[PostVisibility] = Field(default=PostVisibility.PUBLIC)
    user_id: Optional[str] = None
    supabase_jwt: Optional[str] = None
    supabase_refresh_jwt: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# End of Post

def BuildPostResponse(account: ConnectedAccount, status: str, message: str, post_url: Optional[str] = None,
                      external_post_id: Optional[str] = None):
    return {
        'platform': account.platform,
        'instance': account.instance,
        'handle': account.handle,
        'status': status,
        'message': message,
        'post_url': post_url,
        'external_post_id': external_post_id,
    }

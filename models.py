from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Enums ---
class PostType(str, Enum):
    TEXT = "text"
    MEDIA = "media"
    VIDEO = "video"
    POLL = "poll"
#End of PostType

class PostVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    FOLLOWERS = "followers"
#End of PostVisibility

# --- Support Models ---
class PollOption(BaseModel):
    option_text: Optional[str] = None
    vote_count: Optional[int] = 0
#End of PollOption

class PollData(BaseModel):
    question: Optional[str] = None
    options: Optional[List[PollOption]] = None
    expires_at: Optional[datetime] = None

class ConnectedAccount(BaseModel):
    platform: Optional[str] = None
    access_token: Optional[str] = None
    handle: Optional[str] = None
    did: Optional[str] = None
    app_password: Optional[str] = None
#End of PollData

# --- Main Post Model ---
class Post(BaseModel):
    #Core Content
    message: Optional[str] = Field(None, description="Main text content")
    connected_accounts: Optional[List[ConnectedAccount]] = None

    #Media
    media_filenames: Optional[List[str]] = None
    video_filename: Optional[str] = None

    #Polls
    poll: Optional[PollData] = None

    #Metadata
    type: Optional[PostType] = Field(default=PostType.TEXT)
    visibility: Optional[PostVisibility] = Field(default=PostVisibility.PUBLIC)
    author_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
#End of Post
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "YouTube Metadata Automation"
    base_url: str = Field(..., description="Public Render URL, for example https://app.onrender.com")
    webhook_secret: str = Field(..., min_length=16)
    admin_token: str = Field(..., min_length=16)

    youtube_channel_id: str = Field(..., description="Your YouTube channel ID")
    youtube_uploads_playlist_id: Optional[str] = Field(
        default=None,
        description="Optional uploads playlist ID. If unset, the app resolves it from the channel.",
    )
    youtube_client_id: str = Field(...)
    youtube_client_secret: str = Field(...)
    youtube_refresh_token: str = Field(...)

    default_description: str = Field(
        default="Thanks for watching!\n\nSubscribe for more videos.",
        description="Default description template. Supports {title}, {video_id}, {trending_topics}, and {trending_hashtags}.",
    )
    default_tags: List[str] = Field(default_factory=list)
    default_hashtags: List[str] = Field(default_factory=list)
    max_tags: int = Field(default=45, ge=1, le=100)

    enable_trending_enrichment: bool = True
    trending_region_code: str = "US"
    trending_video_category_id: Optional[str] = None
    trending_limit: int = Field(default=15, ge=1, le=50)
    trending_tag_limit: int = Field(default=12, ge=0, le=30)
    trending_title_keyword_limit: int = Field(default=8, ge=0, le=20)

    update_only_existing_videos: bool = True
    processed_store_path: str = "data/processed_videos.json"
    dry_run: bool = False
    auto_subscribe_on_startup: bool = True

    @field_validator("default_tags", "default_hashtags", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("Expected a comma-separated string or list")

    @field_validator("base_url")
    @classmethod
    def strip_base_url(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()

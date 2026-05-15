from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Settings
from app.metadata import MetadataResult, TrendingVideo, build_metadata

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


@dataclass(frozen=True)
class UpdateResult:
    video_id: str
    title: str
    dry_run: bool
    description: str
    tags: List[str]
    trending_topics: List[str]
    updated_at: str


class YouTubeClient:
    """Wrapper around YouTube Data API operations used by the app."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        credentials = Credentials(
            token=None,
            refresh_token=settings.youtube_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
            scopes=YOUTUBE_SCOPES,
        )
        self.service = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            credentials=credentials,
            cache_discovery=False,
        )

    def update_video_metadata(self, video_id: str) -> UpdateResult:
        video = self.get_video(video_id)
        snippet = video["snippet"]
        title = snippet["title"]
        trending_videos = self.get_trending_videos() if self.settings.enable_trending_enrichment else []
        metadata = build_metadata(
            video_id=video_id,
            title=title,
            default_description=self.settings.default_description,
            default_tags=self.settings.default_tags,
            default_hashtags=self.settings.default_hashtags,
            trending_videos=trending_videos,
            max_tags=self.settings.max_tags,
            trending_tag_limit=self.settings.trending_tag_limit,
            trending_title_keyword_limit=self.settings.trending_title_keyword_limit,
        )

        if not self.settings.dry_run:
            self._update_snippet(video_id=video_id, original_snippet=snippet, metadata=metadata)

        return UpdateResult(
            video_id=video_id,
            title=title,
            dry_run=self.settings.dry_run,
            description=metadata.description,
            tags=metadata.tags,
            trending_topics=metadata.trending_topics,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_video(self, video_id: str) -> Dict[str, Any]:
        response = (
            self.service.videos()
            .list(part="snippet", id=video_id)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            raise ValueError(f"No YouTube video found for id {video_id}")
        return items[0]

    def get_latest_upload_video_id(self) -> str:
        playlist_id = self.settings.youtube_uploads_playlist_id or self.get_uploads_playlist_id()
        response = (
            self.service.playlistItems()
            .list(part="contentDetails", playlistId=playlist_id, maxResults=1)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            raise ValueError("No uploaded videos found for the configured channel")
        return items[0]["contentDetails"]["videoId"]

    def get_uploads_playlist_id(self) -> str:
        response = (
            self.service.channels()
            .list(part="contentDetails", id=self.settings.youtube_channel_id)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            raise ValueError(f"No channel found for id {self.settings.youtube_channel_id}")
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    def get_trending_videos(self) -> Sequence[TrendingVideo]:
        request_kwargs: Dict[str, Any] = {
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": self.settings.trending_region_code,
            "maxResults": self.settings.trending_limit,
        }
        if self.settings.trending_video_category_id:
            request_kwargs["videoCategoryId"] = self.settings.trending_video_category_id

        response = self.service.videos().list(**request_kwargs).execute()
        trending: List[TrendingVideo] = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            trending.append(
                TrendingVideo(
                    title=str(snippet.get("title", "")),
                    tags=[str(tag) for tag in snippet.get("tags", [])],
                )
            )
        return trending

    def subscribe_to_upload_notifications(self) -> Dict[str, str]:
        import httpx

        topic_url = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={self.settings.youtube_channel_id}"
        callback_url = f"{self.settings.base_url}/youtube/webhook?secret={self.settings.webhook_secret}"
        data = {
            "hub.mode": "subscribe",
            "hub.topic": topic_url,
            "hub.callback": callback_url,
            "hub.verify": "async",
        }
        response = httpx.post("https://pubsubhubbub.appspot.com/subscribe", data=data, timeout=20)
        response.raise_for_status()
        return {"topic": topic_url, "callback": callback_url, "status": "subscription requested"}

    def _update_snippet(self, *, video_id: str, original_snippet: Dict[str, Any], metadata: MetadataResult) -> None:
        updated_snippet = {
            "title": original_snippet["title"],
            "description": metadata.description,
            "tags": metadata.tags,
            "categoryId": original_snippet["categoryId"],
        }
        if "defaultLanguage" in original_snippet:
            updated_snippet["defaultLanguage"] = original_snippet["defaultLanguage"]
        if "defaultAudioLanguage" in original_snippet:
            updated_snippet["defaultAudioLanguage"] = original_snippet["defaultAudioLanguage"]

        self.service.videos().update(
            part="snippet",
            body={"id": video_id, "snippet": updated_snippet},
        ).execute()

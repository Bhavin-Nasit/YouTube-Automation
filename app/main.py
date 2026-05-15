from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.storage import ProcessedVideoStore
from app.youtube_client import UpdateResult, YouTubeClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    settings = get_settings()
    if settings.auto_subscribe_on_startup:
        try:
            YouTubeClient(settings).subscribe_to_upload_notifications()
            logger.info("YouTube upload notification subscription requested")
        except Exception as exc:  # startup should not fail because subscription can be retried via admin endpoint
            logger.warning("Unable to subscribe to YouTube upload notifications on startup: %s", exc)
    yield


app = FastAPI(title="YouTube Metadata Automation", version="1.0.0", lifespan=lifespan)

YOUTUBE_XML_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


class ProcessRequest(BaseModel):
    video_id: Optional[str] = None
    force: bool = False


class ProcessResponse(BaseModel):
    status: str
    video_id: str
    title: Optional[str] = None
    dry_run: Optional[bool] = None
    updated_at: Optional[str] = None
    trending_topics: list[str] = []


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[Optional[str], Header()] = None,
) -> None:
    expected = f"Bearer {settings.admin_token}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


def get_youtube_client(settings: Annotated[Settings, Depends(get_settings)]) -> YouTubeClient:
    return YouTubeClient(settings)


def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> ProcessedVideoStore:
    return ProcessedVideoStore(settings.processed_store_path)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/youtube/webhook")
def verify_webhook(
    settings: Annotated[Settings, Depends(get_settings)],
    secret: str = Query(...),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> Response:
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")
    return Response(content=hub_challenge, media_type="text/plain")


@app.post("/youtube/webhook", response_model=ProcessResponse)
async def receive_webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    youtube: Annotated[YouTubeClient, Depends(get_youtube_client)],
    store: Annotated[ProcessedVideoStore, Depends(get_store)],
    secret: str = Query(...),
) -> ProcessResponse:
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    payload = await request.body()
    video_id = extract_video_id(payload)
    if not video_id:
        logger.info("Webhook did not include a video id; ignoring")
        return ProcessResponse(status="ignored", video_id="")

    return process_video(video_id=video_id, force=False, youtube=youtube, store=store)


@app.post("/admin/subscribe", dependencies=[Depends(require_admin)])
def subscribe(youtube: Annotated[YouTubeClient, Depends(get_youtube_client)]) -> dict[str, str]:
    return youtube.subscribe_to_upload_notifications()


@app.post("/admin/process", response_model=ProcessResponse, dependencies=[Depends(require_admin)])
def process_endpoint(
    body: ProcessRequest,
    youtube: Annotated[YouTubeClient, Depends(get_youtube_client)],
    store: Annotated[ProcessedVideoStore, Depends(get_store)],
) -> ProcessResponse:
    video_id = body.video_id or youtube.get_latest_upload_video_id()
    return process_video(video_id=video_id, force=body.force, youtube=youtube, store=store)


def process_video(
    *,
    video_id: str,
    force: bool,
    youtube: YouTubeClient,
    store: ProcessedVideoStore,
) -> ProcessResponse:
    if store.has(video_id) and not force:
        existing = store.get(video_id) or {}
        return ProcessResponse(
            status="already_processed",
            video_id=video_id,
            title=existing.get("title") if isinstance(existing.get("title"), str) else None,
            dry_run=bool(existing.get("dry_run")) if "dry_run" in existing else None,
            updated_at=existing.get("updated_at") if isinstance(existing.get("updated_at"), str) else None,
            trending_topics=existing.get("trending_topics", []) if isinstance(existing.get("trending_topics"), list) else [],
        )

    result = youtube.update_video_metadata(video_id)
    store.mark(video_id, result.__dict__)
    return _to_response(result)


def extract_video_id(payload: bytes) -> Optional[str]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return None
    video_id = root.findtext(".//yt:videoId", namespaces=YOUTUBE_XML_NAMESPACES)
    if video_id:
        return video_id.strip()
    return None


def _to_response(result: UpdateResult) -> ProcessResponse:
    return ProcessResponse(
        status="updated" if not result.dry_run else "dry_run",
        video_id=result.video_id,
        title=result.title,
        dry_run=result.dry_run,
        updated_at=result.updated_at,
        trending_topics=result.trending_topics,
    )

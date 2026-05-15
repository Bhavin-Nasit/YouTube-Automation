# YouTube Metadata Automation

A Render-ready Python service that updates YouTube video descriptions and tags after an upload. It keeps your configured defaults, enriches them with current YouTube trending-video data, and then updates the existing video metadata through the YouTube Data API.

## What it does

- Receives YouTube upload notifications through a `/youtube/webhook` endpoint.
- Extracts the uploaded video ID from the YouTube notification payload.
- Reads your default description, tags, and hashtags from environment variables.
- Pulls current `mostPopular` YouTube videos for your configured region/category.
- Adds frequent trending tags and title keywords to your defaults.
- Updates only the uploaded video's existing description and tags while preserving the title and category.
- Tracks processed video IDs so repeated webhook deliveries do not keep rewriting the same video unless you force an update.

## Render deployment

1. Create a new Render Blueprint from this repository or create a Python web service manually.
2. Use `render.yaml` for the build and start commands.
3. Add the secret environment variables shown in `.env.example`.
4. Deploy. When `AUTO_SUBSCRIBE_ON_STARTUP=true`, the app requests YouTube upload webhook subscription during startup.

Render start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```


For a full step-by-step guide to every Render, Google Cloud, OAuth, YouTube, and metadata value, see [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md).

## Required environment variables

| Variable | Purpose |
| --- | --- |
| `BASE_URL` | Public Render URL, for example `https://your-app.onrender.com`. |
| `WEBHOOK_SECRET` | Long random secret added to YouTube webhook callback URLs. |
| `ADMIN_TOKEN` | Bearer token required for admin endpoints. |
| `YOUTUBE_CHANNEL_ID` | Channel ID to monitor. |
| `YOUTUBE_CLIENT_ID` | Google OAuth client ID. |
| `YOUTUBE_CLIENT_SECRET` | Google OAuth client secret. |
| `YOUTUBE_REFRESH_TOKEN` | OAuth refresh token with YouTube scope. |
| `DEFAULT_DESCRIPTION` | Description template. Supports `{title}`, `{video_id}`, `{trending_topics}`, and `{trending_hashtags}`. |
| `DEFAULT_TAGS` | Comma-separated default tags applied first. |
| `DEFAULT_HASHTAGS` | Comma-separated hashtags appended to the description. |

## Optional environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `YOUTUBE_UPLOADS_PLAYLIST_ID` | empty | Optional uploads playlist ID. If empty, the app resolves it from the channel. |
| `AUTO_SUBSCRIBE_ON_STARTUP` | `true` | Requests YouTube webhook subscription during app startup. |
| `ENABLE_TRENDING_ENRICHMENT` | `true` | Enables trending-video enrichment. |
| `TRENDING_REGION_CODE` | `US` | Region used for YouTube `mostPopular` data. |
| `TRENDING_VIDEO_CATEGORY_ID` | empty | Optional YouTube video category ID for trending data. |
| `TRENDING_LIMIT` | `15` | Number of trending videos to inspect. |
| `TRENDING_TAG_LIMIT` | `12` | Maximum trending tags to add. |
| `TRENDING_TITLE_KEYWORD_LIMIT` | `8` | Maximum trending title keywords to add. |
| `MAX_TAGS` | `45` | Maximum final YouTube tags sent to the API. |
| `PROCESSED_STORE_PATH` | `data/processed_videos.json` | JSON file used to prevent duplicate updates. |
| `DRY_RUN` | `false` | Builds metadata without sending the YouTube update. |

## OAuth note

YouTube channel updates require channel-owner OAuth. Service accounts cannot update a normal YouTube channel's video metadata. To avoid exposing secrets, store the resulting refresh token only in Render environment variables.

Helpers are included for generating a refresh token:

```bash
YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... python scripts/print_auth_url.py
GOOGLE_AUTH_CODE=... YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... python scripts/exchange_auth_code.py
```

## Admin endpoints

All admin endpoints require this header:

```text
Authorization: Bearer $ADMIN_TOKEN
```

### Subscribe or renew YouTube notifications

```bash
curl -X POST "$BASE_URL/admin/subscribe" -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Process the latest upload manually

```bash
curl -X POST "$BASE_URL/admin/process" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### Process a specific video manually

```bash
curl -X POST "$BASE_URL/admin/process" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"video_id":"VIDEO_ID","force":true}'
```

## Google free infrastructure option

This app is Render-first, but it is portable to Google Cloud Run because it is a standard ASGI Python service. If you later want Google-native hosting, add a Dockerfile and deploy the same app to Cloud Run. Cloud Run plus Secret Manager and Firestore would remove the local JSON processed-video file and keep the service serverless.

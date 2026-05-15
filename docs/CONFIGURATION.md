# Configuration Guide

This guide explains every value you need to configure in Render and how to get it. Keep all real values in Render environment variables only. Do not commit `.env` files or secrets to GitHub.

## Quick checklist

| Step | What you configure | Where you get it |
| --- | --- | --- |
| 1 | `BASE_URL` | Your Render service URL after deployment. |
| 2 | `WEBHOOK_SECRET` | Generate a long random string. Render can generate this for you from `render.yaml`. |
| 3 | `ADMIN_TOKEN` | Generate a different long random string. Render can generate this for you from `render.yaml`. |
| 4 | `YOUTUBE_CHANNEL_ID` | YouTube Studio or your channel URL/source page. |
| 5 | `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` | Google Cloud OAuth client. |
| 6 | `YOUTUBE_REFRESH_TOKEN` | Generated once with the helper scripts after approving channel access. |
| 7 | `DEFAULT_DESCRIPTION`, `DEFAULT_TAGS`, `DEFAULT_HASHTAGS` | Your own reusable metadata defaults. |
| 8 | Trending settings | Optional tuning values for region/category/limits. |

## Render configuration

Deploy this repository as a Render Blueprint or Python web service. The included `render.yaml` sets the Python runtime, build command, start command, health check path, and non-secret defaults.

Required Render settings:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

After Render creates the service, copy the public service URL into:

```text
BASE_URL=https://your-render-service.onrender.com
```

Do not include a trailing slash.

## Google Cloud setup

### 1. Create or choose a Google Cloud project

1. Open Google Cloud Console.
2. Create a new project or select an existing project dedicated to this automation.
3. Make sure billing/quota is available if Google asks for project setup. The YouTube Data API has a daily quota, and this app uses very little quota per upload.

### 2. Enable YouTube Data API v3

1. In Google Cloud Console, go to **APIs & Services**.
2. Open **Library**.
3. Search for **YouTube Data API v3**.
4. Click **Enable**.

### 3. Configure OAuth consent screen

1. Go to **APIs & Services > OAuth consent screen**.
2. Choose the user type available to your account.
3. Add an app name, support email, and developer contact email.
4. Add yourself as a test user if your app is in testing mode.
5. Add the YouTube scope used by this app:

```text
https://www.googleapis.com/auth/youtube
```

This scope is needed because the app updates video metadata on your channel.

### 4. Create OAuth client credentials

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Choose **Desktop app** for the helper-script flow.
4. Copy the generated client ID and client secret into Render:

```text
YOUTUBE_CLIENT_ID=your-client-id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=your-client-secret
```

## Getting the YouTube refresh token

YouTube metadata updates require OAuth approval from the channel owner. A normal service account cannot update videos on a regular YouTube channel.

Run these commands on your local machine, not in Render:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
YOUTUBE_CLIENT_ID='your-client-id.apps.googleusercontent.com' \
YOUTUBE_CLIENT_SECRET='your-client-secret' \
python scripts/print_auth_url.py
```

Open the printed URL in a browser while signed in as the YouTube channel owner. Approve access. Copy the returned authorization code, then run:

```bash
GOOGLE_AUTH_CODE='paste-the-code-here' \
YOUTUBE_CLIENT_ID='your-client-id.apps.googleusercontent.com' \
YOUTUBE_CLIENT_SECRET='your-client-secret' \
python scripts/exchange_auth_code.py
```

Copy the printed value into Render:

```text
YOUTUBE_REFRESH_TOKEN=the-refresh-token-from-the-script
```

## Getting the YouTube channel ID

Use one of these methods:

### Method A: YouTube Studio

1. Open YouTube Studio.
2. Go to **Settings > Channel > Advanced settings**.
3. Copy the **Channel ID**.

### Method B: Channel source page

1. Open your YouTube channel page in a browser.
2. View page source.
3. Search for `channelId`.
4. Copy the value that starts with `UC...`.

Put it in Render:

```text
YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxxxxxx
```

## Metadata defaults

The app always starts with your defaults and then adds trending enrichment.

### `DEFAULT_DESCRIPTION`

Supports these placeholders:

| Placeholder | Meaning |
| --- | --- |
| `{title}` | Current YouTube video title. |
| `{video_id}` | Current video ID. |
| `{trending_topics}` | Comma-separated trending topics found from YouTube most-popular data. |
| `{trending_hashtags}` | Space-separated trending hashtags generated from trending topics. |

Example:

```text
DEFAULT_DESCRIPTION=Thanks for watching {title}!\n\nSubscribe for more videos.\n\nTrending now: {trending_topics}\n{trending_hashtags}
```

### `DEFAULT_TAGS`

Comma-separated list. Defaults are kept first in the final tags list.

```text
DEFAULT_TAGS=my channel name,main niche,brand keyword,video topic
```

### `DEFAULT_HASHTAGS`

Comma-separated list. These are appended to the description before trending hashtags.

```text
DEFAULT_HASHTAGS=#MyChannel,#Subscribe,#MyNiche
```

## Trending enrichment settings

| Variable | Suggested value | Notes |
| --- | --- | --- |
| `ENABLE_TRENDING_ENRICHMENT` | `true` | Turn off only if you want defaults without trending additions. |
| `TRENDING_REGION_CODE` | `US` | Use your target audience country, for example `IN`, `GB`, `CA`, or `US`. |
| `TRENDING_VIDEO_CATEGORY_ID` | empty | Optional. Leave empty for all categories, or set a category ID if you want niche-specific trending videos. |
| `TRENDING_LIMIT` | `15` | Number of trending videos to inspect. |
| `TRENDING_TAG_LIMIT` | `12` | Maximum trending tags to add. |
| `TRENDING_TITLE_KEYWORD_LIMIT` | `8` | Maximum keywords extracted from trending titles. |
| `MAX_TAGS` | `45` | Final tag count cap. The app also keeps YouTube's total tag character limit in mind. |

Common YouTube category IDs:

| Category | ID |
| --- | --- |
| Film & Animation | `1` |
| Autos & Vehicles | `2` |
| Music | `10` |
| Pets & Animals | `15` |
| Sports | `17` |
| Travel & Events | `19` |
| Gaming | `20` |
| People & Blogs | `22` |
| Comedy | `23` |
| Entertainment | `24` |
| News & Politics | `25` |
| Howto & Style | `26` |
| Education | `27` |
| Science & Technology | `28` |

## Security settings

Use different random values for both of these:

```text
WEBHOOK_SECRET=long-random-secret-for-youtube-callback-url
ADMIN_TOKEN=long-random-secret-for-admin-api
```

You can generate a local random value with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Render can also generate these automatically because `render.yaml` uses `generateValue` for both values.

## How updates happen after deployment

1. Render starts the app.
2. If `AUTO_SUBSCRIBE_ON_STARTUP=true`, the app requests a YouTube upload-notification subscription.
3. When you upload a video, YouTube sends a notification to `/youtube/webhook`.
4. The app verifies the webhook secret.
5. The app extracts the video ID.
6. The app fetches the current video snippet.
7. The app fetches trending videos for your configured region/category.
8. The app builds the final description and tags from your defaults plus trending data.
9. The app updates the existing video description and tags.
10. The app records the video ID so duplicate notifications do not keep updating it.

## Manual update commands

Use these if you want to test or force an update.

Process latest upload:

```bash
curl -X POST "$BASE_URL/admin/process" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

Process a specific video:

```bash
curl -X POST "$BASE_URL/admin/process" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"video_id":"VIDEO_ID","force":true}'
```

Renew YouTube webhook subscription:

```bash
curl -X POST "$BASE_URL/admin/subscribe" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Recommended first deployment values

```text
AUTO_SUBSCRIBE_ON_STARTUP=true
ENABLE_TRENDING_ENRICHMENT=true
TRENDING_REGION_CODE=US
TRENDING_VIDEO_CATEGORY_ID=
TRENDING_LIMIT=15
TRENDING_TAG_LIMIT=12
TRENDING_TITLE_KEYWORD_LIMIT=8
MAX_TAGS=45
DRY_RUN=true
```

Start with `DRY_RUN=true` for the first deployment to verify logs and responses. After confirming the generated metadata looks right, set:

```text
DRY_RUN=false
```

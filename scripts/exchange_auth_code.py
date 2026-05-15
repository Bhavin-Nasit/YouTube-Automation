from __future__ import annotations

import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]


def main() -> None:
    code = os.environ["GOOGLE_AUTH_CODE"]
    client_config = {
        "installed": {
            "client_id": os.environ["YOUTUBE_CLIENT_ID"],
            "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    flow.fetch_token(code=code)
    print("YOUTUBE_REFRESH_TOKEN=" + flow.credentials.refresh_token)


if __name__ == "__main__":
    main()

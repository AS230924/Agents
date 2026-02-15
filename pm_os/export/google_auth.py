"""
Shared Google API authentication.

Supports two modes:
  1. Service account — set GOOGLE_SERVICE_ACCOUNT_FILE env var
  2. OAuth2 user credentials — uses credentials.json + token.json flow

The auth module provides a single get_credentials() call that returns
google.oauth2.credentials.Credentials usable by both Docs and Sheets APIs.
"""

import json
import logging
import os

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def get_credentials():
    """
    Return Google API credentials.

    Checks in order:
      1. GOOGLE_SERVICE_ACCOUNT_FILE env var (service account JSON key)
      2. GOOGLE_CREDENTIALS_JSON env var (inline service account JSON)
      3. OAuth2 flow via credentials.json / token.json in working dir
    """
    # 1. Service account from file path
    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_file:
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            sa_file, scopes=SCOPES
        )
        log.info("Authenticated via service account file: %s", sa_file)
        return creds

    # 2. Service account from inline JSON
    sa_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if sa_json:
        from google.oauth2 import service_account

        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
        log.info("Authenticated via inline service account JSON")
        return creds

    # 3. OAuth2 user flow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = os.environ.get("GOOGLE_TOKEN_FILE", "token.json")
    creds_path = os.environ.get("GOOGLE_OAUTH_CREDENTIALS", "credentials.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"No Google credentials found. Set GOOGLE_SERVICE_ACCOUNT_FILE, "
                    f"GOOGLE_CREDENTIALS_JSON, or place OAuth credentials at {creds_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())
        log.info("OAuth2 token saved to %s", token_path)

    return creds

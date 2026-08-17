"""
Handles Google sign-in and reading/writing activity data to a Google Sheet.

First-time setup required (one-time, per developer/user):
  1. Go to https://console.cloud.google.com and create (or pick) a project.
  2. Enable the "Google Sheets API" and "Google Drive API" for that project.
  3. Configure the OAuth consent screen (External is fine; add your own
     Google account under "Test users" while the app is unverified).
  4. Create Credentials -> OAuth client ID -> Application type: Desktop app.
  5. Download the JSON file, rename it to credentials.json, and place it
     in the same folder as main.py.

After that, the app handles login itself: the first time it runs (or any
time token.json is missing/invalid), it opens a browser window for you to
sign in and consent. The resulting token is cached in token.json so you
won't need to log in again on future runs.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Sheets: read/write activity rows. Drive (file scope only): find/create
# just the one spreadsheet this app owns -- it can't see any other files
# in the user's Drive.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

SPREADSHEET_NAME = "Activity Tracker Data"
SHEET_TITLE = "Activities"
DATA_RANGE = f"{SHEET_TITLE}!A2:C"
HEADER_RANGE = f"{SHEET_TITLE}!A1:C1"
APPEND_RANGE = f"{SHEET_TITLE}!A:C"


class GoogleAuthError(Exception):
    """Raised when sign-in can't proceed (e.g. missing credentials.json)."""


# ----------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------
def load_saved_credentials():
    """Return valid Credentials from token.json (refreshing if needed), or None."""
    if not os.path.exists(TOKEN_PATH):
        return None

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
            return creds
        except Exception:
            return None

    return None


def login_with_browser():
    """
    Run the OAuth consent flow in the user's default browser.
    Blocks until the user finishes (or closes) the browser step.
    Call this off the UI thread -- it's a blocking network call.
    """
    if not os.path.exists(CREDENTIALS_PATH):
        raise GoogleAuthError(
            "Missing credentials.json.\n\n"
            "Create an OAuth Client ID (Desktop app) in Google Cloud Console, "
            "enable the Sheets and Drive APIs, and download it as "
            "'credentials.json' next to main.py. See the comment at the top "
            "of google_backend.py for step-by-step instructions."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    return creds


def logout():
    """Forget the cached login so the next launch asks the user to sign in again."""
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)


def _save_credentials(creds):
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


# ----------------------------------------------------------------------
# Sheet setup
# ----------------------------------------------------------------------
def _sheets_service(creds):
    return build("sheets", "v4", credentials=creds)


def _drive_service(creds):
    return build("drive", "v3", credentials=creds)


def get_or_create_spreadsheet(creds):
    """Find this app's spreadsheet in Drive, or create it (with headers) if missing."""
    drive_service = _drive_service(creds)

    results = drive_service.files().list(
        q=(
            f"name='{SPREADSHEET_NAME}' "
            "and mimeType='application/vnd.google-apps.spreadsheet' "
            "and trashed=false"
        ),
        spaces="drive",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    sheets_service = _sheets_service(creds)
    spreadsheet = sheets_service.spreadsheets().create(
        body={
            "properties": {"title": SPREADSHEET_NAME},
            "sheets": [{"properties": {"title": SHEET_TITLE}}],
        },
        fields="spreadsheetId",
    ).execute()
    spreadsheet_id = spreadsheet["spreadsheetId"]

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=HEADER_RANGE,
        valueInputOption="RAW",
        body={"values": [["ID", "Activity", "Date"]]},
    ).execute()

    return spreadsheet_id


# ----------------------------------------------------------------------
# Data operations
# ----------------------------------------------------------------------
def read_activities(creds, spreadsheet_id):
    """Return rows as [[id, name, date], ...] in the order they appear in the sheet."""
    service = _sheets_service(creds)
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=DATA_RANGE
    ).execute()
    return result.get("values", [])


def append_activity(creds, spreadsheet_id, name, date):
    service = _sheets_service(creds)

    existing = read_activities(creds, spreadsheet_id)
    existing_ids = [int(row[0]) for row in existing if row and str(row[0]).isdigit()]
    next_id = max(existing_ids) + 1 if existing_ids else 1

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=APPEND_RANGE,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [[str(next_id), name, date]]},
    ).execute()


def delete_activity_row(creds, spreadsheet_id, sheet_row_number):
    """sheet_row_number is 1-based, counting the header row as row 1."""
    service = _sheets_service(creds)
    sheet_meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = sheet_meta["sheets"][0]["properties"]["sheetId"]

    requests = [{
        "deleteDimension": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "ROWS",
                "startIndex": sheet_row_number - 1,
                "endIndex": sheet_row_number,
            }
        }
    }]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()


def clear_all_activities(creds, spreadsheet_id):
    service = _sheets_service(creds)
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=DATA_RANGE
    ).execute()

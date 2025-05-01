import json
from datetime import datetime
from pathlib import Path
import os

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths and constants
LOG_PATH = Path("analytics/usage-events.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

GOOGLE_CREDS_PATH = os.getenv("GOOGLE_SHEETS_CREDS_PATH")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

def log_usage_event(user_id, url, cuisine=None, meal_format=None):
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "event": "recipe_shared",
        "url": url,
        "cuisine": cuisine or "unknown",
        "meal_format": meal_format or "unknown"
    }

    # Log locally to JSONL
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")

    # Also send to Google Sheet
    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
        sheet.append_row([
            event["timestamp"],
            event["user_id"],
            event["url"],
            event["cuisine"],
            event["meal_format"]
        ])
    except Exception as e:
        print(f"[Analytics] Google Sheets logging failed: {e}")
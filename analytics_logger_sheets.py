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
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

def log_usage_event(user_id, url, cuisine=None, meal_format=None, tags=None):
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "event": "recipe_shared",
        "url": url,
        "cuisine": cuisine or "unknown",
        "meal_format": meal_format or "unknown",
        "tags": tags or []
    }
    print(f"[Analytics] Logging event: {event}")

    # Log locally to JSONL
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")

    # Also send to Google Sheet
    try:
        print(f"[Analytics] Attempting to use Google creds from: {GOOGLE_CREDS_PATH}")
        print(f"[DEBUG] Verifying path: {GOOGLE_CREDS_PATH}")
        with open(GOOGLE_CREDS_PATH, 'r') as f:
            creds_data = json.load(f)
            print(f"[DEBUG] project_id: {creds_data['project_id']}")
        print(f"[Analytics] Using Google Sheet ID: {GOOGLE_SHEET_ID}")
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDS_PATH,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]        )
        print(f"[Analytics] Credentials loaded successfully.")
        print(f"[DEBUG] Service account: {creds.service_account_email}")
        gc = gspread.authorize(creds)
        print(f"[Analytics] gspread client authorized.")
        sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
        print(f"[Analytics] Sheet opened: {sheet.title}")
        print(f"[Analytics] Successfully opened sheet. Appending row...")
        sheet.append_row([
            event["timestamp"],
            event["user_id"],
            event["url"],
            event["cuisine"],
            event["meal_format"],
            ", ".join(event["tags"])
        ])
        print(f"[Analytics] Row appended successfully.")
    except Exception as e:
        import traceback
        print(f"[Analytics] Google Sheets logging failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Example test run
    log_usage_event(
        user_id="test_user",
        url="https://www.instagram.com/reel/test_recipe/",
        cuisine="mexican",
        meal_format="reel"
    )
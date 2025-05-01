import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("analytics/usage-events.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_usage_event(user_id, url, cuisine=None, meal_format=None):
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "event": "recipe_shared",
        "url": url,
        "cuisine": cuisine or "unknown",
        "meal_format": meal_format or "unknown"
    }

    with LOG_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")
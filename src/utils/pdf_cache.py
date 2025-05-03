import json
from pathlib import Path

CACHE_PATH = Path("analytics/pdf_cache.json")
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_pdf_cache():
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_pdf_cache(data):
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
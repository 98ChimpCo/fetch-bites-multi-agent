import json
import os
from pathlib import Path
from datetime import datetime
import hashlib

CACHE_PATH = Path("analytics/pdf_cache.json")
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
LAYOUT_VERSION = "v1"  # bump this when PDF template changes

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

def get_post_hash(caption: str, creator_handle: str, layout_version: str) -> str:
    identifier = (creator_handle.strip() + caption.strip() + layout_version.strip()).encode("utf-8")
    return hashlib.sha256(identifier).hexdigest()

class PDFCache:
    def __init__(self):
        self.cache = load_pdf_cache()

    def get(self, post_hash):
        entry = self.cache.get(post_hash)
        if entry and entry.get("layout_version") == LAYOUT_VERSION:
            return entry["extracted_text"]
        return None

    def set(self, post_hash, user_id, caption, extracted_text, pdf_path):
        self.cache[post_hash] = {
            "user_id": user_id,
            "caption": caption,
            "recipe": extracted_text,
            "pdf_path": pdf_path,
            "layout_version": LAYOUT_VERSION,
            "cached_at": datetime.utcnow().isoformat()
        }
        save_pdf_cache(self.cache)

    def exists(self, post_hash: str) -> bool:
        entry = self.cache.get(post_hash)
        return entry is not None and entry.get("layout_version") == LAYOUT_VERSION

    def load_pdf_path(self, post_hash):
        entry = self.cache.get(post_hash)
        if entry and entry.get("layout_version") == LAYOUT_VERSION:
            path = entry.get("pdf_path")
            if path and isinstance(path, str):
                return path
        return None

    def save(self):
        save_pdf_cache(self.cache)

    def load_recipe_details(self, post_hash):
        entry = self.cache.get(post_hash)
        if entry and entry.get("layout_version") == LAYOUT_VERSION:
            return entry.get("recipe")
        return None
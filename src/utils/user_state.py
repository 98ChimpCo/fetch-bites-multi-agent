"""
Handles onboarding message flow for new users.
"""

import json
import os
from datetime import datetime
import logging

USER_MEMORY_FILE = "user_memory.json"
STATE_NEW = "new"

logger = logging.getLogger(__name__)

WELCOME_MESSAGES = [
    "👋 Hey! I’m your recipe assistant. If you send me a shared recipe post, I’ll extract the full recipe and send you back a clean PDF copy.",
    "📌 Just paste or forward any Instagram recipe post. I’ll do the rest — no sign-up needed.",
    "✨ Want your recipes saved or emailed to you? Just say “email me” and I’ll set that up."
]

class UserStateManager:
    def __init__(self, filepath=USER_MEMORY_FILE):
        self.filepath = filepath
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def save_state(self):
        with open(self.filepath, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_user_state(self, user_id):
        return self.data.get(user_id, {"state": STATE_NEW})

    def update_user_state(self, user_id, new_state):
        self.data[user_id] = {
            **self.get_user_state(user_id),
            **new_state,
            "last_updated": datetime.utcnow().isoformat()
        }
        self.save_state()

class OnboardingManager:
    def __init__(self, user_state_manager: UserStateManager):
        self.user_state_manager = user_state_manager

    def should_onboard(self, user_id: str) -> bool:
        state = self.user_state_manager.get_user_state(user_id)
        return state.get("state") == STATE_NEW

    def mark_onboarded(self, user_id: str):
        self.user_state_manager.update_user_state(user_id, {"state": "awaiting_url"})

    def get_onboarding_messages(self) -> list[str]:
        return WELCOME_MESSAGES
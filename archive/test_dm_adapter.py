# test_dm_adapter.py

from archive.instagram_message_adapter_vision_fixed_v2 import InstagramMessageAdapterVision
import os
from dotenv import load_dotenv

load_dotenv()  # Load credentials from .env file

def dummy_callback(sender, message):
    print(f"Message from {sender}: {message}")

if __name__ == "__main__":
    print("Adapter created ✅")
    adapter = InstagramMessageAdapterVision(
        username=os.getenv("IG_USERNAME"),
        password=os.getenv("IG_PASSWORD"),
        message_callback=dummy_callback,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        headless=False
    )

    print("Starting adapter... (press Ctrl+C to quit)")
    print("Calling start_monitoring()...")
    adapter.start_monitoring(interval_seconds=10)
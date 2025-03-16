# In instagram_message_adapter.py or a separate file like utils/message_tracker.py
import json
import os
import logging

logger = logging.getLogger(__name__)

class MessageTracker:
    """Tracks which messages have been processed to avoid duplication."""
    
    def __init__(self, storage_path="data/processed_messages.json"):
        self.storage_path = storage_path
        self.processed_messages = self._load_processed_messages()
        
    def _load_processed_messages(self):
        """Load the set of processed message IDs from storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.error(f"Error loading processed messages: {str(e)}")
            return set()
    
    def _save_processed_messages(self):
        """Save the set of processed message IDs to storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(list(self.processed_messages), f)
        except Exception as e:
            logger.error(f"Error saving processed messages: {str(e)}")
    
    def is_processed(self, message_id):
        """Check if a message has already been processed."""
        return message_id in self.processed_messages
    
    def mark_processed(self, message_id):
        """Mark a message as processed."""
        self.processed_messages.add(message_id)
        self._save_processed_messages()
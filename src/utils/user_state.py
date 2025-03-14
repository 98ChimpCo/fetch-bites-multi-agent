"""
User state management for the Instagram Recipe Agent.
Tracks user interaction state and saves user information.
"""

import json
import os
import re
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# User interaction states
STATE_NEW = "new"  # New user, no interaction yet
STATE_AWAITING_EMAIL = "awaiting_email"  # Waiting for user to provide email
STATE_AWAITING_URL = "awaiting_url"  # Waiting for user to provide Instagram URL
STATE_PROCESSING = "processing"  # Processing a recipe request

class UserStateManager:
    """Manages user state and information for the Instagram Recipe Agent."""
    
    def __init__(self, data_dir: str = "data/users"):
        """Initialize the user state manager.
        
        Args:
            data_dir: Directory to store user data files
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.user_states = {}  # In-memory cache of user states
        
    def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """Get the current state for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            User state dictionary
        """
        # Check in-memory cache first
        if user_id in self.user_states:
            return self.user_states[user_id]
            
        # Try to load from file
        user_file = os.path.join(self.data_dir, f"{user_id}.json")
        if os.path.exists(user_file):
            try:
                with open(user_file, 'r') as f:
                    user_state = json.load(f)
                self.user_states[user_id] = user_state
                return user_state
            except Exception as e:
                logger.error(f"Error loading user state for {user_id}: {str(e)}")
        
        # Return default state for new users
        default_state = {
            "state": STATE_NEW,
            "email": None,
            "pending_url": None,
            "processed_posts": []
        }
        self.user_states[user_id] = default_state
        return default_state
    
    def update_user_state(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user's state.
        
        Args:
            user_id: Unique identifier for the user
            updates: Dictionary of fields to update
            
        Returns:
            Updated user state
        """
        user_state = self.get_user_state(user_id)
        user_state.update(updates)
        self.user_states[user_id] = user_state
        
        # Save to file
        user_file = os.path.join(self.data_dir, f"{user_id}.json")
        try:
            with open(user_file, 'w') as f:
                json.dump(user_state, f)
        except Exception as e:
            logger.error(f"Error saving user state for {user_id}: {str(e)}")
            
        return user_state
    
    def is_valid_email(self, email: str) -> bool:
        """Check if an email address is valid.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Simple email validation regex
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))
    
    def is_instagram_post_url(self, url: str) -> bool:
        """Check if a URL is a valid Instagram post URL or post content.
        
        Args:
            url: URL or content to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check for standard Instagram post URL
        standard_pattern = r'^https?://(www\.)?instagram\.com/p/[\w-]+/?.*$'
        if re.match(standard_pattern, url):
            return True
            
        # Check for Instagram username in the content (might be a shared post)
        instagram_username_pattern = r'@[\w\.]+\s+'
        if re.search(instagram_username_pattern, url):
            return True
            
        # Check for common Instagram patterns
        instagram_indicators = [
            'instagram.com', 
            'kauscooks',  # Add specific accounts you're interested in
            'reel',
            'story'
        ]
        
        if any(indicator in url.lower() for indicator in instagram_indicators):
            return True
                
        return False
    
    def add_processed_post(self, user_id: str, post_url: str, recipe_title: str) -> None:
        """Add a processed post to a user's history.
        
        Args:
            user_id: Unique identifier for the user
            post_url: Instagram post URL
            recipe_title: Title of the extracted recipe
        """
        user_state = self.get_user_state(user_id)
        processed_posts = user_state.get("processed_posts", [])
        processed_posts.append({
            "url": post_url,
            "title": recipe_title,
            "timestamp": import_datetime().now().isoformat()
        })
        self.update_user_state(user_id, {"processed_posts": processed_posts})


def import_datetime():
    """Import datetime module dynamically to avoid circular imports."""
    import datetime
    return datetime

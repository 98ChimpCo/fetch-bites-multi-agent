"""
Enhanced User state management for the Instagram Recipe Agent.
Tracks user interaction state and saves user information with improved email extraction.
"""

import json
import os
import re
import logging
from typing import Dict, Optional, Any, List

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
        """Check if the given string is a valid email address.
        
        Args:
            email: String to check
            
        Returns:
            True if valid email, False otherwise
        """
        # Trim whitespace and convert to lowercase
        if not isinstance(email, str):
            return False
            
        # First attempt to extract an email if the string contains other text
        extracted_email = self.extract_email_from_text(email)
        if extracted_email:
            email = extracted_email
        else:
            email = email.strip().lower()
        
        # Simple, permissive email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(email_pattern, email))
        
        # Debug logging
        logger.info(f"Validating email: '{email}' - Result: {is_valid}")
        
        return is_valid
    
    def extract_email_from_text(self, text: str) -> Optional[str]:
        """
        Extract email address from text that may contain other content.
        
        Args:
            text: Text that might contain an email address
            
        Returns:
            Extracted email address or None if not found
        """
        if not text or not isinstance(text, str):
            return None
            
        # Debug log
        logger.info(f"Trying to extract email from: '{text}'")
        
        # First try common email pattern
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, text)
        
        if email_matches:
            extracted = email_matches[0]
            logger.info(f"Found email via regex: {extracted}")
            return extracted
        
        # Clean up text - remove common UI elements
        cleaned_text = text.lower()
        ui_elements = [
            'react', 'reply', 'more', 'enter', 'send', 'close', 
            'password', 'login', 'save', 'forgot', 'phone number', 'username'
        ]
        
        for element in ui_elements:
            cleaned_text = cleaned_text.replace(element, ' ')
        
        # Remove any non-email characters and split by spaces
        words = re.split(r'[\s,;]+', cleaned_text)
        
        # Check each word for email pattern
        for word in words:
            if '@' in word and '.' in word and len(word) > 5:
                # Further clean the word in case there are still unwanted characters
                cleaned_word = re.sub(r'[^a-zA-Z0-9.@_+-]', '', word)
                
                # Validate the cleaned word
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', cleaned_word):
                    logger.info(f"Found email via word cleaning: {cleaned_word}")
                    return cleaned_word
        
        # Try extracting email parts around @ symbol
        at_index = text.find('@')
        if at_index != -1:
            # Look for a valid email around the @ symbol
            # Find start (working backwards from @)
            start_index = at_index
            while start_index > 0 and re.match(r'[a-zA-Z0-9._%+-]', text[start_index-1]):
                start_index -= 1
            
            # Find end (working forwards from @)
            end_index = at_index
            while end_index < len(text)-1 and re.match(r'[a-zA-Z0-9.-]', text[end_index+1]):
                end_index += 1
            
            # Find the domain end (looking for the '.' and valid TLD)
            while end_index < len(text)-1:
                if text[end_index] == '.':
                    # Found a dot, check for valid TLD length (2-6 chars)
                    potential_end = end_index + 1
                    while potential_end < len(text) and re.match(r'[a-zA-Z]', text[potential_end]):
                        potential_end += 1
                    
                    # If we found a valid TLD length, use this as our end
                    if 2 <= potential_end - (end_index + 1) <= 6:
                        end_index = potential_end
                        break
                
                end_index += 1
                if end_index >= len(text) or not re.match(r'[a-zA-Z0-9.-]', text[end_index]):
                    break
            
            # Extract the potential email and validate
            if start_index < at_index and end_index > at_index:
                potential_email = text[start_index:end_index]
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', potential_email):
                    logger.info(f"Found email via @ parsing: {potential_email}")
                    return potential_email
        
        # No valid email found
        logger.warning(f"No email extracted from: '{text}'")
        return None
    
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
            'hungry.happens',
            'reel',
            'story'
        ]
        
        if any(indicator in url.lower() for indicator in instagram_indicators):
            return True
                
        return False
    
    def extract_instagram_urls(self, text: str) -> List[str]:
        """
        Extract Instagram post URLs from text.
        
        Args:
            text: Text that might contain Instagram URLs
            
        Returns:
            List of extracted Instagram URLs
        """
        if not text or not isinstance(text, str):
            return []
        
        # Instagram post URL pattern
        instagram_url_pattern = r'https?://(www\.)?instagram\.com/p/[\w-]+/?[^\s]*'
        
        # Find all matching URLs
        urls = re.findall(instagram_url_pattern, text)
        
        # Return full URLs
        return [match for match in re.findall(instagram_url_pattern, text)]
    
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

import os
import json
import time
import logging
import re
from typing import Dict, Optional, List, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class UserStateManager:
    """
    Enhanced user state management with improved email extraction and persistence.
    """
    
    def __init__(self, data_dir: str = "data/users"):
        """
        Initialize user state manager.
        
        Args:
            data_dir (str): Directory for user state persistence
        """
        self.user_states = {}
        self.data_dir = data_dir
        
        # Create directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing user states
        self._load_user_states()
    
    def _get_user_file_path(self, user_id: str) -> str:
        """Get file path for user state file."""
        # Clean user_id to create a valid filename
        safe_user_id = re.sub(r'[^\w\-_.]', '_', user_id)
        return os.path.join(self.data_dir, f"{safe_user_id}.json")
    
    def _load_user_states(self):
        """Load all user states from disk."""
        try:
            # Get all JSON files in data directory
            for filename in os.listdir(self.data_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.data_dir, filename)
                    try:
                        with open(file_path, 'r') as f:
                            user_state = json.load(f)
                            user_id = user_state.get("user_id")
                            if user_id:
                                self.user_states[user_id] = user_state
                    except Exception as e:
                        logger.error(f"Error loading user state from {file_path}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error loading user states: {str(e)}")
    
    def _save_user_state(self, user_id: str):
        """Save user state to disk."""
        try:
            user_state = self.user_states.get(user_id)
            if user_state:
                file_path = self._get_user_file_path(user_id)
                with open(file_path, 'w') as f:
                    json.dump(user_state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user state for {user_id}: {str(e)}")
    
    def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """
        Get state for a user, creating new state if none exists.
        
        Args:
            user_id (str): User identifier
            
        Returns:
            Dict: User state data
        """
        if user_id not in self.user_states:
            # Initialize new user state
            self.user_states[user_id] = {
                "user_id": user_id,
                "state": "initial",
                "email": None,
                "recipe_url": None,
                "recipes": [],
                "preferences": {
                    "notification_frequency": "immediate"
                },
                "last_interaction": time.time(),
                "created_at": time.time()
            }
            self._save_user_state(user_id)
            
        return self.user_states[user_id]
    
    def update_user_state(self, user_id: str, updates: Dict[str, Any]):
        """
        Update state for a user.
        
        Args:
            user_id (str): User identifier
            updates (Dict): State updates to apply
        """
        # Get current state, creating if needed
        user_state = self.get_user_state(user_id)
        
        # Apply updates
        user_state.update(updates)
        
        # Always update last_interaction time
        user_state["last_interaction"] = time.time()
        
        # Save to disk
        self._save_user_state(user_id)
    
    def is_valid_email(self, email: str) -> bool:
        """
        Check if the given string is a valid email address.
        
        Args:
            email (str): Email address to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.match(pattern, email):
            return True
        return False
    
    def extract_email_from_text(self, text: str) -> Optional[str]:
        """
        Extract email from text with multiple approaches.
        
        Args:
            text (str): Text to extract email from
            
        Returns:
            str or None: Extracted email address or None if not found
        """
        logger.info(f"Trying to extract email from: '{text}'")
        
        # Clean text (remove extra spaces, line breaks)
        cleaned_text = text.strip()
        
        # Try regex pattern first
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, cleaned_text)
        if matches:
            return matches[0]
        
        # Try focusing on words with @ symbols
        words = cleaned_text.split()
        for word in words:
            if '@' in word and '.' in word:
                # Clean the word (remove punctuation at start/end)
                cleaned_word = word.strip('.,;:!?()[]{}\'\"')
                if re.match(email_pattern, cleaned_word):
                    return cleaned_word
        
        logger.warning(f"No email extracted from: '{text}'")
        return None
    
    def add_recipe(self, user_id: str, recipe_data: Dict[str, Any]):
        """
        Add a processed recipe to user's history.
        
        Args:
            user_id (str): User identifier
            recipe_data (Dict): Recipe data
        """
        user_state = self.get_user_state(user_id)
        
        # Add recipe if not already present
        recipe_url = recipe_data.get("source", {}).get("url")
        
        if recipe_url:
            # Check if recipe already exists
            exists = False
            for recipe in user_state.get("recipes", []):
                if recipe.get("source", {}).get("url") == recipe_url:
                    exists = True
                    break
            
            if not exists:
                # Add timestamp
                recipe_data["added_at"] = time.time()
                
                # Add to recipes list
                if "recipes" not in user_state:
                    user_state["recipes"] = []
                user_state["recipes"].append(recipe_data)
                
                # Save changes
                self._save_user_state(user_id)
    
    def get_user_recipes(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get list of user's processed recipes.
        
        Args:
            user_id (str): User identifier
            
        Returns:
            List[Dict]: List of recipe data
        """
        user_state = self.get_user_state(user_id)
        return user_state.get("recipes", [])
    
    def set_user_email(self, user_id: str, email: str) -> bool:
        """
        Set user's email address after validation.
        
        Args:
            user_id (str): User identifier
            email (str): Email address
            
        Returns:
            bool: True if email was valid and set, False otherwise
        """
        if self.is_valid_email(email):
            self.update_user_state(user_id, {"email": email})
            return True
        return False
    
    def get_user_email(self, user_id: str) -> Optional[str]:
        """
        Get user's email address.
        
        Args:
            user_id (str): User identifier
            
        Returns:
            str or None: User's email address or None if not set
        """
        user_state = self.get_user_state(user_id)
        return user_state.get("email")
    
    def set_user_preference(self, user_id: str, preference: str, value: Any):
        """
        Set a user preference.
        
        Args:
            user_id (str): User identifier
            preference (str): Preference name
            value (Any): Preference value
        """
        user_state = self.get_user_state(user_id)
        
        if "preferences" not in user_state:
            user_state["preferences"] = {}
            
        user_state["preferences"][preference] = value
        self._save_user_state(user_id)
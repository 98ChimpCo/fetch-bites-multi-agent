import os
import re
import logging
import time
from typing import Dict, List, Optional, Any, Callable

from src.utils.user_state_enhanced import UserStateManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class ConversationHandler:
    """
    Enhanced conversation handler with improved flow management and response generation.
    """
    
    def __init__(
        self, 
        user_state_manager: UserStateManager,
        send_message_callback: Callable[[str, str], bool]
    ):
        """
        Initialize conversation handler.
        
        Args:
            user_state_manager (UserStateManager): User state manager
            send_message_callback (callable): Callback for sending messages
        """
        self.user_state_manager = user_state_manager
        self.send_message_callback = send_message_callback
        
        # Define conversation flows - mapping state to handler methods
        self.state_handlers = {
            "initial": self._handle_initial_state,
            "awaiting_email": self._handle_awaiting_email_state,
            "processing_recipe": self._handle_processing_recipe_state,
            "completed": self._handle_completed_state
        }
        
        # Message templates
        self.templates = {
            "welcome": "👋 Hello there, food explorer! I'm Fetch Bites, your personal recipe assistant! 🥘\n\n"
                      "I can turn Instagram recipe posts into beautiful, printable recipe cards "
                      "delivered straight to your inbox! No more screenshots or manually typing out recipes.\n\n"
                      "Want to see what I can do? Just send me a link to an Instagram recipe post, "
                      "and I'll work my magic! ✨\n\n"
                      "Or type \"help\" to learn more about how I work.",
                      
            "help": "🍳 *How to Use Fetch Bites:*\n\n"
                   "1️⃣ Send me a link to an Instagram recipe post\n"
                   "2️⃣ I'll ask for your email address\n"
                   "3️⃣ I'll extract the recipe and send you a beautifully formatted PDF\n\n"
                   "You can also share posts directly with me from Instagram!\n\n"
                   "Type \"examples\" to see the kinds of recipes I can process.",
                   
            "examples": "I can process all kinds of recipes from Instagram posts, like:\n\n"
                       "🍝 Pasta dishes\n"
                       "🍗 Chicken recipes\n"
                       "🥗 Salads\n"
                       "🍰 Desserts\n\n"
                       "Just find a recipe post you like and send me the link!",
                       
            "email_request": "That recipe looks delicious! 😋 Before I can send you the recipe card...\n\n"
                            "📧 What email address should I send your recipe card to?\n"
                            "(Just type your email address)",
                            
            "invalid_email": "Hmm, that doesn't look like a valid email address. Could you please try again?\n\n"
                            "I need a valid email address to send you the recipe card.",
                            
            "processing": "Perfect! I'll send your recipe card to {email}.\n\n"
                         "Working on your recipe card now... ⏳",
                         
            "completion": "✨ Recipe card for \"{title}\" has been created and sent to your inbox!\n\n"
                          "Feel free to send me another recipe post anytime you want to save a recipe.\n\n"
                          "Happy cooking! 👨‍🍳👩‍🍳",
                          
            "no_recipe": "I couldn't find a recipe in that post. Could you try sharing a different post that contains "
                        "recipe details like ingredients and cooking instructions?",
                        
            "error": "I'm having some trouble processing that. Could you try again or send a different recipe post?"
        }
    
    def process_message(self, sender: str, content: str) -> Optional[str]:
        """
        Process an incoming message and generate a response.
        
        Args:
            sender (str): Message sender
            content (str): Message content
            
        Returns:
            str or None: Response message or None if no response needed
        """
        logger.info(f"Received message from {sender}: '{content}'")
        
        # Get current user state
        user_state = self.user_state_manager.get_user_state(sender)
        current_state = user_state.get("state", "initial")
        
        # Check for commands that override normal flow
        if content.lower().strip() in ["help", "/help"]:
            return self.templates["help"]
            
        if content.lower().strip() in ["examples", "/examples"]:
            return self.templates["examples"]
            
        if content.lower().strip() in ["reset", "/reset"]:
            self.user_state_manager.update_user_state(sender, {"state": "initial"})
            return "I've reset our conversation. What would you like to do now?"
        
        # Handle based on current state
        handler = self.state_handlers.get(current_state, self._handle_unknown_state)
        return handler(sender, content, user_state)
    
    def _handle_initial_state(self, sender: str, content: str, user_state: Dict[str, Any]) -> str:
        """Handle messages in initial state."""
        # Check if this is a greeting
        if self._is_greeting(content):
            return self.templates["welcome"]
        
        # Check if this is a recipe URL or contains a URL
        recipe_url = self._extract_url(content)
        if recipe_url:
            # Update state with recipe URL
            self.user_state_manager.update_user_state(sender, {
                "state": "awaiting_email",
                "recipe_url": recipe_url
            })
            return self.templates["email_request"]
        
        # Check if content might be recipe text directly
        if self._looks_like_recipe(content):
            # Update state with recipe content
            self.user_state_manager.update_user_state(sender, {
                "state": "awaiting_email",
                "recipe_content": content
            })
            return self.templates["email_request"]
        
        # Default response for initial state
        return self.templates["welcome"]
    
    def _handle_awaiting_email_state(self, sender: str, content: str, user_state: Dict[str, Any]) -> str:
        """Handle messages when awaiting email address."""
        # Try to extract email
        email = self.user_state_manager.extract_email_from_text(content)
        
        # If email found and valid
        if email and self.user_state_manager.is_valid_email(email):
            # Update state with email
            self.user_state_manager.update_user_state(sender, {
                "state": "processing_recipe",
                "email": email
            })
            
            # Return processing message
            return self.templates["processing"].format(email=email)
        else:
            # Invalid or no email found
            return self.templates["invalid_email"]
    
    def _handle_processing_recipe_state(self, sender: str, content: str, user_state: Dict[str, Any]) -> Optional[str]:
        """Handle messages when processing recipe."""
        # This would trigger recipe processing in a real implementation
        # For demo purposes, just transition to completed state
        self.user_state_manager.update_user_state(sender, {
            "state": "completed"
        })
        
        # Return completion message
        return self.templates["completion"].format(title="Delicious Recipe")
    
    def _handle_completed_state(self, sender: str, content: str, user_state: Dict[str, Any]) -> str:
        """Handle messages after recipe processing completed."""
        # Check if this is a new recipe URL
        recipe_url = self._extract_url(content)
        if recipe_url:
            # Start new recipe flow
            self.user_state_manager.update_user_state(sender, {
                "state": "awaiting_email",
                "recipe_url": recipe_url
            })
            return self.templates["email_request"]
        
        # Check if content might be a new recipe text
        if self._looks_like_recipe(content):
            # Start new recipe flow
            self.user_state_manager.update_user_state(sender, {
                "state": "awaiting_email",
                "recipe_content": content
            })
            return self.templates["email_request"]
        
        # Default response - offer to process another recipe
        return "Would you like to process another recipe? Just send me a link to an Instagram recipe post!"
    
    def _handle_unknown_state(self, sender: str, content: str, user_state: Dict[str, Any]) -> str:
        """Handle messages for unknown state."""
        # Reset to initial state
        self.user_state_manager.update_user_state(sender, {"state": "initial"})
        return self.templates["welcome"]
    
    def _is_greeting(self, content: str) -> bool:
        """Check if message is a greeting."""
        greetings = ["hello", "hi", "hey", "howdy", "hola", "good morning", "good afternoon", "good evening", "👋"]
        return any(greeting in content.lower() for greeting in greetings)
    
    def _extract_url(self, content: str) -> Optional[str]:
        """Extract URL from message content."""
        # Simple regex pattern for URLs
        url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
        
        # Find all URLs
        urls = re.findall(url_pattern, content)
        
        # Filter for Instagram URLs
        instagram_urls = [url for url in urls if "instagram.com" in url]
        
        # Return first Instagram URL if found
        if instagram_urls:
            return instagram_urls[0]
            
        # If no Instagram URL, return any URL
        if urls:
            return urls[0]
            
        return None
    
    def _looks_like_recipe(self, content: str) -> bool:
        """Check if content might be a recipe."""
        # Look for recipe indicators
        recipe_indicators = [
            r'\d+\s*(?:cup|cups|tbsp|tsp|tablespoon|teaspoon|oz|ounce|pound|lb|kg|g|gram|ml|liter|l)\b',  # Measurements
            r'ingredient[s]?',  # Ingredient mention
            r'instruction[s]?',  # Instruction mention
            r'step\s+\d+',  # Step references
            r'(?:pre-?heat|bake|cook|simmer|boil|fry|saute|roast|grill|mix|stir|blend|whisk)\b',  # Cooking verbs
            r'(?:oven|stove|pan|pot|bowl|mixer|blender)\b'  # Cooking tools
        ]
        
        # Check if content has multiple lines
        has_multiple_lines = content.count('\n') >= 3
        
        # Check if content is long enough
        is_long_enough = len(content.split()) >= 30
        
        # Check for recipe indicators
        has_indicators = False
        for pattern in recipe_indicators:
            if re.search(pattern, content, re.IGNORECASE):
                has_indicators = True
                break
        
        # Consider it a recipe if it has indicators and is either long or has multiple lines
        return has_indicators and (is_long_enough or has_multiple_lines)

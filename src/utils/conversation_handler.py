"""
Conversation handler for the Instagram Recipe Agent onboarding flow.
Manages the conversation flow and responses based on user input.
"""

import logging
import re
import os
import threading
import time
import traceback
from typing import Dict, Tuple, Optional

from src.agents.instagram_monitor import InstagramMonitor
from src.agents.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator
from src.agents.delivery_agent import DeliveryAgent
from src.utils.message_templates import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    EMAIL_REQUEST,
    EMAIL_CONFIRMATION,
    PROCESSING_COMPLETE,
    RETURNING_USER,
    INVALID_URL,
    EXTRACTION_ERROR,
    PROCESSING_ERROR,
    INVALID_EMAIL
)
from src.utils.user_state import UserStateManager, STATE_NEW, STATE_AWAITING_EMAIL, STATE_AWAITING_URL, STATE_PROCESSING

logger = logging.getLogger(__name__)

class ConversationHandler:
    """Handles the conversation flow for the Instagram Recipe Agent."""
    
    def __init__(
        self,
        user_state_manager: UserStateManager,
        instagram_monitor: InstagramMonitor,
        recipe_extractor: RecipeExtractor,
        pdf_generator: PDFGenerator,
        delivery_agent: DeliveryAgent
    ):
        """Initialize the conversation handler.
        
        Args:
            user_state_manager: User state manager instance
            instagram_monitor: Instagram monitor agent instance
            recipe_extractor: Recipe extractor agent instance
            pdf_generator: PDF generator agent instance
            delivery_agent: Delivery agent instance
        """
        self.user_state_manager = user_state_manager
        self.instagram_monitor = instagram_monitor
        self.recipe_extractor = recipe_extractor
        self.pdf_generator = pdf_generator
        self.delivery_agent = delivery_agent
        
    def handle_message(self, user_id: str, message: str) -> str:
        """Handle an incoming message from a user."""
        # Log the raw message for debugging
        logger.info(f"Received message from {user_id}: '{message}'")
        
        # Get current user state
        user_state = self.user_state_manager.get_user_state(user_id)
        current_state = user_state.get("state", STATE_NEW)
        
        # Check for command keywords regardless of state
        message_lower = message.lower().strip()
        
        # Help command
        if message_lower == "help":
            return HELP_MESSAGE
            
        # Process state-specific logic
        if current_state == STATE_NEW:
            # For new users, send welcome message if they don't provide a URL
            post_info = self._extract_instagram_post_info(message)
            if post_info:
                # User provided URL right away
                self.user_state_manager.update_user_state(user_id, {
                    "state": STATE_AWAITING_EMAIL,
                    "pending_url": message
                })
                return EMAIL_REQUEST
            else:
                # Update to awaiting URL state
                self.user_state_manager.update_user_state(user_id, {
                    "state": STATE_AWAITING_URL
                })
                return WELCOME_MESSAGE
                
        elif current_state == STATE_AWAITING_URL:
            # Expecting a URL
            if self.user_state_manager.is_instagram_post_url(message):
                # Valid URL provided
                if user_state.get("email"):
                    # User already has email, start processing
                    return self._process_recipe_request(user_id, message)
                else:
                    # Need email first
                    self.user_state_manager.update_user_state(user_id, {
                        "state": STATE_AWAITING_EMAIL,
                        "pending_url": message
                    })
                    return EMAIL_REQUEST
            else:
                # Invalid URL
                return INVALID_URL
                
        elif current_state == STATE_AWAITING_EMAIL:
            # First, try with the raw message
            if self.user_state_manager.is_valid_email(message):
                email = message
            else:
                # Enhanced email extraction
                extracted_email = self._extract_email_from_message(message)
                if not extracted_email:
                    # No valid email found
                    return INVALID_EMAIL
                email = extracted_email
                logger.info(f"Successfully extracted email: {email}")
            
            # Process with the extracted email
            pending_url = user_state.get("pending_url")
            
            self.user_state_manager.update_user_state(user_id, {
                "email": email
            })
            
            # Send confirmation
            confirmation = EMAIL_CONFIRMATION.format(email=email)
            
            if pending_url:
                # Process the pending URL
                self.user_state_manager.update_user_state(user_id, {
                    "state": STATE_PROCESSING
                })
                
                # Process asynchronously and return confirmation for now
                self._process_recipe_request_async(user_id, pending_url)
                return confirmation
            else:
                # No pending URL, await one
                self.user_state_manager.update_user_state(user_id, {
                    "state": STATE_AWAITING_URL
                })
                return confirmation + "\n\nNow, send me an Instagram recipe post to try it out!"
        
        # Default response for any other state or unrecognized input
        if self.user_state_manager.is_instagram_post_url(message):
            return self._process_recipe_request(user_id, message)
        else:
            # Update to awaiting URL state if in an unexpected state
            self.user_state_manager.update_user_state(user_id, {
                "state": STATE_AWAITING_URL
            })
            return INVALID_URL

    def _extract_email_from_message(self, message: str) -> Optional[str]:
        """
        Advanced email extraction from message text.
        
        Args:
            message: Raw message text that might contain an email
            
        Returns:
            Extracted email or None if no valid email found
        """
        if not message:
            return None
        
        # Log the raw message for debugging
        logger.info(f"Extracting email from: '{message}'")
        
        # Method 1: Use regex to find email patterns
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, message)
        
        if email_matches:
            for match in email_matches:
                if self.user_state_manager.is_valid_email(match):
                    logger.info(f"Found email via regex: {match}")
                    return match
        
        # Method 2: Clean up text and split into words
        cleaned_text = message.lower()
        # Remove common UI elements and punctuation
        ui_elements = ['react', 'reply', 'more', 'enter', 'send', 'close']
        
        for element in ui_elements:
            cleaned_text = cleaned_text.replace(element, ' ')
        
        # Replace non-email punctuation with spaces
        cleaned_text = re.sub(r'[^\w\s@.-]', ' ', cleaned_text)
        
        # Split into words and examine each
        words = re.split(r'\s+', cleaned_text)
        
        for word in words:
            # Look for words with @ and . which are common in emails
            if '@' in word and '.' in word:
                # Further clean the word
                clean_word = re.sub(r'[^a-zA-Z0-9.@_+-]', '', word)
                if self.user_state_manager.is_valid_email(clean_word):
                    logger.info(f"Found email via word cleaning: {clean_word}")
                    return clean_word
        
        # Method 3: Try to extract just the email portion from longer text
        at_index = message.find('@')
        
        if at_index != -1:
            # Look for a valid email around the @ symbol
            # Find start (working backwards from @)
            start_index = at_index
            while start_index > 0 and re.match(r'[a-zA-Z0-9._%+-]', message[start_index-1]):
                start_index -= 1
            
            # Find end (working forwards from @)
            end_index = at_index
            while end_index < len(message)-1 and re.match(r'[a-zA-Z0-9.-]', message[end_index+1]):
                end_index += 1
            
            # Find the domain end (looking for the '.' and valid TLD)
            while end_index < len(message)-1:
                if message[end_index] == '.':
                    # Found a dot, check for valid TLD length (2-6 chars)
                    potential_end = end_index + 1
                    while potential_end < len(message) and re.match(r'[a-zA-Z]', message[potential_end]):
                        potential_end += 1
                    
                    # If we found a valid TLD length, use this as our end
                    if 2 <= potential_end - (end_index + 1) <= 6:
                        end_index = potential_end
                        break
                
                end_index += 1
                if end_index >= len(message) or not re.match(r'[a-zA-Z0-9.-]', message[end_index]):
                    break
            
            # Extract the potential email and validate
            if start_index < at_index and end_index > at_index:
                potential_email = message[start_index:end_index]
                if self.user_state_manager.is_valid_email(potential_email):
                    logger.info(f"Found email via @ parsing: {potential_email}")
                    return potential_email
        
        # No valid email found with any method
        logger.warning(f"No valid email found in message: '{message}'")
        return None
    
    def _process_recipe_request(self, user_id: str, post_url: str) -> str:
        """Process a recipe request for a user.
        
        Args:
            user_id: Unique identifier for the user
            post_url: Instagram post URL
            
        Returns:
            Response message to send to the user
        """
        user_state = self.user_state_manager.get_user_state(user_id)
        email = user_state.get("email")
        
        if not email:
            # Need email first
            self.user_state_manager.update_user_state(user_id, {
                "state": STATE_AWAITING_EMAIL,
                "pending_url": post_url
            })
            return EMAIL_REQUEST
            
        # User has email, update state and start processing
        self.user_state_manager.update_user_state(user_id, {
            "state": STATE_PROCESSING
        })
        
        # Process the recipe request asynchronously
        # In a real implementation, this would be truly asynchronous
        try:
            # Start process and inform user it's in progress
            logger.info(f"Starting recipe processing for user {user_id}, post {post_url}")
            threading.Thread(target=self._process_recipe_request_async, args=(user_id, post_url)).start()
            return RETURNING_USER.format(email=email)
        except Exception as e:
            logger.error(f"Error starting recipe processing: {str(e)}")
            return PROCESSING_ERROR
    
    def _process_recipe_request_async(self, user_id: str, post_url: str) -> None:
        """Process a recipe request asynchronously.
        
        Args:
            user_id: Unique identifier for the user
            post_url: Instagram post URL
        """
        # This would be a background task in a real implementation
        try:
            # Extract post content
            post_content = self.instagram_monitor.extract_post_content(post_url)
            if not post_content or not post_content.get("caption"):
                logger.error(f"Failed to extract content from {post_url}")
                # Would need to notify user about the failure in a real implementation
                return
                
            # Extract recipe
            recipe_data = self.recipe_extractor.extract_recipe(post_content["caption"])
            if not recipe_data:
                logger.error(f"Failed to extract recipe from {post_url}")
                # Would need to notify user about the failure in a real implementation
                return
                
            # Add source information to recipe data
            if 'source' not in recipe_data:
                recipe_data['source'] = {
                    'platform': 'Instagram',
                    'url': post_url,
                    'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
            # Generate PDF
            pdf_path = self.pdf_generator.generate_pdf(recipe_data)
            if not pdf_path:
                logger.error(f"Failed to generate PDF for {post_url}")
                # Would need to notify user about the failure in a real implementation
                return
                
            # Send email
            user_state = self.user_state_manager.get_user_state(user_id)
            email = user_state.get("email")
            if email:
                self.delivery_agent.send_recipe_email(
                    email, 
                    recipe_data.get("title", "Recipe"),
                    pdf_path
                )
                
            # Update user state
            self.user_state_manager.add_processed_post(
                user_id, 
                post_url, 
                recipe_data.get("title", "Recipe")
            )
            self.user_state_manager.update_user_state(user_id, {
                "state": STATE_AWAITING_URL
            })
            
            # In a real implementation, would notify user of completion
            
        except Exception as e:
            logger.error(f"Error processing recipe request: {str(e)}")
            logger.error(traceback.format_exc())
            # Would need to notify user about the failure in a real implementation

    def _extract_instagram_post_info(self, message: str) -> Optional[str]:
        """Extract Instagram post information from a message."""
        # Check if message is directly a URL
        if message.startswith('http') and ('instagram.com' in message):
            return message
        
        # Check for shared content - look for account names and food-related terms
        food_keywords = ['recipe', 'cook', 'food', 'meal', 'dish', 'bake', 'ingredient']
        instagram_accounts = ['kauscooks', 'hungry.happens', 'recipe', 'food']
        
        # Check if message mentions food and has an Instagram account name
        has_food = any(keyword in message.lower() for keyword in food_keywords)
        has_account = any(account in message.lower() for account in instagram_accounts)
        
        if has_account and has_food:
            return message
        
        # Check for clear Instagram sharing indicators
        if '@' in message and any(term in message.lower() for term in ['recipe', 'cook', 'food']):
            return message
        
        return None
"""
Conversation handler for the Instagram Recipe Agent onboarding flow.
Manages the conversation flow and responses based on user input.
"""

import logging
import re
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
        """Handle an incoming message from a user.
        
        Args:
            user_id: Unique identifier for the user
            message: Message from the user
            
        Returns:
            Response message to send to the user
        """
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
            if self.user_state_manager.is_instagram_post_url(message):
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
            # Expecting an email address
            if self.user_state_manager.is_valid_email(message):
                # Valid email provided
                email = message
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
                    # In a real implementation, this would be a background task
                    self._process_recipe_request_async(user_id, pending_url)
                    return confirmation
                else:
                    # No pending URL, await one
                    self.user_state_manager.update_user_state(user_id, {
                        "state": STATE_AWAITING_URL
                    })
                    return confirmation + "\n\nNow, send me an Instagram recipe post to try it out!"
            else:
                # Invalid email
                return INVALID_EMAIL
        
        # Default response for any other state or unrecognized input
        if self.user_state_manager.is_instagram_post_url(message):
            return self._process_recipe_request(user_id, message)
        else:
            # Update to awaiting URL state if in an unexpected state
            self.user_state_manager.update_user_state(user_id, {
                "state": STATE_AWAITING_URL
            })
            return INVALID_URL
    
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
            
        # User has email, send returning user message
        self.user_state_manager.update_user_state(user_id, {
            "state": STATE_PROCESSING
        })
        
        # In a real implementation, processing would happen asynchronously
        # Here we'll simulate with a synchronous call for simplicity
        return RETURNING_USER.format(email=email)
    
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
                
            # Generate PDF
            pdf_path = self.pdf_generator.generate_recipe_pdf(recipe_data, post_content.get("image_url"))
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
            # Would need to notify user about the failure in a real implementation

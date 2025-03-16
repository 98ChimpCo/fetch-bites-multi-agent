"""
Enhanced conversation handler for the Instagram Recipe Agent onboarding flow.
Manages the conversation flow and responses based on user input with improved email extraction.
"""

import logging
import re
import os
import threading
import time
import traceback
from typing import Dict, Tuple, Optional, List, Any

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
from src.utils.user_state_enhanced import UserStateManager, STATE_NEW, STATE_AWAITING_EMAIL, STATE_AWAITING_URL, STATE_PROCESSING

logger = logging.getLogger(__name__)

class ConversationHandlerEnhanced:
    """Enhanced handler for the conversation flow for the Instagram Recipe Agent."""
    
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
        """Handle an incoming message from a user with enhanced email extraction.
        
        Args:
            user_id: Unique identifier for the user
            message: Message from the user
            
        Returns:
            Response message to send to the user
        """
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
        
        # Check for special message types - email detection
        if "is_email" in message_lower or message_lower.endswith("@gmail.com") or message_lower.endswith("@mac.com") or "@" in message_lower:
            # This might be an email message - try to extract email
            if current_state == STATE_AWAITING_EMAIL or user_state.get("email") is None:
                extracted_email = self._extract_email_from_message(message)
                if extracted_email:
                    # Process valid email
                    return self._handle_valid_email(user_id, extracted_email)
        
        # Process state-specific logic
        if current_state == STATE_NEW:
            # For new users, check if they provided a URL right away
            instagram_urls = self._extract_instagram_urls(message)
            if instagram_urls:
                # User provided URL right away
                self.user_state_manager.update_user_state(user_id, {
                    "state": STATE_AWAITING_EMAIL,
                    "pending_url": instagram_urls[0]
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
            instagram_urls = self._extract_instagram_urls(message)
            if instagram_urls or self.user_state_manager.is_instagram_post_url(message):
                # Valid URL provided
                post_url = instagram_urls[0] if instagram_urls else message
                
                if user_state.get("email"):
                    # User already has email, start processing
                    return self._process_recipe_request(user_id, post_url)
                else:
                    # Need email first
                    self.user_state_manager.update_user_state(user_id, {
                        "state": STATE_AWAITING_EMAIL,
                        "pending_url": post_url
                    })
                    return EMAIL_REQUEST
            else:
                # Invalid URL - check if it's a potential email instead
                extracted_email = self._extract_email_from_message(message)
                if extracted_email:
                    # They've sent an email when we expected a URL - handle it anyway
                    self.user_state_manager.update_user_state(user_id, {"email": extracted_email})
                    return f"Thanks! I've saved your email address ({extracted_email}). Now, please send me an Instagram recipe post link to get a recipe card."
                    
                # Not a URL or email
                return INVALID_URL
                
        elif current_state == STATE_AWAITING_EMAIL:
            # Expecting an email address - try enhanced extraction
            extracted_email = self._extract_email_from_message(message)
            
            if extracted_email:
                # Process valid email
                return self._handle_valid_email(user_id, extracted_email)
            else:
                # Check if they sent a URL instead of an email
                instagram_urls = self._extract_instagram_urls(message)
                if instagram_urls:
                    # They've sent a URL when we expected an email
                    # Update the pending URL but still ask for email
                    self.user_state_manager.update_user_state(user_id, {
                        "pending_url": instagram_urls[0]
                    })
                    return EMAIL_REQUEST
                    
                # Invalid email
                return INVALID_EMAIL
        
        # Default response for any other state or unrecognized input
        instagram_urls = self._extract_instagram_urls(message)
        if instagram_urls or self.user_state_manager.is_instagram_post_url(message):
            post_url = instagram_urls[0] if instagram_urls else message
            return self._process_recipe_request(user_id, post_url)
        else:
            # Last attempt to extract an email if needed
            if not user_state.get("email"):
                extracted_email = self._extract_email_from_message(message)
                if extracted_email:
                    return self._handle_valid_email(user_id, extracted_email)
            
            # Update to awaiting URL state if in an unexpected state
            self.user_state_manager.update_user_state(user_id, {
                "state": STATE_AWAITING_URL
            })
            
            # If they already have an email, remind them we need a URL
            if user_state.get("email"):
                return f"I need an Instagram recipe post link to create a recipe card for you. Please send me a link that starts with 'https://www.instagram.com/p/'"
            else:
                return INVALID_URL
    
    def _handle_valid_email(self, user_id: str, email: str) -> str:
        """
        Handle a valid extracted email address.
        
        Args:
            user_id: User identifier
            email: Extracted email address
            
        Returns:
            Response message
        """
        user_state = self.user_state_manager.get_user_state(user_id)
        pending_url = user_state.get("pending_url")
        
        # Update the email in user state
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
            
            # Process asynchronously
            threading.Thread(target=self._process_recipe_request_async, args=(user_id, pending_url)).start()
            return confirmation
        else:
            # No pending URL, await one
            self.user_state_manager.update_user_state(user_id, {
                "state": STATE_AWAITING_URL
            })
            return confirmation + "\n\nNow, send me an Instagram recipe post to try it out!"
    
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
    
    def _extract_email_from_message(self, message: str) -> Optional[str]:
        """
        Enhanced email extraction from message text.
        
        Args:
            message: Raw message text that might contain an email
            
        Returns:
            Extracted email or None if no valid email found
        """
        # Use the enhanced extraction function from UserStateManager
        return self.user_state_manager.extract_email_from_text(message)
    
    def _extract_instagram_urls(self, message: str) -> List[str]:
        """
        Extract Instagram post URLs from a message.
        
        Args:
            message: Message that might contain Instagram URLs
            
        Returns:
            List of extracted Instagram URLs
        """
        # Use the URL extraction function from UserStateManager
        return self.user_state_manager.extract_instagram_urls(message)
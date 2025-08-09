# src/utils/fetch_bites_messages.py
"""
Centralized messaging system for Fetch Bites user-facing copy
Based on co-founder feedback and user experience improvements
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FetchBitesMessages:
    """Centralized message manager with dynamic personalization"""
    
    def __init__(self):
        self.messages = {
            # === ONBOARDING FLOW ===
            "onboarding_welcome": "Hey {name}! 👋 I'm Fetch Bites - a food-loving AI agent that helps people turn amazing recipe posts into beautiful and organized PDFs.",
            
            "onboarding_instructions": "Thanks for reaching out! Looks like you're enjoying using Fetch Bites! 😊\n\nWould you mind giving us some feedback about what we can improve? That would be amazing - thanks! 🙏",
            
            "onboarding_value_prop": "Please share your email address with me so I can send you a nice-looking PDF of the recipe.",
            
            # === RECIPE PROCESSING ===
            "recipe_processing_start": "Hey {name}, I see you've shared a post! Let me check it out — if it's a recipe, I'll turn it into a beautiful card for you! 🍽️",
            
            "recipe_extraction_success": "I sent your PDF! Let me know if you didn't receive it. Thanks for using Fetch Bites! 🎉",
            
            "recipe_ready_no_email": "Your recipe PDF is ready! (Please provide your email for the PDF attachment)",
            
            # === ERROR HANDLING ===
            "recipe_extraction_failed": "Hey {name}! 😊\n\nI took a thorough look through the post you shared and scanned the captions, comments, and anything written - but I couldn't extract a useful recipe.\n\nThe problem may be the language of the post or that the recipe was mostly shared as a voice over.\n\nFeel free to try sharing a different post - I'm ready when you are! 🍽️",
            
            "language_extraction_issue": "Hey {name}! 😔\n\nI have some bad news. I took a thorough look through the post you shared and scanned the captions, comments, and anything written - but I couldn't extract a useful recipe.\n\nThe problem may be the language of the post or that the recipe was mostly shared as a voice over.\n\nWould you like to try sending a different post? I'm ready to try again whenever you are! 🍽️",
            
            "pdf_generation_failed": "Hey {name}! 😊\n\nGreat news - I successfully extracted your recipe! However, I'm having some technical difficulties creating the PDF right now.\n\nI'm working on fixing this issue. Could you try sending the post again in a few minutes? I'll be ready to help! 🍽️✨",
            
            # === EMAIL MANAGEMENT ===
            "email_request": "Please share your email address to receive your recipe PDF.",
            
            "email_confirmation": "Your recipe PDF has been emailed to you! 📧",
            
            "email_not_received": "Good news! I can extract the real info & PDF but I don't have an email from you on file. Please share your email address with me so I can send you a nice-looking PDF of the recipe.",
            
            # === USER ENGAGEMENT ===
            "returning_user_greeting": "Hey {name}! 😊\n\nWelcome back! I see you're using Fetch Bites again. \n\nWould you mind giving us some feedback about what we can improve? That would be amazing - thanks! 🙏",
            
            "feedback_request": "Hey {name}! 😊\n\nLooks like you're enjoying using Fetch Bites! Would you mind giving us some feedback about what we can improve? That would be amazing - thanks! 🙏",
            
            # === SUCCESS STATES ===
            "pdf_sent_success": "Hey {name}! 😊\nYour PDF has been sent!\nLet me know if you didn't receive it.\nThanks for using Fetch Bites! 🎉",
            
            "recipe_processed_successfully": "Perfect! I've successfully processed your recipe and created a beautiful PDF. Check your email! 📧✨",
            
            # === TECHNICAL ISSUES ===
            "processing_error": "Hmm, I'm having some trouble processing that post right now. Can you try sharing it again? 🔄",
            
            "system_maintenance": "I'm currently updating my recipe detection system. Please try again in a few minutes! 🛠️",
            
            # === FALLBACK MESSAGES ===
            "generic_help": "Hey {name}! I'm Fetch Bites, your recipe extraction assistant. Share any Instagram recipe post with me and I'll turn it into a clean PDF! 🍽️",
            
            "unknown_message_type": "I'm not sure how to respond to that, but I'm always ready to help with recipe extraction! Share a recipe post and let's get cooking! 👨‍🍳"
        }
    
    def get_message(self, message_type: str, user_name: Optional[str] = None, **kwargs) -> str:
        """
        Get a formatted message with dynamic personalization
        
        Args:
            message_type: The type of message to retrieve
            user_name: User's name for personalization (optional)
            **kwargs: Additional formatting parameters
            
        Returns:
            Formatted message string
        """
        try:
            if message_type not in self.messages:
                logger.warning(f"Unknown message type: {message_type}")
                return self.get_message("unknown_message_type", user_name)
            
            message_template = self.messages[message_type]
            
            # Prepare formatting parameters
            format_params = kwargs.copy()
            
            # Handle user name personalization
            if "{name}" in message_template:
                if user_name:
                    # Clean and format user name
                    clean_name = self._clean_user_name(user_name)
                    format_params["name"] = clean_name
                else:
                    # Fallback for missing name
                    format_params["name"] = "there"
            
            # Format the message
            formatted_message = message_template.format(**format_params)
            
            logger.debug(f"Retrieved message type '{message_type}' for user '{user_name}'")
            return formatted_message
            
        except Exception as e:
            logger.error(f"Error formatting message '{message_type}': {e}")
            return f"Hey! I'm Fetch Bites, ready to help with your recipes! 🍽️"
    
    def _clean_user_name(self, user_name: str) -> str:
        """
        Return user name exactly as provided without any transformations
        
        Args:
            user_name: Raw user name from Instagram
            
        Returns:
            User name exactly as provided
        """
        if not user_name:
            return "there"
        
        # Handle special cases only
        if user_name.lower().replace("@", "") in ["user", "unknown", "direct", "audio-call", "video-call"]:
            return "there"
        
        # Return username exactly as provided - no transformations
        return user_name
    
    def get_onboarding_sequence(self, user_name: Optional[str] = None) -> list:
        """Get the complete onboarding message sequence"""
        return [
            self.get_message("onboarding_welcome", user_name),
            self.get_message("onboarding_instructions", user_name),
            self.get_message("onboarding_value_prop", user_name)
        ]
    
    def get_error_message(self, error_type: str, user_name: Optional[str] = None) -> str:
        """Get appropriate error message based on error type"""
        error_mapping = {
            "extraction_failed": "recipe_extraction_failed",
            "language_issue": "language_extraction_issue", 
            "processing_error": "processing_error",
            "no_recipe_found": "recipe_extraction_failed"
        }
        
        message_type = error_mapping.get(error_type, "processing_error")
        return self.get_message(message_type, user_name)

# Global instance for easy access
fetch_bites_messages = FetchBitesMessages()

# Convenience functions for common use cases
def get_onboarding_messages(user_name: Optional[str] = None) -> list:
    """Get onboarding message sequence"""
    return fetch_bites_messages.get_onboarding_sequence(user_name)

def get_message(message_type: str, user_name: Optional[str] = None, **kwargs) -> str:
    """Get a single message with personalization"""
    return fetch_bites_messages.get_message(message_type, user_name, **kwargs)

def get_error_message(error_type: str, user_name: Optional[str] = None) -> str:
    """Get error message"""
    return fetch_bites_messages.get_error_message(error_type, user_name)
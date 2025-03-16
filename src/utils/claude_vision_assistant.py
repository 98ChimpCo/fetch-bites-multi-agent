"""
Claude Vision Assistant for the Instagram Recipe Agent.
Provides visual analysis of Instagram screenshots for more robust UI interaction.
"""

import base64
import imghdr
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any, Tuple
import requests

logger = logging.getLogger(__name__)

class ClaudeVisionAssistant:
    """Uses Claude's visual understanding to assist with automation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Claude Vision Assistant.
        
        Args:
            api_key: Anthropic API key (optional, will use env var if not provided)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.warning("No Anthropic API key provided. Claude vision capabilities will be limited.")
    
    def analyze_screenshot(self, screenshot_path: str, prompt: str) -> Dict[str, Any]:
        """Send a screenshot to Claude with a specific prompt."""
        try:
            # Determine the correct media type based on file extension
            if screenshot_path.lower().endswith('.png'):
                media_type = "image/png"
            elif screenshot_path.lower().endswith('.jpg') or screenshot_path.lower().endswith('.jpeg'):
                media_type = "image/jpeg"
            else:
                media_type = "image/png"  # Default to PNG

            image_type = imghdr.what(screenshot_path)
            media_type = f"image/{image_type}"
        
            # Encode image to base64
            with open(screenshot_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare API request to Claude
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            payload = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,  # Use detected media type
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ]
            }

            # Make API request
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            
            # Process response
            if response.status_code == 200:
                response_data = response.json()
                content = response_data["content"][0]["text"]
                
                # Try to parse as JSON if applicable
                try:
                    if content.strip().startswith('{') and content.strip().endswith('}'):
                        return json.loads(content)
                    elif '```json' in content and '```' in content.split('```json')[1]:
                        json_text = content.split('```json')[1].split('```')[0].strip()
                        return json.loads(json_text)
                except json.JSONDecodeError:
                    # Return as text if not valid JSON
                    return {"text_response": content}
                
                return {"text_response": content}
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return {"error": f"API request failed: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {str(e)}")
            return {"error": str(e)}
    
    def extract_emails(self, screenshot_path: str) -> List[str]:
        """
        Extract emails from a screenshot.
        
        Args:
            screenshot_path: Path to the screenshot file
            
        Returns:
            List of extracted email addresses
        """
        prompt = """
        Please identify any email addresses visible in this screenshot of an Instagram conversation.
        
        Return only the email addresses with no additional text, one per line.
        If you find multiple email addresses, list all of them.
        
        If there are no valid email addresses visible, respond with "NO_EMAIL_FOUND".
        """
        
        result = self.analyze_screenshot(screenshot_path, prompt)
        
        if "error" in result:
            logger.error(f"Error extracting emails: {result['error']}")
            return []
            
        if "text_response" in result:
            # Process text response
            response = result["text_response"]
            
            # Check for no email found
            if "NO_EMAIL_FOUND" in response:
                return []
                
            # Extract emails from response
            emails = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if '@' in line and '.' in line and len(line) > 5:
                    emails.append(line)
            
            return emails
        
        return []
    
    def identify_ui_elements(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Identify UI elements in an Instagram screenshot.
        
        Args:
            screenshot_path: Path to the screenshot file
            
        Returns:
            Dictionary with identified UI elements and their coordinates
        """
        prompt = """
        Please analyze this Instagram screenshot and identify the following UI elements:
        
        1. Message input field (coordinates of center)
        2. Send button (coordinates of center)
        3. Any visible email addresses
        4. Any visible Instagram post URLs
        5. Conversation elements (user messages and their content)
        
        For each UI element, provide:
        - Name/type of element
        - Exact text content if applicable
        - X,Y coordinates of the center of the element (normalized from 0-1 based on image dimensions)
        
        Return the results in JSON format like this:
        {
          "input_field": {"x": 0.5, "y": 0.95},
          "send_button": {"x": 0.9, "y": 0.95},
          "emails": ["example@gmail.com"],
          "instagram_urls": ["https://www.instagram.com/p/AbC123/"],
          "messages": [
            {"text": "Hello there", "is_user": true, "x": 0.8, "y": 0.3},
            {"text": "Welcome to Fetch Bites", "is_user": false, "x": 0.2, "y": 0.4}
          ]
        }
        
        Only include elements that you can clearly identify in the image.
        """
        
        result = self.analyze_screenshot(screenshot_path, prompt)
        
        if "error" in result:
            logger.error(f"Error identifying UI elements: {result['error']}")
            return {"error": result["error"]}
        
        # If we got a JSON response, use it directly
        if isinstance(result, dict) and "input_field" in result:
            return result
        
        # If we got a text response, try to extract JSON
        if "text_response" in result:
            response = result["text_response"]
            
            # Try to extract JSON from the response
            try:
                # Look for JSON block
                if '{' in response and '}' in response:
                    json_text = response[response.find('{'):response.rfind('}')+1]
                    return json.loads(json_text)
            except json.JSONDecodeError:
                logger.error("Could not parse JSON from Claude's response")
                
            # Return the raw text if we couldn't parse JSON
            return {"text_response": response}
        
        return {"error": "Unexpected response format"}
    
    def analyze_current_state(self, screenshot_path: str) -> Dict[str, Any]:
        """
        Determine the current state of the Instagram interface.
        
        Args:
            screenshot_path: Path to the screenshot file
            
        Returns:
            Dictionary with state information
        """
        prompt = """
        Please analyze this Instagram screenshot and determine what state/screen it shows.
        
        Possible states:
        1. login_screen - Login form is visible
        2. inbox - Direct message inbox list is visible
        3. conversation - A specific conversation/chat is open
        4. profile - A user profile is shown
        5. post - A specific post is shown
        
        Also identify any key information visible:
        - For login: Are there any error messages?
        - For inbox: How many unread conversations?
        - For conversation: Who is the conversation with? Is there an email address visible?
        - For post: Is this a recipe post?
        
        Return the results in JSON format like this:
        {
          "state": "conversation",
          "details": {
            "conversation_with": "user123",
            "email_visible": "user@example.com",
            "last_message": "Here's my email"
          }
        }
        """
        
        return self.analyze_screenshot(screenshot_path, prompt)
    
    def get_normalized_to_actual_coordinates(
        self, 
        normalized_x: float, 
        normalized_y: float, 
        actual_width: int, 
        actual_height: int
    ) -> Tuple[int, int]:
        """
        Convert normalized coordinates (0-1 range) to actual pixel coordinates.
        
        Args:
            normalized_x: X coordinate in 0-1 range
            normalized_y: Y coordinate in 0-1 range
            actual_width: Actual width of the screenshot in pixels
            actual_height: Actual height of the screenshot in pixels
            
        Returns:
            Tuple of (x, y) in pixel coordinates
        """
        x = int(normalized_x * actual_width)
        y = int(normalized_y * actual_height)
        return (x, y)

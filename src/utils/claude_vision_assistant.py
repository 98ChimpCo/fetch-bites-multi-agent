import os
import base64
import json
import logging
import re
from typing import Dict, List, Optional, Union, Tuple
from anthropic import Anthropic

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class ClaudeVisionAssistant:
    """
    Helper class to analyze Instagram UI using Claude Vision API.
    Provides visual understanding capabilities for more reliable Instagram interaction.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Claude Vision Assistant.
        
        Args:
            api_key (str, optional): Anthropic API key. If not provided, attempts to get from environment.
        """
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            
        if not api_key:
            logger.warning("No API key provided for ClaudeVisionAssistant. Visual analysis will be limited.")
            self.client = None
        else:
            self.client = Anthropic(api_key=api_key)
    
    def identify_ui_elements(self, screenshot_path: str) -> Dict:
        """
        Identify UI elements in a screenshot of Instagram interface.
        
        Args:
            screenshot_path (str): Path to the screenshot file
            
        Returns:
            Dict: Dictionary with UI elements and their normalized coordinates (0-1 range)
        """
        if not self.client:
            logger.warning("No Claude client available. Cannot perform UI element identification.")
            return {}
            
        try:
            # Check if screenshot exists
            if not os.path.exists(screenshot_path):
                logger.error(f"Screenshot not found at {screenshot_path}")
                return {}
                
            # Read and encode the image
            with open(screenshot_path, "rb") as f:
                img_content = f.read()
                img_b64 = base64.b64encode(img_content).decode('utf-8')
                
            # Create prompt for UI analysis
            prompt = """
            Analyze this Instagram direct message interface screenshot.
            
            Identify the following UI elements with their normalized coordinates (0-1 range where 0,0 is top left and 1,1 is bottom right):
            1. Message input field (where users type messages)
            2. Send button
            3. Any visible user names or conversation entries
            4. Back button (if visible)
            5. Any visible message bubbles
            
            For each element, provide:
            - The element type (e.g., input_field, send_button, etc.)
            - The x, y coordinates of its center as normalized values between 0 and 1
            - Any visible text associated with the element
            
            Return the results as a JSON object with this structure:
            {
                "input_field": {"x": 0.5, "y": 0.9, "text": ""},
                "send_button": {"x": 0.9, "y": 0.9, "text": ""},
                "conversations": [
                    {"x": 0.2, "y": 0.3, "text": "User1"},
                    {"x": 0.2, "y": 0.4, "text": "User2"}
                ],
                "back_button": {"x": 0.1, "y": 0.1, "text": "Back"},
                "messages": [
                    {"x": 0.7, "y": 0.5, "text": "Hello", "from_user": false},
                    {"x": 0.3, "y": 0.6, "text": "Hi there", "from_user": true}
                ]
            }
            """
            
            # Send request to Claude Vision
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Using a less expensive model for UI analysis
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}
                    ]}
                ]
            )
            
            # Parse JSON from response
            response_text = message.content[0].text
            # Extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code block markers
                json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
            
            try:
                ui_elements = json.loads(json_str)
                logger.info(f"Successfully identified {len(ui_elements)} UI elements")
                return ui_elements
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"Error in identify_ui_elements: {str(e)}")
            return {}
    
    def extract_messages(self, screenshot_path: str) -> List[Dict]:
        """
        Extract messages from a conversation screenshot.
        
        Args:
            screenshot_path (str): Path to the screenshot file
            
        Returns:
            List[Dict]: List of messages with sender and content information
        """
        if not self.client:
            logger.warning("No Claude client available. Cannot perform message extraction.")
            return []
            
        try:
            # Read and encode the image
            with open(screenshot_path, "rb") as f:
                img_content = f.read()
                img_b64 = base64.b64encode(img_content).decode('utf-8')
                
            # Create prompt for message extraction
            prompt = """
            Analyze this Instagram direct message conversation screenshot.
            
            Extract all visible messages from the conversation, identifying:
            1. The message content
            2. Who sent each message (the user or the other person)
            3. Any timestamps or status indicators
            
            Return the results as a JSON array with this structure:
            [
                {
                    "sender": "User" or the actual name if visible,
                    "content": "The text content of the message",
                    "timestamp": "Any visible timestamp" (optional),
                    "is_user_message": true/false (whether the message was sent by the user)
                },
                ...
            ]
            
            Only include messages where you can clearly read the content.
            Order the messages from oldest to newest (top to bottom in the conversation).
            """
            
            # Send request to Claude Vision
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}
                    ]}
                ]
            )
            
            # Parse JSON from response
            response_text = message.content[0].text
            # Extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code block markers
                json_str = response_text[response_text.find("["):response_text.rfind("]")+1]
            
            try:
                messages = json.loads(json_str)
                logger.info(f"Successfully extracted {len(messages)} messages")
                return messages
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Error in extract_messages: {str(e)}")
            return []
    
    def extract_emails(self, screenshot_path: str) -> List[str]:
        """
        Extract email addresses from a screenshot.
        
        Args:
            screenshot_path (str): Path to the screenshot file
            
        Returns:
            List[str]: List of extracted email addresses
        """
        if not self.client:
            logger.warning("No Claude client available. Cannot perform email extraction.")
            return []
            
        try:
            # Read and encode the image
            with open(screenshot_path, "rb") as f:
                img_content = f.read()
                img_b64 = base64.b64encode(img_content).decode('utf-8')
                
            # Create prompt for email extraction
            prompt = """
            Examine this screenshot and extract any email addresses visible in the image.
            
            Focus specifically on:
            1. Messages that contain email addresses
            2. Any form fields that have email addresses entered
            3. Email addresses in any visible text
            
            Return only the email addresses as a JSON array of strings.
            For example: ["user@example.com", "another@gmail.com"]
            
            If no email addresses are visible, return an empty array: []
            """
            
            # Send request to Claude Vision
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}
                    ]}
                ]
            )
            
            # Parse JSON from response
            response_text = message.content[0].text
            # Extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code block markers
                json_str = response_text[response_text.find("["):response_text.rfind("]")+1]
                if not json_str:
                    # If no JSON array found, try to extract emails using regex
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, response_text)
                    return emails
            
            try:
                emails = json.loads(json_str)
                logger.info(f"Successfully extracted {len(emails)} email addresses")
                return emails
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response: {e}")
                
                # Fallback: Try to extract emails using regex
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, response_text)
                if emails:
                    logger.info(f"Extracted {len(emails)} email addresses using regex fallback")
                return emails
                
        except Exception as e:
            logger.error(f"Error in extract_emails: {str(e)}")
            return []
    
    def analyze_instagram_content(self, screenshot_path: str) -> Dict:
        """
        Analyze Instagram content to determine if it contains a recipe.
        
        Args:
            screenshot_path (str): Path to the screenshot file
            
        Returns:
            Dict: Analysis results including whether content contains a recipe
        """
        if not self.client:
            logger.warning("No Claude client available. Cannot perform content analysis.")
            return {"contains_recipe": False, "confidence": 0, "recipe_indicators": []}
            
        try:
            # Read and encode the image
            with open(screenshot_path, "rb") as f:
                img_content = f.read()
                img_b64 = base64.b64encode(img_content).decode('utf-8')
                
            # Create prompt for recipe detection
            prompt = """
            Analyze this Instagram post screenshot and determine if it contains a recipe or cooking instructions.
            
            Look for:
            1. Lists of ingredients
            2. Cooking steps or instructions
            3. Measurements (cups, teaspoons, grams, etc.)
            4. Cooking terms (bake, stir, mix, etc.)
            5. Recipe-related hashtags (#recipe, #cooking, #homemade, etc.)
            
            Return your analysis as a JSON object with this structure:
            {
                "contains_recipe": true/false,
                "confidence": 0-100 (how confident you are that this is a recipe),
                "recipe_indicators": ["list", "of", "observed", "recipe", "indicators"],
                "recipe_type": "The type of recipe if identifiable" (optional),
                "ingredients_detected": ["list", "of", "ingredients"] (if visible)
            }
            """
            
            # Send request to Claude Vision
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}
                    ]}
                ]
            )
            
            # Parse JSON from response
            response_text = message.content[0].text
            # Extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code block markers
                json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
            
            try:
                analysis = json.loads(json_str)
                logger.info(f"Successfully analyzed content: Recipe detected: {analysis.get('contains_recipe', False)}")
                return analysis
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response: {e}")
                return {"contains_recipe": False, "confidence": 0, "recipe_indicators": []}
                
        except Exception as e:
            logger.error(f"Error in analyze_instagram_content: {str(e)}")
            return {"contains_recipe": False, "confidence": 0, "recipe_indicators": []}
    
    def identify_clickable_elements(self, screenshot_path: str) -> Dict[str, List[Dict]]:
        """
        Identify all clickable elements in an Instagram interface screenshot.
        
        Args:
            screenshot_path (str): Path to the screenshot file
            
        Returns:
            Dict[str, List[Dict]]: Dictionary of clickable element types and their details
        """
        if not self.client:
            logger.warning("No Claude client available. Cannot perform clickable element identification.")
            return {}
            
        try:
            # Read and encode the image
            with open(screenshot_path, "rb") as f:
                img_content = f.read()
                img_b64 = base64.b64encode(img_content).decode('utf-8')
                
            # Create prompt for clickable element identification
            prompt = """
            Analyze this Instagram interface screenshot and identify all clickable elements.
            
            For each clickable element, determine:
            1. The element type (button, link, input, etc.)
            2. The approximate center coordinates in normalized form (0-1 range)
            3. The purpose or action associated with the element
            4. Any visible text or icon description
            
            Focus on identifying these types of elements:
            - Buttons (send, back, like, etc.)
            - Input fields
            - Navigation items
            - Conversation entries
            - Message bubbles that might be clickable
            - Menu items
            
            Return the results as a JSON object with categories of elements:
            {
                "buttons": [
                    {"x": 0.9, "y": 0.1, "purpose": "Back", "text": "←"},
                    {"x": 0.95, "y": 0.9, "purpose": "Send", "text": "➤"}
                ],
                "inputs": [
                    {"x": 0.5, "y": 0.9, "purpose": "Message input", "text": "Message..."}
                ],
                "navigation": [
                    {"x": 0.1, "y": 0.2, "purpose": "Home", "text": "Home"}
                ],
                "conversations": [
                    {"x": 0.3, "y": 0.3, "purpose": "Open conversation", "text": "John Doe"}
                ]
            }
            """
            
            # Send request to Claude Vision
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}
                    ]}
                ]
            )
            
            # Parse JSON from response
            response_text = message.content[0].text
            # Extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code block markers
                json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
            
            try:
                clickable_elements = json.loads(json_str)
                total_elements = sum(len(elements) for elements in clickable_elements.values())
                logger.info(f"Successfully identified {total_elements} clickable elements")
                return clickable_elements
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"Error in identify_clickable_elements: {str(e)}")
            return {}
    
    def get_conversation_list(self, screenshot_path: str) -> List[Dict]:
        """
        Extract list of conversations from Instagram DM inbox screenshot.
        
        Args:
            screenshot_path (str): Path to the screenshot file
            
        Returns:
            List[Dict]: List of conversations with position and details
        """
        # First try to use the identify_ui_elements method which might have this info
        ui_elements = self.identify_ui_elements(screenshot_path)
        if ui_elements and "conversations" in ui_elements:
            return ui_elements["conversations"]
            
        # If not found, use identify_clickable_elements which should have it
        clickable_elements = self.identify_clickable_elements(screenshot_path)
        if clickable_elements and "conversations" in clickable_elements:
            return clickable_elements["conversations"]
            
        # If still not found, do a specialized extraction
        if not self.client:
            logger.warning("No Claude client available. Cannot perform conversation list extraction.")
            return []
            
        try:
            # Read and encode the image
            with open(screenshot_path, "rb") as f:
                img_content = f.read()
                img_b64 = base64.b64encode(img_content).decode('utf-8')
                
            # Create prompt for conversation list extraction
            prompt = """
            Analyze this Instagram Direct Messages inbox screenshot.
            
            Identify all visible conversations in the left sidebar or main view.
            For each conversation entry, provide:
            1. The name of the user or group
            2. The position (normalized x,y coordinates of the center)
            3. Any visible message preview or status
            4. Whether the conversation appears to have unread messages
            
            Return the results as a JSON array:
            [
                {
                    "name": "User Name",
                    "x": 0.2,
                    "y": 0.3,
                    "preview": "Last message preview if visible",
                    "unread": true/false,
                    "active_status": "Active status if visible"
                },
                ...
            ]
            
            Order the conversations from top to bottom as they appear in the interface.
            """
            
            # Send request to Claude Vision
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}
                    ]}
                ]
            )
            
            # Parse JSON from response
            response_text = message.content[0].text
            # Extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code block markers
                json_str = response_text[response_text.find("["):response_text.rfind("]")+1]
            
            try:
                conversations = json.loads(json_str)
                logger.info(f"Successfully extracted {len(conversations)} conversations")
                return conversations
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude response: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Error in get_conversation_list: {str(e)}")
            return []

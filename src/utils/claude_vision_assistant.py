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

    DEFAULT_MODEL = "claude-3-opus-20240229"

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
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                
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
                model=self.DEFAULT_MODEL,
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
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                
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
                model=self.DEFAULT_MODEL,
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
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                
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
                model=self.DEFAULT_MODEL,
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
    
    def analyze_instagram_content(self, image_path: str) -> Optional[Dict]:
        logger.info(f"🧠 ClaudeVision: analyzing screenshot {image_path}")
        """
        Send image to Claude Vision API with tailored prompt for analyzing shared IG posts.
        """
        try:
            with open(image_path, "rb") as image_file:
                img_b64 = base64.b64encode(image_file.read()).decode("utf-8")

                prompt = """
                This is a screenshot of an Instagram DM thread. A user may have shared a post preview (e.g. video or photo thumbnail) and the DM interface may be visible.
                
                Please analyze the screenshot and return the following in **valid JSON**:
                
                - "is_shared_post": true or false — whether a shared post is present
                - "post_url": the Instagram post URL if visible
                - "confidence": a float between 0 and 1 for your certainty
                - "summary": a 1-line summary of what the post appears to be about
                - If visible, return the click target coordinates of the shared post preview as "click_target": {"x": ..., "y": ...}
                - If the message input field is visible, return "message_box": {"x": ..., "y": ...}
                - If the send button is visible, return "send_button": {"x": ..., "y": ...}
                
                Use normalized screen coordinates (0-1 range). Do not include any explanation — just return a single JSON object.
                """
                response = self.client.messages.create(
                model=self.DEFAULT_MODEL,
                max_tokens=1024,
                temperature=0.3,
                system="You are an expert UI interpreter for Instagram screenshots.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            if hasattr(response, "content"):
                text = response.content[0].text.strip()
                logger.info(f"Claude raw response: {text}")

                # Extract JSON block only
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if not json_match:
                    logger.error("No JSON object found in Claude response.")
                    return None

                json_str = json_match.group(0)

                try:
                    return json.loads(json_str)
                except Exception as e:
                    logger.error(f"Failed to parse extracted JSON block: {e}")
                    return None

        except Exception as e:
            logger.error(f"Claude Vision error: {e}")
            return None
        
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
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                
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
                model=self.DEFAULT_MODEL,
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
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
                
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
                model=self.DEFAULT_MODEL,
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

    def extract_structured_post_data(self, dm_data: Dict) -> Dict:
        logger.info(f"🧠 Extracting structured post data from: {list(dm_data.keys())}")
        """
        Extract a structured post object from a DM message or screenshot.
        Returns keys: post_url, caption_text, confidence, source_type
        """
        result = {
            "post_url": None,
            "caption_text": None,
            "confidence": None,
            "source_type": "unknown"
        }

        try:
            if dm_data.get("screenshot_path"):
                analysis = self.analyze_instagram_content(dm_data["screenshot_path"])
                if not analysis:
                    logger.warning("Claude Vision returned no analysis.")
                    return result

                # Existing logic for handling click target (if any) would be here.
                if "click_target" in analysis:
                    # (Existing click target handling logic)
                    pass

                if analysis.get("post_url"):
                    result.update({
                        "post_url": analysis["post_url"],
                        "confidence": analysis.get("confidence", 0),
                        "source_type": "screenshot"
                    })
                if analysis.get("contains_recipe"):
                    result["caption_text"] = analysis.get("caption_text") or ""

                # Ensure shared post processing always runs, even if already expanded.
                if analysis.get("is_shared_post", False):
                    logger.info("📎 Post URL: %s", analysis.get("post_url"))
                    confidence = analysis.get("confidence", 0.0)
                    logger.info(f"🧠 Claude Vision confidence: {confidence}")
                    # Proceed with recipe extraction, PDF generation, and reply

            elif dm_data.get("html_block"):
                url_match = re.search(r"https://www.instagram.com/[^\s\"']+", dm_data["html_block"])
                if url_match:
                    result.update({
                        "post_url": url_match.group(0),
                        "confidence": 85.0,
                        "source_type": "html_block"
                    })

            elif dm_data.get("message"):
                url_match = re.search(r"https://www.instagram.com/[^\s\"']+", dm_data["message"])
                if url_match:
                    result.update({
                        "post_url": url_match.group(0),
                        "confidence": 90.0,
                        "source_type": "message"
                    })
                else:
                    # Fallback: if message indicates a blog recipe, extract blog URL
                    msg_lower = dm_data["message"].lower()
                    if "full recipe" in msg_lower and "blog" in msg_lower:
                        blog_url_match = re.search(r"https?://(?:www\.)?[\w.-]+\.[a-z]{2,}(?:/[^\s\"']+)?", dm_data["message"])
                        if blog_url_match:
                            result.update({
                                "post_url": blog_url_match.group(0),
                                "confidence": 80.0,
                                "source_type": "blog_link"
                            })
                        else:
                            result["caption_text"] = dm_data["message"]
                            result["source_type"] = "message_text"
                    else:
                        result["caption_text"] = dm_data["message"]
                        result["source_type"] = "message_text"

            return result
        except Exception as e:
            logger.error(f"Failed to extract structured post data: {e}")
            return result
        
    def find_shared_post_coordinates(self, screenshot_path: str) -> Optional[Dict[str, float]]:
        """
        Ask Claude to locate the shared post preview in a screenshot.
        Returns normalized coordinates (0-1 range) if found.
        """
        prompt = """
        You are an expert UI assistant. The attached screenshot is from an Instagram DM thread.

        A user has shared a post preview (e.g. a video thumbnail or image preview). 
        Please locate the preview of that shared post.

        Respond in JSON:
        {
            "x": 0.5,  // normalized X coordinate (0 to 1)
            "y": 0.6   // normalized Y coordinate (0 to 1)
        }

        Only respond with the JSON. Do not include any explanation.
        """

        try:
            response = self.analyze_image_and_get_json(screenshot_path, prompt)
            if response and "x" in response and "y" in response:
                return {"x": float(response["x"]), "y": float(response["y"])}
        except Exception as e:
            logger.error(f"Vision coordinate extraction failed: {e}")
        
        return None
    

    def analyze_image_and_get_json(self, screenshot_path: str, prompt: str) -> Dict:
        """
        Send a screenshot and prompt to Claude Vision and return the parsed JSON response.
        """
        try:
            with open(screenshot_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            message = self.client.messages.create(
                model=self.DEFAULT_MODEL,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}}
                    ]
                }]
            )

            match = re.search(r"\{.*?\}", message.content[0].text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                logger.error("No JSON object found in Claude response.")
                return {}
        except Exception as e:
            logger.error(f"analyze_image_and_get_json failed: {e}")
            return {}
        
    def extract_post_content_from_image(self, screenshot_path: str) -> Dict:
        """
        Given a screenshot of an Instagram post, ask Claude to return caption and metadata.
        """
        prompt = """
        This is a screenshot of an Instagram post.

        Please extract the following in JSON format:
        {
        "caption": "...",
        "hashtags": ["...", "..."],
        "mentions": ["..."],
        "urls": ["..."]
        }

        Only include fields if present. Return clean JSON only.
        """
        return self.analyze_image_and_get_json(screenshot_path, prompt)

    def get_click_target_from_screenshot(self, screenshot_path: str, target_name: str = "Shahin Zangenehpour") -> Optional[Dict[str, float]]:
        """
        Ask Claude Vision to find a DM conversation tile matching a name and return click coordinates.
 
        Args:
            screenshot_path (str): Path to the screenshot image.
            target_name (str): The display name of the person to click.
 
        Returns:
            Dict with keys 'x' and 'y' (normalized 0-1), or None if not found.
        """
        if not self.client:
            logger.warning("No Claude client available. Cannot locate conversation click target.")
            return None
 
        try:
            with open(screenshot_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
 
            prompt = f"""
            You are an expert UI assistant. This is a screenshot of the Instagram DM interface.
 
            Please locate the conversation tile that includes the name "{target_name}" on the left-hand sidebar.
 
            Return a JSON object like:
            {{
                "click_target": {{ "x": float, "y": float }},
                "reasoning": "why you chose this location"
            }}
 
            Only return JSON. No extra commentary.
            """
 
            message = self.client.messages.create(
                model=self.DEFAULT_MODEL,
                max_tokens=1024,
                temperature=0.3,
                system="You are an expert UI interpreter for Instagram screenshots.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {
                                "type": "base64", "media_type": "image/png", "data": img_b64
                            }},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
            )
 
            if hasattr(message, "content"):
                text = message.content[0].text.strip()
                logger.info(f"Claude raw response: {text}")
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    return json.loads(match.group(0)).get("click_target")
            return None
        except Exception as e:
            logger.error(f"get_click_target_from_screenshot failed: {e}")
            return None
        
    def get_all_unread_thread_targets(self, screenshot_path):
        """
        Returns a list of click coordinates for unread DM threads, identified by blue dot indicator.
        """
        prompt = (
            "You are viewing the Instagram DM interface. Your task is to locate all unread DM threads in the left panel. "
            "These are visually identified by a small blue dot on the right edge of the conversation tile.\n\n"
            "Please return a list of click coordinates `(x, y)` — one per unread thread — to click the center of the profile picture "
            "or tile to open each thread. The coordinates should be normalized between 0 and 1, and listed from bottom to top, "
            "in reverse vertical order.\n\n"
            "Only include threads with a blue dot. Do not include any read threads."
        )
        with open(screenshot_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        image_data = encoded
        response = self._call_claude_vision(prompt, image_data)
        
        if isinstance(response, list):
            logger.info(f"🔵 Claude returned {len(response)} unread thread targets.")
            for i, coords in enumerate(response):
                logger.info(f"    [{i}] x: {coords['x']:.3f}, y: {coords['y']:.3f}")
            return response
        else:
            logger.warning("⚠️ Claude did not return a list of unread threads.")
            return []
    
    def _load_image_as_base64(self, image_path):
        import base64
        if not os.path.exists(image_path):
            logger.error(f"Screenshot not found at {image_path}")
            return ""

        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        if not encoded:
            logger.error("Base64 encoding failed: empty result.")
        else:
            logger.debug(f"Base64 sample: {encoded[:100]}...")
        return f"data:image/png;base64,{encoded}"

    def _call_claude_vision(self, prompt: str, image_data: str) -> Union[Dict, List, str]:
        try:
            message = self.client.messages.create(
                model=self.DEFAULT_MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data
                            }}
                        ]
                    }
                ]
            )
            if hasattr(message, "content"):
                text = message.content[0].text.strip()
                logger.info(f"Claude raw response: {text}")

                match = re.search(r"\[.*\]|\{.*\}", text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except json.JSONDecodeError:
                        pass

                # Fallback: try parsing raw tuple lines like (0.175, 0.65)
                tuple_matches = re.findall(r"\((\d*\.\d+),\s*(\d*\.\d+)\)", text)
                if tuple_matches:
                    return [{"x": float(x), "y": float(y)} for x, y in tuple_matches]

                # If nothing matched, just return raw text
                return text
        except Exception as e:
            logger.error(f"_call_claude_vision failed: {e}")
            return {}
        
    def extract_dm_handle(self, image_path):
        image_data = self._encode_image_base64(image_path)
        prompt = (
            "You're looking at an Instagram DM conversation. "
            "What is the visible username or account handle of the other person in this chat? "
            "Return only the handle as a plain string, like @chefjohn."
        )
        response = self._call_claude_vision(prompt, image_data)
        if isinstance(response, str):
            clean = response.strip().split()[0]
            if clean.startswith("@"):
                logger.info(f"✅ Extracted DM handle: {clean}")
                return clean
            logger.warning(f"⚠️ Unexpected handle format: {response}")
        else:
            logger.warning("⚠️ Claude did not return a string for handle extraction.")
        return None

    def analyze_dm_thread(self, screenshot_path: str) -> Optional[Dict]:
        """
        Perform a unified analysis of a DM thread screenshot to extract:
        - Instagram handle
        - Shared post preview info
        - Post URL and caption
        - Message box and send button locations
        """
        prompt = """
        You are analyzing a screenshot of the Instagram inbox (DM list view).

        Your task is to:
        1. Identify any unread conversation threads. These are visually marked by a small **blue dot on the right side** of the thread row.
        2. If multiple unread threads are present, return the **lowest one on the list** (bottom-most unread thread).
        3. Return the normalized coordinates for clicking — not on the blue dot, but on the **center of the unread conversation tile**, typically where the profile image or name is. Do NOT click the blue dot itself.

        You should also return:
        - "handle": the username or name next to the blue dot
        - "is_shared_post": false (in this inbox view it's not visible)
        - "message_box" and "send_button": null
        - "post_url" and "caption": null
        - "confidence": float between 0 and 1 indicating how sure you are that it's an unread thread

        Return only JSON — no explanation or extra text.
        """
        try:
            with open(screenshot_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
 
            response = self._call_claude_vision(prompt, image_data)
            if isinstance(response, dict):
                logger.info("✅ Unified thread analysis successful.")
                return response
            else:
                logger.warning("⚠️ Claude thread analysis returned unexpected format.")
                return None
        except Exception as e:
            logger.error(f"analyze_dm_thread failed: {e}")
            return None
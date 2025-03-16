"""
Instagram Message Adapter for the Instagram Recipe Agent using Claude Vision.
Handles receiving and sending messages via Instagram DM with screenshot-based analysis.
"""

import logging
import time
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from src.utils.claude_vision_assistant import ClaudeVisionAssistant
from src.utils.message_tracker import MessageTracker

logger = logging.getLogger(__name__)

class InstagramMessageAdapterVision:
    """Adapter for interacting with Instagram direct messages using Claude Vision."""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        chrome_driver_path: Optional[str] = None,
        headless: bool = False,
        check_interval: int = 60,  # seconds
        message_tracker: Optional[MessageTracker] = None,
        claude_api_key: Optional[str] = None
    ):
        """Initialize the Instagram message adapter.
        
        Args:
            username: Instagram username
            password: Instagram password
            chrome_driver_path: Path to Chrome WebDriver (optional)
            headless: Whether to run in headless mode
            check_interval: How often to check for new messages (seconds)
            message_tracker: Optional MessageTracker instance
            claude_api_key: Anthropic API key for Claude vision capabilities
        """
        self.username = username or os.getenv('INSTAGRAM_USERNAME')
        self.password = password or os.getenv('INSTAGRAM_PASSWORD')
        self.chrome_driver_path = chrome_driver_path
        self.headless = headless
        self.check_interval = check_interval
        self.driver = None
        self.is_running = False
        self.message_handlers = []
        self.message_tracker = message_tracker or MessageTracker()
        
        # Screen dimensions - will be set when driver is initialized
        self.screen_width = 0
        self.screen_height = 0
        
        # Claude Vision Assistant
        self.claude_assistant = ClaudeVisionAssistant(claude_api_key or os.getenv('ANTHROPIC_API_KEY'))
        
        # Create screenshots directory with timestamp subfolders
        self.screenshots_dir = f"screenshots/{time.strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
    def setup_driver(self) -> webdriver.Chrome:
        """Set up and return a Chrome WebDriver instance with anti-detection measures.
        
        Returns:
            Chrome WebDriver instance
        """
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
            
        # Basic config
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1280,800")  # Standard desktop size
        options.add_argument("--start-maximized")
        
        # Anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Remove mobile emulation - use desktop version instead
        # options.add_experimental_option("mobileEmulation", {...})  <-- Remove this
        
        if self.chrome_driver_path:
            service = Service(self.chrome_driver_path)
        else:
            service = Service(ChromeDriverManager().install())
                
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set additional anti-detection measures
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
            """
        })
        
        # Store screen dimensions
        self.screen_width = driver.execute_script("return window.innerWidth")
        self.screen_height = driver.execute_script("return window.innerHeight")
        logger.info(f"Browser dimensions: {self.screen_width}x{self.screen_height}")
        
        return driver
        
    def login(self) -> bool:
        """Log in to Instagram using Claude Vision for UI analysis.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.driver:
                self.driver = self.setup_driver()
                    
            logger.info("Logging in to Instagram...")
            self.driver.get("https://www.instagram.com/")
            
            # Take screenshot of initial page
            initial_screenshot = f"{self.screenshots_dir}/initial_page.png"
            self.driver.save_screenshot(initial_screenshot)
            
            # Wait for page to load
            time.sleep(3)
            
            # First attempt with standard selectors - this should work for desktop version
            try:
                # Try to find username and password fields
                username_field = self.driver.find_element(By.NAME, "username")
                password_field = self.driver.find_element(By.NAME, "password")
                
                # Enter credentials
                username_field.clear()
                username_field.send_keys(self.username)
                password_field.clear()
                password_field.send_keys(self.password)
                
                # Find and click login button
                login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
                
                logger.info("Logged in using standard selectors")
            except Exception as e:
                # Fall back to JavaScript approach if selectors fail
                logger.warning(f"Standard login failed: {str(e)}")
                
                # Try a JavaScript approach as last resort
                login_js = f"""
                function attemptLogin() {{
                    // Try to find input fields
                    const inputs = document.querySelectorAll('input');
                    let usernameField = null;
                    let passwordField = null;
                    
                    for (const input of inputs) {{
                        if (input.type === 'text' || input.name === 'username' || 
                            input.placeholder && input.placeholder.toLowerCase().includes('username')) {{
                            usernameField = input;
                        }}
                        if (input.type === 'password' || input.name === 'password' || 
                            input.placeholder && input.placeholder.toLowerCase().includes('password')) {{
                            passwordField = input;
                        }}
                    }}
                    
                    if (!usernameField || !passwordField) {{
                        return false;
                    }}
                    
                    // Enter credentials
                    usernameField.value = "{self.username}";
                    passwordField.value = "{self.password}";
                    
                    // Dispatch events to simulate typing
                    usernameField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    // Find login button
                    const buttons = document.querySelectorAll('button');
                    for (const button of buttons) {{
                        if (button.type === 'submit' || 
                            button.textContent.toLowerCase().includes('log in') ||
                            button.textContent.toLowerCase().includes('login')) {{
                            button.click();
                            return true;
                        }}
                    }}
                    
                    return false;
                }}
                
                return attemptLogin();
                """
                
                login_success = self.driver.execute_script(login_js)
                if not login_success:
                    logger.error("All login approaches failed")
                    return False
            
            # Wait for login to complete
            time.sleep(5)
            
            # Handle dialogs using standard selectors first
            try:
                # Check for "Save Login Info" dialog
                save_login_buttons = self.driver.find_elements(By.XPATH, "//button[text()='Not Now']")
                if save_login_buttons:
                    save_login_buttons[0].click()
                    time.sleep(2)
                    
                # Check for notifications dialog
                notification_buttons = self.driver.find_elements(By.XPATH, "//button[text()='Not Now']")
                if notification_buttons:
                    notification_buttons[0].click()
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"Error handling dialogs: {str(e)}")
                
            # Navigate to inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(5)  # Allow page to load fully
            
            # Take screenshot after reaching inbox
            inbox_screenshot = f"{self.screenshots_dir}/inbox.png"
            self.driver.save_screenshot(inbox_screenshot)
            
            logger.info("Successfully logged in to Instagram")
            return True
                
        except Exception as e:
            logger.error(f"Error logging in to Instagram: {str(e)}")
            if self.driver:
                self.driver.save_screenshot(f"{self.screenshots_dir}/login_error.png")
            return False
    
    def _handle_post_login_dialogs(self) -> bool:
        """Handle dialogs that appear after login using Claude Vision.
        
        Returns:
            True if all dialogs handled successfully, False otherwise
        """
        try:
            # Take screenshot to analyze dialogs
            dialog_screenshot = f"{self.screenshots_dir}/post_login_dialogs.png"
            self.driver.save_screenshot(dialog_screenshot)
            
            # Analyze current state
            state = self.claude_assistant.analyze_current_state(dialog_screenshot)
            
            # Check for common dialogs in Claude's analysis
            if "details" in state:
                details = state["details"]
                
                # Handle "Save Login Info" dialog
                if details.get("dialog_type") == "save_login_info" or "save login info" in self.driver.page_source.lower():
                    logger.info("Save Login Info dialog detected")
                    self._dismiss_dialog("Not Now")
                    time.sleep(2)
                    self.driver.save_screenshot(f"{self.screenshots_dir}/after_save_login_dialog.png")
                
                # Handle "Turn on Notifications" dialog
                if details.get("dialog_type") == "turn_on_notifications" or "notifications" in self.driver.page_source.lower():
                    logger.info("Notifications dialog detected")
                    self._dismiss_dialog("Not Now")
                    time.sleep(2)
                    self.driver.save_screenshot(f"{self.screenshots_dir}/after_notifications_dialog.png")
                
                # Handle "Add Instagram to Home Screen" dialog (mobile)
                if details.get("dialog_type") == "add_to_home_screen" or "add instagram to your home screen" in self.driver.page_source.lower():
                    logger.info("Add to Home Screen dialog detected")
                    self._dismiss_dialog("Cancel")
                    time.sleep(2)
                
                # Handle cookie consent dialog
                if details.get("dialog_type") == "cookie_consent" or "cookie" in self.driver.page_source.lower():
                    logger.info("Cookie consent dialog detected")
                    self._dismiss_dialog("Accept All")
                    time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling post-login dialogs: {str(e)}")
            return False
    
    def _dismiss_dialog(self, button_text: str) -> bool:
        """
        Attempt to dismiss a dialog by clicking a button with the given text.
        
        Args:
            button_text: Text of the button to click
            
        Returns:
            True if button found and clicked, False otherwise
        """
        try:
            # First, try direct XPath to find the button
            button_xpath = f"//button[contains(text(), '{button_text}')]"
            buttons = self.driver.find_elements(By.XPATH, button_xpath)
            if buttons:
                buttons[0].click()
                logger.info(f"Clicked '{button_text}' button using XPath")
                return True
            
            # If that fails, take a screenshot and analyze with Claude
            dialog_screenshot = f"{self.screenshots_dir}/dismiss_dialog_{time.time()}.png"
            self.driver.save_screenshot(dialog_screenshot)
            
            # Ask Claude to find the button
            prompt = f"""
            Please analyze this Instagram screenshot and identify the button with text "{button_text}" 
            or similar dismissive action (like X, Close, Cancel, etc.).
            
            Return the coordinates (x, y) of the center of the button, normalized to the image dimensions (0-1 range).
            
            Return just a JSON object like:
            {{
              "button_found": true/false,
              "x": 0.5,
              "y": 0.7
            }}
            """
            
            button_info = self.claude_assistant.analyze_screenshot(dialog_screenshot, prompt)
            
            if "button_found" in button_info and button_info["button_found"]:
                # Click at the coordinates
                self._click_at_normalized_coordinates(button_info["x"], button_info["y"])
                logger.info(f"Clicked '{button_text}' button using coordinates from Claude")
                return True
            
            # If Claude couldn't find it, try JavaScript as a last resort
            dismiss_js = f"""
            function findAndClickButton() {{
                // Try to find by text content
                const buttons = Array.from(document.querySelectorAll('button'));
                const links = Array.from(document.querySelectorAll('a'));
                
                // Combine buttons and links
                const clickables = [...buttons, ...links];
                
                // Try to find by text content
                for (const el of clickables) {{
                    if (el.textContent && el.textContent.toLowerCase().includes('{button_text.lower()}')) {{
                        el.click();
                        return true;
                    }}
                }}
                
                // Look for similar dismissive actions
                for (const el of clickables) {{
                    const text = el.textContent && el.textContent.toLowerCase();
                    if (text && (
                        text.includes('cancel') || 
                        text.includes('close') || 
                        text.includes('not now') ||
                        text.includes('dismiss') ||
                        text.includes('skip')
                    )) {{
                        el.click();
                        return true;
                    }}
                }}
                
                return false;
            }}
            
            return findAndClickButton();
            """
            
            clicked = self.driver.execute_script(dismiss_js)
            if clicked:
                logger.info(f"Clicked dialog dismiss button using JavaScript")
                return True
                
            logger.warning(f"Could not find button with text '{button_text}'")
            return False
            
        except Exception as e:
            logger.error(f"Error dismissing dialog: {str(e)}")
            return False
            
    def register_message_handler(self, handler):
        """Register a function to handle incoming messages.
        
        Args:
            handler: Function that takes user_id and message as arguments
                    and returns a response message
        """
        self.message_handlers.append(handler)

    def _click_at_normalized_coordinates(self, normalized_x: float, normalized_y: float) -> bool:
        """
        Click at specific normalized coordinates (0-1 range).
        
        Args:
            normalized_x: X coordinate in 0-1 range
            normalized_y: Y coordinate in 0-1 range
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current window size - important to refresh this as it might change
            self.screen_width = self.driver.execute_script("return window.innerWidth")
            self.screen_height = self.driver.execute_script("return window.innerHeight")
            
            # Convert to actual pixel coordinates
            x = int(normalized_x * self.screen_width)
            y = int(normalized_y * self.screen_height)
            
            # Make sure coordinates are within bounds
            x = min(x, self.screen_width - 10)  # Stay 10px away from edge
            y = min(y, self.screen_height - 10)  # Stay 10px away from edge
            
            logger.info(f"Clicking at coordinates: ({x}, {y})")
            
            # Try alternative clicking approaches
            try:
                # First try direct ActionChains click
                actions = ActionChains(self.driver)
                actions.move_by_offset(x, y).click().perform()
                actions.reset_actions()
                return True
            except Exception as e:
                logger.warning(f"Direct coordinate click failed: {str(e)}")
                
                # Try JavaScript-based clicking
                click_js = f"""
                document.elementFromPoint({x}, {y}).click();
                return true;
                """
                result = self.driver.execute_script(click_js)
                if result:
                    logger.info("Clicked using JavaScript elementFromPoint")
                    return True
                
                # As a last resort, try to find an element at the position and click it
                element = self.driver.execute_script(f"return document.elementFromPoint({x}, {y});")
                if element:
                    element.click()
                    logger.info("Clicked element found at coordinates")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Error clicking at coordinates ({normalized_x}, {normalized_y}): {str(e)}")
            return False

    def check_new_messages(self) -> List[Dict[str, Any]]:
        """Check for new messages in the Instagram inbox using Claude Vision.
        
        Returns:
            List of new messages with user_id and message content
        """
        try:
            # Navigate to inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(3)
            
            # Take a screenshot of the inbox
            inbox_screenshot = f"{self.screenshots_dir}/inbox_{time.time()}.png"
            self.driver.save_screenshot(inbox_screenshot)
            
            # Analyze inbox to find conversations
            prompt = """
            Please analyze this Instagram DM inbox screenshot and identify:
            
            1. All visible conversations
            2. For each conversation:
               - Username/name
               - Whether it has unread messages (look for blue dots or "New message" indicators)
               - Position (normalized coordinates of the center of the conversation item)
            
            Return the data in JSON format like this:
            {
              "conversations": [
                {
                  "username": "user1",
                  "has_unread": true,
                  "x": 0.5,
                  "y": 0.2
                },
                {
                  "username": "user2",
                  "has_unread": false,
                  "x": 0.5,
                  "y": 0.3
                }
              ]
            }
            
            Only include conversations you can clearly identify in the image.
            """
            
            inbox_analysis = self.claude_assistant.analyze_screenshot(inbox_screenshot, prompt)
            
            new_messages = []
            
            # Check if we have conversation data
            if "conversations" in inbox_analysis:
                conversations = inbox_analysis["conversations"]
                logger.info(f"Found {len(conversations)} conversations in inbox")
                
                # Prioritize conversations with unread messages
                unread_conversations = [c for c in conversations if c.get("has_unread", False)]
                other_conversations = [c for c in conversations if not c.get("has_unread", False)]
                
                # Process unread conversations first, then others
                prioritized_conversations = unread_conversations + other_conversations
                
                # Limit to 5 conversations to avoid processing too many
                for conversation in prioritized_conversations[:5]:
                    # Click on the conversation
                    self._click_at_normalized_coordinates(conversation["x"], conversation["y"])
                    time.sleep(3)  # Wait for conversation to load
                    
                    # Process this conversation
                    conversation_messages = self._process_conversation(conversation["username"])
                    new_messages.extend(conversation_messages)
                    
                    # Go back to inbox
                    self.driver.get("https://www.instagram.com/direct/inbox/")
                    time.sleep(3)
            else:
                logger.warning("Could not identify conversations in inbox")
                
                # Try a more direct approach
                try:
                    # Look for unread indicators
                    unread_elements = self.driver.find_elements(By.XPATH, 
                        "//div[contains(text(), 'New message') or contains(@class, 'unread')]")
                    
                    if unread_elements:
                        for element in unread_elements[:3]:  # Limit to first 3
                            try:
                                element.click()
                                time.sleep(3)
                                
                                # Process using a generic ID since we don't know the username
                                conversation_id = f"conversation_{time.time()}"
                                conversation_messages = self._process_conversation(conversation_id)
                                new_messages.extend(conversation_messages)
                                
                                # Go back to inbox
                                self.driver.get("https://www.instagram.com/direct/inbox/")
                                time.sleep(3)
                            except Exception as e:
                                logger.error(f"Error processing unread conversation: {str(e)}")
                except Exception as e:
                    logger.error(f"Error with direct unread conversation approach: {str(e)}")
            
            return new_messages
            
        except Exception as e:
            logger.error(f"Error checking new messages: {str(e)}")
            if self.driver:
                self.driver.save_screenshot(f"{self.screenshots_dir}/message_check_error.png")
            return []
    
    def _process_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Process a conversation to extract messages using Claude Vision.
        
        Args:
            conversation_id: Identifier for the conversation
            
        Returns:
            List of extracted messages
        """
        try:
            # Take screenshot of the conversation
            conversation_screenshot = f"{self.screenshots_dir}/conversation_{conversation_id}_{time.time()}.png"
            self.driver.save_screenshot(conversation_screenshot)
            
            # Analyze conversation to identify messages and input field
            conversation_analysis = self.claude_assistant.identify_ui_elements(conversation_screenshot)
            
            # Extract messages from the analysis
            messages = []
            
            if "messages" in conversation_analysis:
                for message in conversation_analysis["messages"]:
                    # Create a unique ID for the message
                    message_id = f"{conversation_id}_{message['text'][:20]}_{time.time()}"
                    
                    # Skip if already processed
                    if self.message_tracker.is_processed(message_id):
                        continue
                    
                    # Add to messages list
                    messages.append({
                        "user_id": conversation_id,
                        "message": message["text"],
                        "is_user": message.get("is_user", False)
                    })
                    
                    # Mark as processed
                    self.message_tracker.mark_processed(message_id)
            
            # Look for email addresses
            if "emails" in conversation_analysis and conversation_analysis["emails"]:
                for email in conversation_analysis["emails"]:
                    email_message_id = f"{conversation_id}_email_{email}_{time.time()}"
                    
                    # Skip if already processed
                    if self.message_tracker.is_processed(email_message_id):
                        continue
                    
                    # Add as a special email message
                    messages.append({
                        "user_id": conversation_id,
                        "message": email,
                        "is_email": True
                    })
                    
                    # Mark as processed
                    self.message_tracker.mark_processed(email_message_id)
            
            # Extract more potential emails using Claude directly
            extracted_emails = self.claude_assistant.extract_emails(conversation_screenshot)
            for email in extracted_emails:
                email_message_id = f"{conversation_id}_extracted_email_{email}_{time.time()}"
                
                # Skip if already processed
                if self.message_tracker.is_processed(email_message_id):
                    continue
                
                # Add as a special email message
                messages.append({
                    "user_id": conversation_id,
                    "message": email,
                    "is_email": True
                })
                
                # Mark as processed
                self.message_tracker.mark_processed(email_message_id)
            
            # Process the messages with our handlers
            for message_data in messages:
                for handler in self.message_handlers:
                    try:
                        response = handler(message_data["user_id"], message_data["message"])
                        if response:
                            # Send response
                            self._send_message_using_vision(response)
                    except Exception as e:
                        logger.error(f"Error in message handler: {str(e)}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Error processing conversation {conversation_id}: {str(e)}")
            self.driver.save_screenshot(f"{self.screenshots_dir}/conversation_error_{conversation_id}.png")
            return []
    
    def _send_message_using_vision(self, message: str) -> bool:
        """
        Send a message using Claude Vision to identify input field.
        
        Args:
            message: Message to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try direct approach first
            if self._send_message_direct(message):
                return True
            
            # Take screenshot to analyze if direct approach fails
            send_screenshot = f"{self.screenshots_dir}/send_message_{time.time()}.png"
            self.driver.save_screenshot(send_screenshot)
            
            # Analyze to find input field and send button
            ui_elements = self.claude_assistant.identify_ui_elements(send_screenshot)
            
            if "input_field" in ui_elements:
                # Click input field
                self._click_at_normalized_coordinates(
                    ui_elements["input_field"]["x"],
                    ui_elements["input_field"]["y"]
                )
                time.sleep(0.5)
                
                # Type message
                for chunk in [message[i:i+20] for i in range(0, len(message), 20)]:
                    ActionChains(self.driver).send_keys(chunk).perform()
                    time.sleep(0.2)
                
                # Send message
                if "send_button" in ui_elements:
                    # Click send button
                    self._click_at_normalized_coordinates(
                        ui_elements["send_button"]["x"],
                        ui_elements["send_button"]["y"]
                    )
                else:
                    # Press Enter if no send button
                    ActionChains(self.driver).send_keys(Keys.RETURN).perform()
                
                time.sleep(1)  # Wait for message to send
                
                logger.info(f"Message sent using vision approach: {message[:30]}...")
                return True
                
            logger.error("Could not identify message input field")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            self.driver.save_screenshot(f"{self.screenshots_dir}/send_message_error.png")
            return False
    
    def send_message(self, user_id: str, message: str) -> bool:
        """
        Send a message to a specific user.
        
        Args:
            user_id: ID or username of the recipient
            message: Message to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we're already in a conversation
            current_url = self.driver.current_url
            
            # If not in direct messages, navigate to inbox
            if "/direct/" not in current_url:
                self.driver.get("https://www.instagram.com/direct/inbox/")
                time.sleep(3)
            
            # Try to find the conversation with user_id
            # First with standard approach
            try:
                # Get current conversation username
                current_user_element = self.driver.find_element(By.XPATH, "//div[contains(@class, 'header')]//div[text()]")
                current_username = current_user_element.text
                
                # If we're already in the right conversation, just send
                if user_id.lower() in current_username.lower():
                    return self._send_message_using_vision(message)
            except:
                pass
            
            # Take screenshot to analyze inbox
            inbox_screenshot = f"{self.screenshots_dir}/find_user_{user_id}.png"
            self.driver.save_screenshot(inbox_screenshot)
            
            # Ask Claude to find the user in the conversation list
            prompt = f"""
            Please analyze this Instagram inbox screenshot and find the conversation with user "{user_id}".
            
            Return the coordinates (x, y) of the center of the conversation item, normalized to the image dimensions (0-1 range).
            
            Return a JSON object like:
            {{
              "found": true/false,
              "x": 0.5,
              "y": 0.7
            }}
            
            If you can't find the exact username, try to find the closest match.
            """
            
            result = self.claude_assistant.analyze_screenshot(inbox_screenshot, prompt)
            
            if result.get("found", False):
                # Found the user, click on conversation
                self._click_at_normalized_coordinates(result["x"], result["y"])
                time.sleep(3)
                
                # Send message
                return self._send_message_using_vision(message)
            else:
                logger.warning(f"Could not find user {user_id} in inbox")
                
                # Try a new message approach
                try:
                    # Look for "New Message" or similar button
                    new_message_elements = self.driver.find_elements(By.XPATH, 
                        "//button[contains(text(), 'New') or contains(text(), 'Message')]")
                    
                    if new_message_elements:
                        new_message_elements[0].click()
                        time.sleep(2)
                        
                        # Try to search for user
                        search_field = self.driver.find_element(By.XPATH, "//input[@placeholder='Search...']")
                        search_field.send_keys(user_id)
                        time.sleep(2)
                        
                        # Click first result
                        first_result = self.driver.find_element(By.XPATH, "//div[@role='button'][contains(@class, 'item')]")
                        first_result.click()
                        time.sleep(1)
                        
                        # Click next or similar button
                        next_button = self.driver.find_element(By.XPATH, 
                            "//button[contains(text(), 'Next') or contains(text(), 'Chat')]")
                        next_button.click()
                        time.sleep(2)
                        
                        # Now send message
                        return self._send_message_using_vision(message)
                except Exception as e:
                    logger.error(f"Error creating new conversation with {user_id}: {str(e)}")
                    return False
                
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {str(e)}")
            self.driver.save_screenshot(f"{self.screenshots_dir}/send_to_user_error.png")
            return False
    
    def start_message_monitoring(self):
        """Start monitoring for new messages in a loop."""
        if self.is_running:
            logger.warning("Message monitoring is already running")
            return
            
        try:
            if not self.driver:
                success = self.login()
                if not success:
                    logger.error("Failed to log in, cannot start monitoring")
                    return
            
            logger.info("Starting Instagram message monitoring with Claude Vision...")
            self.is_running = True
            
            while self.is_running:
                try:
                    # Check for new messages
                    new_messages = self.check_new_messages()
                    
                    # Wait before checking again
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in message monitoring loop: {str(e)}")
                    # Take screenshot of the error state
                    self.driver.save_screenshot(f"{self.screenshots_dir}/monitoring_error_{time.time()}.png")
                    
                    # Try to refresh the browser
                    try:
                        self.driver.get("https://www.instagram.com/")
                        time.sleep(3)
                        self.driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(3)
                    except:
                        pass
                        
                    time.sleep(10)  # Wait a bit before retrying
                    
        except KeyboardInterrupt:
            logger.info("Message monitoring stopped by user")
        finally:
            self.is_running = False
            
    def stop_message_monitoring(self):
        """Stop the message monitoring loop."""
        self.is_running = False
        logger.info("Stopping Instagram message monitoring...")
        
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
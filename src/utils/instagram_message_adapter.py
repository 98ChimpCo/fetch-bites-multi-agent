"""
Instagram Message Adapter for the Instagram Recipe Agent.
Handles receiving and sending messages via Instagram DM.
"""

import logging
import time
import os
import json
import re
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

logger = logging.getLogger(__name__)

class MessageTracker:
    """Tracks which messages have been processed to avoid duplication."""
    
    def __init__(self, storage_path="data/processed_messages.json"):
        self.storage_path = storage_path
        self.processed_messages = self._load_processed_messages()
        
    def _load_processed_messages(self):
        """Load the set of processed message IDs from storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.error(f"Error loading processed messages: {str(e)}")
            return set()
    
    def _save_processed_messages(self):
        """Save the set of processed message IDs to storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(list(self.processed_messages), f)
        except Exception as e:
            logger.error(f"Error saving processed messages: {str(e)}")
    
    def is_processed(self, message_id):
        """Check if a message has already been processed."""
        return message_id in self.processed_messages
    
    def mark_processed(self, message_id):
        """Mark a message as processed."""
        self.processed_messages.add(message_id)
        self._save_processed_messages()

class InstagramMessageAdapter:
    """Adapter for interacting with Instagram direct messages."""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        chrome_driver_path: Optional[str] = None,
        headless: bool = False,
        check_interval: int = 60,  # seconds
        message_tracker: Optional[MessageTracker] = None
    ):
        """Initialize the Instagram message adapter.
        
        Args:
            username: Instagram username
            password: Instagram password
            chrome_driver_path: Path to Chrome WebDriver (optional)
            headless: Whether to run in headless mode
            check_interval: How often to check for new messages (seconds)
            message_tracker: Optional MessageTracker instance
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
        
        # Create screenshots directory
        os.makedirs('screenshots', exist_ok=True)
        
    def setup_driver(self) -> webdriver.Chrome:
        """Set up and return a Chrome WebDriver instance.
        
        Returns:
            Chrome WebDriver instance
        """
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        
        # Add anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        if self.chrome_driver_path:
            service = Service(self.chrome_driver_path)
        else:
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set additional anti-detection measures
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """
        })
        
        return driver
        
    def login(self) -> bool:
        """Log in to Instagram.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.driver:
                self.driver = self.setup_driver()
                
            logger.info("Logging in to Instagram...")
            self.driver.get("https://www.instagram.com/")
            
            # Take screenshot before login
            self.driver.save_screenshot("screenshots/before_login.png")
            
            # Wait for cookie dialog and handle it
            try:
                time.sleep(2)
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if "cookie" in body_text:
                    logger.info("Cookie consent dialog detected")
                    accept_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Accept All')]")
                    if accept_buttons:
                        accept_buttons[0].click()
                        time.sleep(1)
            except Exception as e:
                logger.warning(f"Error handling cookie dialog: {str(e)}")
            
            # Wait for login form
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Enter credentials
            self.driver.find_element(By.NAME, "username").send_keys(self.username)
            self.driver.find_element(By.NAME, "password").send_keys(self.password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Handle "Save Login Info" dialog if it appears
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if "save login info" in body_text or "save your login info" in body_text:
                    logger.info("Save Login Info dialog detected")
                    not_now_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Not Now')]")
                    if not_now_buttons:
                        not_now_buttons[0].click()
                        time.sleep(2)
            except Exception as e:
                logger.warning(f"Error handling Save Login Info dialog: {str(e)}")
            
            # Handle "Turn on Notifications" dialog if it appears
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if "notifications" in body_text and "not now" in body_text.lower():
                    logger.info("Notifications dialog detected")
                    not_now_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Not Now')]")
                    if not_now_buttons:
                        not_now_buttons[0].click()
                        time.sleep(2)
            except Exception as e:
                logger.warning(f"Error handling Notifications dialog: {str(e)}")
            
            # Navigate to inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(5)  # Allow page to load fully
            
            # Take screenshot after login
            self.driver.save_screenshot("screenshots/after_login.png")
            
            logger.info("Successfully logged in to Instagram")
            return True
            
        except Exception as e:
            logger.error(f"Error logging in to Instagram: {str(e)}")
            if self.driver:
                self.driver.save_screenshot("screenshots/login_error.png")
            return False
            
    def register_message_handler(self, handler):
        """Register a function to handle incoming messages.
        
        Args:
            handler: Function that takes user_id and message as arguments
                    and returns a response message
        """
        self.message_handlers.append(handler)

    def _find_message_input(self) -> bool:
        """Find and focus the message input field using multiple approaches.
        
        Returns:
            bool: True if input field found and focused, False otherwise
        """
        # Take screenshot before
        self.driver.save_screenshot("screenshots/before_find_input.png")
        
        # Try multiple approaches to find the textarea
        
        # Approach 1: Standard selectors
        try:
            selectors = [
                "textarea[placeholder*='Message']",
                "textarea[aria-label*='Message']",
                "textarea[placeholder]",
                "textarea"
            ]
            
            for selector in selectors:
                try:
                    # Use direct WebDriver find method
                    textarea = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if textarea:
                        textarea.click()
                        time.sleep(0.5)
                        self.driver.save_screenshot("screenshots/input_found_selector.png")
                        return True
                except:
                    continue
        except Exception as e:
            logger.warning(f"Standard selector approach failed: {str(e)}")
        
        # Approach 2: Using JavaScript to find and focus
        try:
            focus_js = """
            function findAndFocusInput() {
                // Various selectors to try
                const selectors = [
                    'textarea[placeholder*="Message"]',
                    'textarea[aria-label*="Message"]', 
                    'textarea[placeholder]',
                    'textarea',
                    'div[role="textbox"]',
                    'div[contenteditable="true"]'
                ];
                
                // Try each selector
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const el of elements) {
                        try {
                            // Try to focus the element
                            el.focus();
                            el.click();
                            
                            // Check if element is now focused
                            if (document.activeElement === el) {
                                return true;
                            }
                        } catch (e) {
                            console.error('Error focusing element:', e);
                        }
                    }
                }
                
                return false;
            }
            
            return findAndFocusInput();
            """
            
            input_found = self.driver.execute_script(focus_js)
            if input_found:
                time.sleep(0.5)
                self.driver.save_screenshot("screenshots/input_found_js.png")
                return True
        except Exception as e:
            logger.warning(f"JavaScript approach failed: {str(e)}")
        
        # Approach 3: Click at the bottom of the chat area using coordinates
        try:
            # Get the size of the viewport
            viewport_size = self.driver.execute_script("""
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                };
            """)
            
            if viewport_size:
                # Click near the bottom center of the screen where the input would typically be
                from selenium.webdriver.common.action_chains import ActionChains
                
                x = viewport_size['width'] // 2
                y = viewport_size['height'] - 100  # 100px from bottom
                
                actions = ActionChains(self.driver)
                actions.move_by_offset(x, y).click().perform()
                time.sleep(0.5)
                
                # Check if we found something we can type into
                active_element_type = self.driver.execute_script("""
                    const active = document.activeElement;
                    return active ? active.tagName : null;
                """)
                
                if active_element_type in ['TEXTAREA', 'INPUT', 'DIV']:
                    self.driver.save_screenshot("screenshots/input_found_coordinates.png")
                    return True
        except Exception as e:
            logger.warning(f"Coordinate approach failed: {str(e)}")
            
        # Take screenshot after all approaches failed
        self.driver.save_screenshot("screenshots/input_not_found.png")
        return False
    
    def find_message_input(self):
        """Find message input field using multiple strategies."""
        try:
            # Try multiple selector approaches
            selectors = [
                "textarea[placeholder='Message...']",
                "div[contenteditable='true']",
                "div[role='textbox']",
                # Add more potential selectors
            ]
            
            for selector in selectors:
                try:
                    # Wait for the element with explicit wait
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    return element
                except Exception:
                    continue
                    
            # JavaScript approach as fallback
            js_script = """
            return document.querySelector("textarea[placeholder='Message...']") || 
                document.querySelector("div[contenteditable='true']") ||
                Array.from(document.querySelectorAll('div')).find(el => 
                    el.getAttribute('role') === 'textbox' || 
                    (el.contentEditable === 'true' && el.isContentEditable))
            """
            element = self.driver.execute_script(js_script)
            if element:
                return element
                
            # Log failure with screenshot for debugging
            self.driver.save_screenshot(f"screenshots/debug_find_input_{time.time()}.png")
            return None
        except Exception as e:
            logger.error(f"Error finding message input: {str(e)}")
            return None

    def check_new_messages(self) -> List[Dict[str, Any]]:
        """Check for new messages in the Instagram inbox, focusing only on unread messages.
        
        Returns:
            List of new messages with user_id and message content
        """
        try:
            # Navigate to inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(3)
            
            # Take a screenshot for debugging
            self.driver.save_screenshot("screenshots/inbox_check.png")
            
            # Find conversations with unread messages using JavaScript
            unread_conversations_js = """
            let results = [];
            try {
                // Get all conversation elements
                const allConvos = Array.from(document.querySelectorAll('div[role="listitem"], div[role="button"]'));
                
                // Filter to only conversations with unread indicators
                results = allConvos
                    .filter(el => {
                        const text = el.textContent && el.textContent.trim();
                        // Look specifically for unread indicators like "New message"
                        return text && (text.includes('New message') || 
                            el.querySelector('.unread-indicator') !== null);
                    })
                    .map((el, index) => ({
                        index: index,
                        text: el.textContent.trim(),
                        hasUnread: true
                    }));
            } catch (e) {
                console.error('Error finding unread conversations:', e);
            }
            return results;
            """
            
            unread_conversations = self.driver.execute_script(unread_conversations_js)
            logger.info(f"Found {len(unread_conversations)} unread conversations")
            
            # Process only unread conversations
            for conversation in unread_conversations:
                self.process_messages_in_conversation(conversation)
            
            # Get all conversations for prioritization
            conversations_js = """
            let results = [];
            try {
                // Get all conversation elements
                const allConvos = Array.from(document.querySelectorAll('div[role="listitem"], div[role="button"]'));
                
                // Get only elements with text content
                results = allConvos
                    .filter(el => {
                        const text = el.textContent && el.textContent.trim();
                        return text && text.length > 0 && 
                               !text.includes('Page Not Found') && 
                               !text.includes('Requests');
                    })
                    .map((el, index) => ({
                        index: index,
                        text: el.textContent.trim(),
                        hasUnread: el.textContent.includes('New message')
                    }));
            } catch (e) {
                console.error('Error finding conversations:', e);
            }
            return results;
            """
            
            conversations = self.driver.execute_script(conversations_js)
            
            # First: "Hello" messages
            hello_conversations = [c for c in conversations if 'hello' in c.get('text', '').lower()]
            
            # Second: Recipe-related conversations
            recipe_indicators = ['recipe', 'food', 'cook', 'bake', 'ingredient', 'kauscooks', 'hungry.happens']
            recipe_conversations = [c for c in conversations if any(indicator in c.get('text', '').lower() for indicator in recipe_indicators)]
            
            # Third: New message conversations
            new_message_conversations = [c for c in conversations if 'new message' in c.get('text', '').lower()]
            
            # Build prioritized list
            prioritized_convos = []
            
            # Add hello conversations first
            for convo in hello_conversations:
                if convo not in prioritized_convos:
                    prioritized_convos.append(convo)
                    
            # Add recipe conversations next
            for convo in recipe_conversations:
                if convo not in prioritized_convos:
                    prioritized_convos.append(convo)
                    
            # Add new message conversations next
            for convo in new_message_conversations:
                if convo not in prioritized_convos:
                    prioritized_convos.append(convo)
                    
            # Add remaining conversations last
            for convo in conversations:
                if convo not in prioritized_convos:
                    prioritized_convos.append(convo)
                    
            # Replace conversations with prioritized list
            conversations = prioritized_convos
            
            new_messages = []
            processed_convos = []
            
            # Process each conversation individually, navigating back to inbox between each
            for convo in conversations[:5]:  # Limit to 5 conversations for performance
                try:
                    if not convo.get('text') or convo.get('index') in processed_convos:
                        continue
                        
                    logger.info(f"Processing conversation: {convo.get('text')[:30]}...")
                    processed_convos.append(convo.get('index'))
                    
                    # Click on conversation using JavaScript to avoid stale element issues
                    click_js = f"""
                    try {{
                        const allConvos = Array.from(document.querySelectorAll('div[role="listitem"], div[role="button"]'));
                        const filtered = allConvos.filter(el => {{
                            const text = el.textContent && el.textContent.trim();
                            return text && text.length > 0;
                        }});
                        
                        if (filtered.length > {convo.get('index')}) {{
                            const convo = filtered[{convo.get('index')}];
                            if (convo) {{
                                convo.click();
                                return true;
                            }}
                        }}
                    }} catch (e) {{
                        console.error('Error clicking conversation:', e);
                    }}
                    return false;
                    """
                    
                    clicked = self.driver.execute_script(click_js)
                    
                    if not clicked:
                        logger.warning(f"Could not click conversation {convo.get('index')}")
                        continue
                        
                    # Wait for conversation to load
                    time.sleep(2)
                    
                    # Take a screenshot of the conversation
                    self.driver.save_screenshot(f"screenshots/conversation_{convo.get('index')}.png")
                    
                    # Extract user ID directly from URL
                    current_url = self.driver.current_url
                    user_id = None
                    
                    if '/t/' in current_url:
                        user_id = current_url.split('/t/')[1].split('/')[0]
                    else:
                        # Try to get user ID from page content
                        user_id_js = """
                        try {
                            const headerTexts = Array.from(document.querySelectorAll('span')).map(s => s.textContent);
                            return headerTexts.find(t => t && t.length > 0 && !t.includes('Instagram') && !t.includes('Back')) || '';
                        } catch (e) {
                            return '';
                        }
                        """
                        
                        potential_id = self.driver.execute_script(user_id_js)
                        if potential_id:
                            user_id = potential_id
                        else:
                            user_id = f"user_{convo.get('index')}"
                    
                    logger.info(f"Identified user: {user_id}")
                    
                    # Enhanced message detection with more detailed selectors
                    messages_js = """
                    try {
                        // Try multiple approaches to find messages
                        let messageElements = [];
                        
                        // Method 1: role=row (most common)
                        messageElements = Array.from(document.querySelectorAll('[role="row"]'));
                        
                        // Method 2: Try message bubbles directly
                        if (!messageElements.length) {
                            const bubbles = document.querySelectorAll('div[style*="background-color"]');
                            if (bubbles.length) messageElements = Array.from(bubbles);
                        }
                        
                        // Method 3: More specific Instagram selectors
                        if (!messageElements.length) {
                            messageElements = Array.from(document.querySelectorAll('div.x9f619 div.x78zum5 div.x1qughib'));
                        }
                        
                        // Method 4: Content divs with width constraints (likely message containers)
                        if (!messageElements.length) {
                            const containers = document.querySelectorAll('div[style*="max-width"]');
                            if (containers.length) messageElements = Array.from(containers);
                        }
                        
                        // Method 5: Fall back to all divs with substantial content
                        if (!messageElements.length) {
                            messageElements = Array.from(document.querySelectorAll('div'))
                                .filter(el => el.textContent && el.textContent.trim().length > 20);
                        }
                        
                        // Extract text content from elements, filtering out empty ones
                        return messageElements
                            .map(el => el.textContent.trim())
                            .filter(text => text && text.length > 0);
                    } catch (e) {
                        console.error('Error getting messages:', e);
                        return [];
                    }
                    """
                    
                    messages = self.driver.execute_script(messages_js)
                    
                    logger.info(f"Found {len(messages)} messages in conversation")
                    
                    # Process the most recent message, with better filtering for actual content
                    if messages and len(messages) > 0:
                        # Get the last 3 messages to find the most recent non-system message
                        recent_messages = messages[-3:] if len(messages) >= 3 else messages
                        
                        # Define system indicators to filter out
                        system_indicators = [
                            "seen", "sent", "delivered", "read", 
                            "active now", "active today", "active yesterday",
                            "notification", "new message", "instagram"
                        ]
                        
                        # Try to find a non-system message
                        valid_message = None
                        for msg in reversed(recent_messages):  # Start from most recent
                            is_system_message = any(indicator in msg.lower() for indicator in system_indicators)
                            if not is_system_message and len(msg) > 3:  # Must be more than 3 chars
                                valid_message = msg
                                break
                        
                        if valid_message:
                            # Found a valid message
                            if "hello" in valid_message.lower():
                                logger.info(f"Found Hello message from {user_id}: {valid_message[:30]}...")
                                
                                new_messages.append({
                                    "user_id": user_id,
                                    "message": "Hello"  # Normalize to just "Hello" for simplicity
                                })
                                
                                # Try to send a response immediately while we're in the conversation
                                for handler in self.message_handlers:
                                    try:
                                        response = handler(user_id, "Hello")
                                        if response:
                                            # Directly send response while in the correct conversation
                                            self._send_message_direct(response)
                                    except Exception as e:
                                        logger.error(f"Error in message handler: {str(e)}")
                            
                            # Check for Instagram recipe content
                            elif any(term in valid_message.lower() for term in ['recipe', 'food', 'cook', 'kauscooks', 'instagram.com/p/']):
                                logger.info(f"Found potential recipe message from {user_id}: {valid_message[:30]}...")
                                
                                new_messages.append({
                                    "user_id": user_id,
                                    "message": valid_message
                                })
                                
                                # Try to send a response immediately while we're in the conversation
                                for handler in self.message_handlers:
                                    try:
                                        response = handler(user_id, valid_message)
                                        if response:
                                            # Directly send response while in the correct conversation
                                            self._send_message_direct(response)
                                    except Exception as e:
                                        logger.error(f"Error in message handler: {str(e)}")
                            
                            # Other valid message
                            else:
                                logger.info(f"Found message from {user_id}: {valid_message[:30]}...")
                                
                                new_messages.append({
                                    "user_id": user_id,
                                    "message": valid_message
                                })
                                
                                # Try to send a response immediately while we're in the conversation
                                for handler in self.message_handlers:
                                    try:
                                        response = handler(user_id, valid_message)
                                        if response:
                                            # Directly send response while in the correct conversation
                                            self._send_message_direct(response)
                                    except Exception as e:
                                        logger.error(f"Error in message handler: {str(e)}")
                    
                    # Go back to inbox
                    self.driver.get("https://www.instagram.com/direct/inbox/")
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing conversation {convo.get('index')}: {str(e)}")
                    # Try to get back to inbox
                    self.driver.get("https://www.instagram.com/direct/inbox/")
                    time.sleep(1)
                    continue
                    
            logger.info(f"Found {len(new_messages)} new messages to process")
            return new_messages
            
        except Exception as e:
            logger.error(f"Error checking new messages: {str(e)}")
            if self.driver:
                self.driver.save_screenshot("screenshots/message_check_error.png")
            return []
            
    def _send_message_direct(self, message: str) -> bool:
        """Send a message in the currently open conversation.
        
        Args:
            message: Message content to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Take screenshot before sending
            self.driver.save_screenshot("screenshots/before_send_direct.png")
            
            # Find and focus the message input field
            if not self._find_message_input():
                logger.error("Could not find message input field")
                return False
            
            # Now the input should be focused, send message with keyboard events
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            
            # Type message in multiple ways to increase chances of success
            
            # Method 1: ActionChains
            try:
                actions = ActionChains(self.driver)
                
                # Clear existing text if any
                actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
                time.sleep(0.2)
                
                # Type message in chunks
                for chunk in [message[i:i+20] for i in range(0, len(message), 20)]:
                    actions = ActionChains(self.driver)
                    actions.send_keys(chunk)
                    actions.perform()
                    time.sleep(0.2)
                
                # Take screenshot after typing
                self.driver.save_screenshot("screenshots/after_typing.png")
                
                # Send message with Enter key
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.RETURN)
                actions.perform()
            except Exception as e:
                logger.warning(f"ActionChains sending failed: {str(e)}")
                
                # Method 2: JavaScript
                try:
                    # Try to send using JavaScript
                    # Properly escape the message for JavaScript
                    escaped_message = message.replace('"', '\\"').replace('\n', '\\n')
                    
                    send_js = """
                    function sendMessage(text) {
                        // Get the active element
                        const active = document.activeElement;
                        
                        if (active) {
                            // For textarea/input elements
                            if (active.tagName === 'TEXTAREA' || active.tagName === 'INPUT') {
                                active.value = text;
                                
                                // Create and dispatch an Enter key event
                                const enterEvent = new KeyboardEvent('keydown', {
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true
                                });
                                
                                active.dispatchEvent(enterEvent);
                                return true;
                            }
                            // For contenteditable divs
                            else if (active.getAttribute('contenteditable') === 'true' || active.getAttribute('role') === 'textbox') {
                                active.textContent = text;
                                
                                // Create and dispatch an Enter key event
                                const enterEvent = new KeyboardEvent('keydown', {
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true
                                });
                                
                                active.dispatchEvent(enterEvent);
                                return true;
                            }
                        }
                        
                        return false;
                    }
                    
                    return sendMessage(arguments[0]);
                    """
                    
                    sent = self.driver.execute_script(send_js, escaped_message)
                    if not sent:
                        raise Exception("JavaScript send failed")
                except Exception as e:
                    logger.warning(f"JavaScript sending failed: {str(e)}")
                    return False
            
            time.sleep(1)
            
            # Take screenshot after sending
            self.driver.save_screenshot("screenshots/after_send_direct.png")
            
            logger.info(f"Message sent directly: {message[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message directly: {str(e)}")
            self.driver.save_screenshot("screenshots/send_direct_error.png")
            return False

    def send_message(self, user_id: str, message: str) -> bool:
        """Send a message to a user.
        
        Args:
            user_id: Instagram username of the recipient
            message: Message content to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we're already in the right conversation
            current_url = self.driver.current_url
            expected_url_fragment = f"/direct/t/{user_id}"
            
            if expected_url_fragment not in current_url:
                # Navigate to the user's conversation
                self.driver.get(f"https://www.instagram.com/direct/t/{user_id}")
                time.sleep(3)
                
            # Take screenshot before sending
            self.driver.save_screenshot("screenshots/before_send.png")
            
            # Use the direct sending method
            return self._send_message_direct(message)
            
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {str(e)}")
            if self.driver:
                self.driver.save_screenshot("screenshots/send_message_error.png")
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
            
            logger.info("Starting Instagram message monitoring...")
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
                    self.driver.save_screenshot("screenshots/monitoring_error.png")
                    
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
            
    def process_messages_in_conversation(self, conversation):
        """Process messages within a conversation, focusing on unread ones."""
        try:
            # Open the conversation if needed
            self._open_conversation(conversation)
            
            # Get all messages in the conversation
            messages_js = """
            let results = [];
            try {
                // Get all message elements
                const allMessages = Array.from(document.querySelectorAll('div[role="row"]'));
                
                // Extract the messages with their details
                results = allMessages.map((el, index) => {
                    // Create a unique identifier based on text content and position
                    const messageText = el.textContent.trim();
                    const messageId = `${messageText.substring(0, 50)}_${index}`;
                    
                    // Check if this message has the unread indicator
                    const isUnread = el.querySelector('.unread-indicator') !== null || 
                                el.classList.contains('unread');
                    
                    return {
                        id: messageId,
                        text: messageText,
                        isUnread: isUnread,
                        index: index
                    };
                });
            } catch (e) {
                console.error('Error finding messages:', e);
            }
            return results;
            """
            
            messages = self.driver.execute_script(messages_js)
            
            # Filter to only unread messages
            unread_messages = [msg for msg in messages if msg.get('isUnread', False)]
            logger.info(f"Found {len(unread_messages)} unread messages in conversation")
            
            # Process only unread messages
            for message in unread_messages:
                message_id = message.get('id')
                
                # Skip if already processed
                if self.message_tracker.is_processed(message_id):
                    continue
                    
                # Process the message
                self._process_message(message)
                
                # Mark as processed
                self.message_tracker.mark_processed(message_id)
            
            # Mark the conversation as read
            self.mark_conversation_as_read()
            
        except Exception as e:
            logger.error(f"Error processing messages in conversation: {str(e)}")

    def _open_conversation(self, conversation):
        """Helper method to open a conversation."""
        try:
            # If conversation is an element, click it
            if hasattr(conversation, 'click'):
                conversation.click()
                time.sleep(2)
            # If conversation is a dictionary with index, use that
            elif isinstance(conversation, dict) and 'index' in conversation:
                # Find and click the conversation at the given index
                conversations = self.driver.find_elements(By.CSS_SELECTOR, 
                    'div[role="listitem"], div[role="button"]')
                if len(conversations) > conversation['index']:
                    conversations[conversation['index']].click()
                    time.sleep(2)
            # Log an error if we can't open the conversation
            else:
                logger.error("Could not open conversation: invalid conversation format")
        except Exception as e:
            logger.error(f"Error opening conversation: {str(e)}")
            
    def has_unread_indicator(self, element):
        """Check if an element has unread indicators."""
        try:
            # Look for common unread indicators
            indicators = [
                '.unread-count',
                '.unread-indicator',
                'div[aria-label="Unread"]',
                'span.unread_count'
            ]
            
            for indicator in indicators:
                if element.find_elements(By.CSS_SELECTOR, indicator):
                    return True
                    
            # Check for CSS classes that might indicate unread
            classes = element.get_attribute('class')
            unread_classes = ['unread', 'has_unread', 'new_message']
            
            for cls in unread_classes:
                if cls in classes:
                    return True
                    
            return False
        except Exception:
            return False

    def mark_conversation_as_read(self):
        """Mark the current conversation as read."""
        try:
            # Scroll to bottom to ensure all messages are loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Instagram usually marks messages as read automatically when viewed
            # But we can also try to find and click any "Mark as Read" buttons
            read_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Mark as read') or contains(@aria-label, 'Mark as read')]")
            
            if read_buttons:
                for button in read_buttons:
                    try:
                        button.click()
                        time.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"Error clicking mark as read button: {str(e)}")
        except Exception as e:
            logger.error(f"Error marking conversation as read: {str(e)}")
            
    def _process_message(self, message):
        """Process a single message."""
        # This should call your existing message processing logic
        # You'll need to adapt this to work with the message format from the JavaScript
        text = message.get('text', '')
        
        # Check if this is a recipe message or other message type
        if self._is_recipe_message(text):
            # Handle recipe message
            self._process_recipe_message(text)
        elif 'hello' in text.lower() or 'hi' in text.lower():
            # Handle greeting
            self._send_welcome_message()
            
    def _is_recipe_message(self, text):
        """Check if a message is recipe-related."""
        if not text:
            return False
            
        # Recipe indicators
        recipe_indicators = [
            'recipe', 'food', 'cook', 'bake', 'ingredient', 
            'kauscooks', 'hungry.happens', 'instagram.com/p/'
        ]
        
        # Check for recipe indicators
        for indicator in recipe_indicators:
            if indicator in text.lower():
                return True
                
        # Check for common recipe patterns (ingredients with measurements)
        measurement_pattern = r'\b\d+(\s+)?(cup|tbsp|tsp|oz|gram|pound|g|kg|ml|l)\b'
        if re.search(measurement_pattern, text.lower()):
            return True
            
        return False
        
    def _process_recipe_message(self, text):
        """Process a recipe message."""
        # Default implementation - should be overridden by subclasses or handlers
        logger.info(f"Processing recipe message: {text[:30]}...")
        
    def _send_welcome_message(self):
        """Send a welcome message."""
        # Default welcome message - should be overridden by subclasses or handlers
        welcome_message = """👋 Hello there, food explorer! I'm Fetch Bites, your personal recipe assistant! 🥘

    I can turn Instagram recipe posts into beautiful, printable recipe cards delivered straight to your inbox! No more screenshots or manually typing out recipes.

    Want to see what I can do? Just send me a link to an Instagram recipe post, and I'll work my magic! ✨

    Or type "help" to learn more about how I work."""
        
        self._send_message_direct(welcome_message)


    # Function to validate email addresses
    def is_valid_email(email):
        """Check if the given string is a valid email address."""
        # More permissive email regex that accepts a wider range of valid formats
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
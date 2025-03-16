import os
import time
import random
import logging
import threading
import json
import re
from typing import Dict, List, Optional, Callable, Any, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from src.utils.claude_vision_assistant import ClaudeVisionAssistant

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class InstagramMessageAdapterVision:
    """
    Adapter for monitoring and responding to Instagram Direct Messages using Claude Vision
    for more reliable UI interaction.
    """
    
    def __init__(
        self, 
        username: str, 
        password: str, 
        message_callback: Callable[[str, str], None],
        anthropic_api_key: Optional[str] = None,
        headless: bool = False
    ):
        """
        Initialize the Instagram Message Adapter.
        
        Args:
            username (str): Instagram username
            password (str): Instagram password
            message_callback (callable): Callback function for received messages
            anthropic_api_key (str, optional): API key for Claude Vision
            headless (bool, optional): Whether to run Chrome in headless mode
        """
        self.username = username
        self.password = password
        self.message_callback = message_callback
        self.anthropic_api_key = anthropic_api_key
        self.headless = headless
        
        self.driver = None
        self.stop_event = threading.Event()
        self.screenshot_dir = "screenshots"
        self.screen_width = 1280
        self.screen_height = 800
        
        # Reset action chain offset
        self.current_offset_x = 0
        self.current_offset_y = 0
        
        # Initialize Claude Vision Assistant
        self.claude_assistant = ClaudeVisionAssistant(anthropic_api_key)
        
        # Create screenshots directory if it doesn't exist
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def _setup_webdriver(self) -> webdriver.Chrome:
        """
        Set up Chrome WebDriver with appropriate options.
        
        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance
        """
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        # Set window size
        chrome_options.add_argument(f"--window-size={self.screen_width},{self.screen_height}")
        
        # Anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-extensions")
        
        # Add random user agent
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Create and configure WebDriver
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # Update browser dimensions
        self.screen_width = driver.execute_script("return window.innerWidth")
        self.screen_height = driver.execute_script("return window.innerHeight")
        logger.info(f"Browser dimensions: {self.screen_width}x{self.screen_height}")
        
        # Execute JavaScript to mask WebDriver properties
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            window.navigator.chrome = {
                runtime: {},
            };
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)
        
        return driver
    
    def _restart_browser(self):
        """Restart the browser in case of severe errors."""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
            
        try:
            self.driver = self._setup_webdriver()
            self.login(self.driver)
        except Exception as e:
            logger.error(f"Failed to restart browser: {str(e)}")
    
    def login(self, driver: webdriver.Chrome) -> bool:
        """
        Log in to Instagram using multiple strategies.
        
        Args:
            driver (webdriver.Chrome): Chrome WebDriver instance
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            logger.info("Logging in to Instagram...")
            driver.get("https://www.instagram.com/")
            time.sleep(random.uniform(3, 5))
            
            # Try finding login elements using standard selectors
            try:
                username_input = driver.find_element(By.NAME, "username")
                password_input = driver.find_element(By.NAME, "password")
                login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                
                # Type with human-like delays
                self._type_humanlike(username_input, self.username)
                self._type_humanlike(password_input, self.password)
                
                # Click login
                login_button.click()
                logger.info("Logged in using standard selectors")
                
                # Wait for home page to load
                time.sleep(random.uniform(8, 12))
                
                # Handle "Save Your Login Info" dialog if it appears
                try:
                    not_now_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                    not_now_button.click()
                    time.sleep(1)
                except:
                    pass
                
                # Handle notifications dialog if it appears
                try:
                    not_now_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                    not_now_button.click()
                except:
                    pass
                
                logger.info("Successfully logged in to Instagram")
                return True
                
            except Exception as e:
                logger.warning(f"Standard login failed: {str(e)}")
                
                # Try alternative login approach
                try:
                    # Use JavaScript to find and fill login form
                    driver.execute_script("""
                        const inputs = document.querySelectorAll('input');
                        const username = Array.from(inputs).find(i => i.getAttribute('name') === 'username' || i.getAttribute('aria-label') === 'Phone number, username, or email');
                        const password = Array.from(inputs).find(i => i.getAttribute('name') === 'password' || i.getAttribute('aria-label') === 'Password');
                        const button = document.querySelector('button[type="submit"]');
                        
                        if (username && password && button) {
                            username.value = arguments[0];
                            password.value = arguments[1];
                            button.click();
                        }
                    """, self.username, self.password)
                    
                    # Wait for home page to load
                    time.sleep(random.uniform(8, 12))
                    
                    # Handle dialogs
                    driver.execute_script("""
                        const notNowButtons = Array.from(document.querySelectorAll('button')).filter(b => 
                            b.textContent.includes('Not Now') || 
                            b.textContent.includes('Skip') || 
                            b.textContent.includes('Not now'));
                        if (notNowButtons.length > 0) {
                            notNowButtons[0].click();
                        }
                    """)
                    
                    logger.info("Successfully logged in with alternative approach")
                    return True
                    
                except Exception as e:
                    logger.error(f"Alternative login failed: {str(e)}")
                    return False
                
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    def _type_humanlike(self, element, text: str):
        """Type text with human-like random delays."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
    
    def _find_conversations(self) -> List[Dict]:
        """
        Find conversations in the Instagram inbox using multiple strategies.
        
        Returns:
            List[Dict]: List of conversations with position information
        """
        try:
            # Take screenshot of inbox for visual analysis
            screenshot_path = f"{self.screenshot_dir}/inbox.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Use Claude Vision to identify conversations
            conversations = self.claude_assistant.get_conversation_list(screenshot_path)
            if conversations:
                return conversations
                
            # Fallback to JavaScript-based detection
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
                    .map((el, index) => {
                        const rect = el.getBoundingClientRect();
                        return {
                            index: index,
                            text: el.textContent.trim(),
                            hasUnread: el.textContent.includes('New message'),
                            x: (rect.left + rect.width/2) / window.innerWidth,
                            y: (rect.top + rect.height/2) / window.innerHeight
                        };
                    });
            } catch (e) {
                console.error('Error finding conversations:', e);
            }
            return results;
            """
            
            js_conversations = self.driver.execute_script(conversations_js)
            if js_conversations:
                return js_conversations
                
            # Final fallback - generic positions for first few conversations
            return [
                {"x": 0.2, "y": 0.15, "text": "Conversation 1", "index": 0},
                {"x": 0.2, "y": 0.25, "text": "Conversation 2", "index": 1},
                {"x": 0.2, "y": 0.35, "text": "Conversation 3", "index": 2},
            ]
            
        except Exception as e:
            logger.error(f"Error finding conversations: {str(e)}")
            return []
    
    def _reset_action_chain(self):
        """Reset the action chain offset tracking."""
        self.current_offset_x = 0
        self.current_offset_y = 0
        
        # Move mouse to top-left to reset
        try:
            actions = ActionChains(self.driver)
            actions.move_by_offset(-self.current_offset_x, -self.current_offset_y).perform()
            self.current_offset_x = 0
            self.current_offset_y = 0
        except:
            # If it fails, just reset the counters
            self.current_offset_x = 0
            self.current_offset_y = 0
    
    def _click_at_coordinates(self, x: int, y: int, retries=3) -> bool:
        """
        Click at absolute coordinates within browser viewport.
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            retries (int): Number of retry attempts
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Ensure coordinates are within viewport
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))
        
        logger.info(f"Clicking at coordinates: ({x}, {y})")
        
        # Reset action chain to avoid compound offsets
        self._reset_action_chain()
        
        for attempt in range(retries):
            try:
                # Strategy 1: Using element click at position
                element = self.driver.execute_script(f"return document.elementFromPoint({x}, {y});")
                if element:
                    element.click()
                    time.sleep(0.5)
                    return True
            except Exception as e:
                logger.warning(f"Element click failed (attempt {attempt+1}): {str(e)}")
                
                try:
                    # Strategy 2: JavaScript click
                    self.driver.execute_script(f"""
                        const element = document.elementFromPoint({x}, {y});
                        if (element) {{
                            element.click();
                        }}
                    """)
                    time.sleep(0.5)
                    return True
                except Exception as e2:
                    logger.warning(f"JavaScript click failed (attempt {attempt+1}): {str(e2)}")
                    
                    try:
                        # Strategy 3: Move and click using actions with absolute positions
                        # First move to origin (0,0)
                        actions = ActionChains(self.driver)
                        actions.move_to_element_with_offset(self.driver.find_element(By.TAG_NAME, "body"), 0, 0)
                        actions.move_by_offset(x, y).click().perform()
                        
                        # Update current position
                        self.current_offset_x = x
                        self.current_offset_y = y
                        
                        time.sleep(0.5)
                        return True
                    except Exception as e3:
                        logger.warning(f"ActionChains click failed (attempt {attempt+1}): {str(e3)}")
        
        logger.error(f"All click attempts failed at coordinates ({x}, {y})")
        return False
    
    def _click_at_normalized_coordinates(self, normalized_x: float, normalized_y: float) -> bool:
        """
        Click at normalized coordinates (0-1 range).
        
        Args:
            normalized_x (float): Normalized X coordinate (0-1)
            normalized_y (float): Normalized Y coordinate (0-1)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Convert normalized to absolute coordinates
        x = int(normalized_x * self.screen_width)
        y = int(normalized_y * self.screen_height)
        
        # Use the absolute coordinate method
        return self._click_at_coordinates(x, y)
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text to ensure it's compatible with ChromeDriver.
        Removes non-BMP Unicode characters that cause issues.
        
        Args:
            text (str): Text to sanitize
            
        Returns:
            str: Sanitized text
        """
        # Remove emojis and other non-BMP characters
        sanitized = ""
        for char in text:
            if ord(char) < 0x10000:  # Only keep BMP characters
                sanitized += char
            else:
                # Replace with a space
                sanitized += " "
        
        return sanitized
    
    def _send_message_direct(self, message: str) -> bool:
        """
        Send a message in the current active conversation.
        
        Args:
            message (str): Message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Sanitize message to avoid Unicode issues
            sanitized_message = self._sanitize_text(message)
            
            # Take screenshot for visual analysis
            screenshot_path = f"{self.screenshot_dir}/conversation.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Use Claude Vision to identify message input field
            ui_elements = self.claude_assistant.identify_ui_elements(screenshot_path)
            
            # Strategy 1: Use DOM selectors
            selectors = [
                "textarea[placeholder='Message...']",
                "div[contenteditable='true']",
                "div[aria-label='Message']",
                "textarea",
                "div[role='textbox']"
            ]
            
            for selector in selectors:
                try:
                    input_fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for input_field in input_fields:
                        if input_field.is_displayed():
                            input_field.click()
                            input_field.clear()
                            input_field.send_keys(sanitized_message)
                            input_field.send_keys(Keys.RETURN)
                            return True
                except Exception as e:
                    logger.warning(f"Selector {selector} failed: {str(e)}")
                    continue
            
            # Strategy 2: JavaScript-based approach
            input_js = """
            // Find input field using various attributes
            const inputSelectors = [
                "textarea[placeholder*='Message']",
                "div[contenteditable='true']",
                "div[aria-label*='Message']",
                "textarea",
                "div[role='textbox']"
            ];
            
            let input = null;
            for (const selector of inputSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const el of elements) {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        input = el;
                        break;
                    }
                }
                if (input) break;
            }
            
            if (input) {
                input.focus();
                return true;
            }
            return false;
            """
            
            if self.driver.execute_script(input_js):
                active_element = self.driver.switch_to.active_element
                active_element.send_keys(sanitized_message)
                active_element.send_keys(Keys.RETURN)
                return True
            
            # Strategy 3: If Claude Vision identified input field, try clicking there
            if ui_elements and "input_field" in ui_elements:
                input_coords = ui_elements["input_field"]
                x = int(input_coords["x"] * self.screen_width)
                y = int(input_coords["y"] * self.screen_height)
                
                if self._click_at_coordinates(x, y):
                    # Wait for field to activate
                    time.sleep(0.5)
                    active_element = self.driver.switch_to.active_element
                    active_element.send_keys(sanitized_message)
                    active_element.send_keys(Keys.RETURN)
                    return True
                
            # Strategy 4: Try clicking near the bottom of the screen where input is usually located
            bottom_center_x = self.screen_width // 2
            bottom_center_y = int(self.screen_height * 0.9)  # 90% down the page
            
            if self._click_at_coordinates(bottom_center_x, bottom_center_y):
                time.sleep(0.5)
                active_element = self.driver.switch_to.active_element
                active_element.send_keys(sanitized_message)
                active_element.send_keys(Keys.RETURN)
                return True
            
            logger.error("Failed to send message: Could not find input field")
            return False
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
    
    def _read_messages_from_conversation(self) -> List[Dict]:
        """
        Read messages from the current active conversation.
        
        Returns:
            List[Dict]: List of messages with sender and content information
        """
        try:
            # Take screenshot for visual analysis
            screenshot_path = f"{self.screenshot_dir}/conversation_messages.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Use Claude Vision to extract messages
            messages = self.claude_assistant.extract_messages(screenshot_path)
            if messages:
                return messages
            
            # If Claude Vision fails, try DOM-based approach
            message_selectors = [
                "div[role='row']",
                "div.x9f619.xjbqb8w",
                "div.x1tlxs6b",
                "div[data-testid='message-container']"
            ]
            
            for selector in message_selectors:
                try:
                    message_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if message_elements:
                        messages = []
                        for element in message_elements:
                            sender = "Unknown"
                            try:
                                sender_element = element.find_element(By.CSS_SELECTOR, "a")
                                sender = sender_element.text
                            except:
                                pass
                                
                            content = element.text
                            if content and len(content) > 0:
                                messages.append({
                                    "sender": sender,
                                    "content": content
                                })
                        return messages
                except Exception as e:
                    logger.warning(f"Failed with selector {selector}: {str(e)}")
                    continue
            
            # JavaScript fallback for message extraction
            messages_js = """
            let messages = [];
            try {
                // Find all message containers
                const selectors = [
                    "div[role='row']",
                    "div.x9f619.xjbqb8w",
                    "div.x1tlxs6b",
                    "div[data-testid='message-container']",
                    // Add dynamic approach to find message elements
                    "div > div > div > div > span"  // Nested spans often contain message text
                ];
                
                let messageElements = [];
                
                // Try each selector
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        messageElements = elements;
                        break;
                    }
                }
                
                // If no selector worked, try a more general approach
                if (messageElements.length === 0) {
                    // Find elements that look like messages
                    const allElements = document.querySelectorAll('div');
                    messageElements = Array.from(allElements).filter(el => {
                        // Message elements usually have text content and are visible
                        const hasText = el.textContent && el.textContent.trim().length > 0;
                        const isVisible = el.offsetWidth > 0 && el.offsetHeight > 0;
                        const isPossiblyMessage = el.clientWidth > 50; // Messages have some minimum width
                        
                        return hasText && isVisible && isPossiblyMessage;
                    });
                }
                
                // Process found elements
                messages = Array.from(messageElements)
                    .filter(el => el.textContent && el.textContent.trim().length > 0)
                    .map(el => {
                        // Try to extract sender
                        let sender = "Unknown";
                        try {
                            const possibleSenderElement = el.querySelector('a');
                            if (possibleSenderElement) {
                                sender = possibleSenderElement.textContent.trim();
                            }
                        } catch(e) {}
                        
                        return {
                            sender: sender,
                            content: el.textContent.trim()
                        };
                    });
            } catch (e) {
                console.error('Error extracting messages:', e);
            }
            return messages;
            """
            
            js_messages = self.driver.execute_script(messages_js)
            if js_messages:
                return js_messages
            
            return []
            
        except Exception as e:
            logger.error(f"Error reading messages: {str(e)}")
            return []
    
    def send_message(self, recipient: str, message: str) -> bool:
        """
        Send a message to a specific recipient.
        
        Args:
            recipient (str): Recipient username
            message (str): Message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Navigate to inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(3)
            
            # Find conversations
            conversations = self._find_conversations()
            
            # Look for recipient in conversations
            recipient_match = None
            for convo in conversations:
                if recipient.lower() in convo.get("text", "").lower():
                    recipient_match = convo
                    break
            
            if recipient_match:
                # Click on conversation
                if "x" in recipient_match and "y" in recipient_match:
                    x = int(recipient_match["x"] * self.screen_width)
                    y = int(recipient_match["y"] * self.screen_height)
                    if self._click_at_coordinates(x, y):
                        time.sleep(2)
                        
                        # Send message
                        return self._send_message_direct(message)
                else:
                    logger.warning(f"Recipient {recipient} found but coordinates missing")
                    return False
            else:
                logger.warning(f"Recipient {recipient} not found in conversations")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {recipient}: {str(e)}")
            return False
    
    def monitor_messages(self, interval_seconds=10):
        """
        Monitor Instagram DMs with improved error recovery.
        
        Args:
            interval_seconds (int): Interval between message checks
        """
        try:
            # Initialize driver if not already done
            if not self.driver:
                self.driver = self._setup_webdriver()
                self.login(self.driver)
            
            logger.info("Starting Instagram message monitoring with Claude Vision...")
            
            while not self.stop_event.is_set():
                try:
                    # Navigate to inbox periodically to refresh
                    if random.random() < 0.2:  # 20% chance to refresh
                        self.driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(3)
                    
                    # Find and process conversations
                    conversations = self._find_conversations()
                    if conversations:
                        logger.info(f"Found {len(conversations)} conversations in inbox")
                        
                        # Process conversations - limit to first few to prevent out-of-bounds issues
                        for i, conversation in enumerate(conversations[:min(3, len(conversations))]):
                            try:
                                # Open conversation - use coordinates if available
                                if "x" in conversation and "y" in conversation:
                                    x = int(conversation["x"] * self.screen_width)
                                    y = int(conversation["y"] * self.screen_height)
                                    success = self._click_at_coordinates(x, y)
                                else:
                                    # Fallback to index-based position
                                    x = int(0.2 * self.screen_width)  # 20% from left
                                    y = int((0.15 + (i * 0.1)) * self.screen_height)  # Position based on index
                                    success = self._click_at_coordinates(x, y)
                                
                                if success:
                                    time.sleep(3)
                                    
                                    # Read messages
                                    messages = self._read_messages_from_conversation()
                                    if messages:
                                        # Process last few messages to avoid processing too many
                                        for message in messages[-3:]:  # Process last 3 messages
                                            try:
                                                # Skip messages from fetch.bites
                                                if message.get("sender", "").lower() != "fetch.bites":
                                                    self.message_callback(message.get("sender", "Unknown"), message.get("content", ""))
                                            except Exception as e:
                                                logger.error(f"Error processing message: {str(e)}")
                                    
                                    # Go back to inbox
                                    try:
                                        # Try clicking back button via several methods
                                        back_button = None
                                        try:
                                            back_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Back']")
                                            back_button.click()
                                            time.sleep(1)
                                        except:
                                            # Try JavaScript approach
                                            back_js = """
                                            const backButtons = Array.from(document.querySelectorAll('button'))
                                                .filter(b => 
                                                    b.textContent.includes('Back') || 
                                                    b.getAttribute('aria-label')?.includes('Back'));
                                            if (backButtons.length > 0) {
                                                backButtons[0].click();
                                                return true;
                                            }
                                            return false;
                                            """
                                            if not self.driver.execute_script(back_js):
                                                # If back button not found, navigate directly to inbox
                                                self.driver.get("https://www.instagram.com/direct/inbox/")
                                    except:
                                        # If all fails, navigate directly to inbox
                                        self.driver.get("https://www.instagram.com/direct/inbox/")
                                    
                                    time.sleep(2)
                            except Exception as e:
                                logger.error(f"Error processing conversation {i}: {str(e)}")
                                # Take recovery action - refresh page
                                self.driver.get("https://www.instagram.com/direct/inbox/")
                                time.sleep(3)
                    
                    # Wait before next check
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Error in message monitoring loop: {str(e)}")
                    # Take recovery action
                    try:
                        self.driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(5)
                    except:
                        # More serious error, try to restart browser
                        self._restart_browser()
                    
                    time.sleep(interval_seconds * 2)  # Wait longer after error
                    
        except Exception as e:
            logger.error(f"Fatal error in monitor_messages: {str(e)}")
        finally:
            logger.info("Stopping Instagram message monitoring...")
    
    def start_monitoring(self, interval_seconds=10):
        """
        Start monitoring Instagram DMs in a separate thread.
        
        Args:
            interval_seconds (int): Interval between message checks
        """
        self.stop_event.clear()
        threading.Thread(target=self.monitor_messages, args=(interval_seconds,), daemon=True).start()
    
    def stop_monitoring(self):
        """Stop monitoring Instagram DMs."""
        logger.info("Message monitoring stopped by user")
        self.stop_event.set()
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.error(f"Error cleaning up: {str(e)}")
            
    def send_welcome_message(self, recipient: str) -> bool:
        """
        Send a welcome message to a specific recipient.
        
        Args:
            recipient (str): Recipient username
            
        Returns:
            bool: True if successful, False otherwise
        """
        welcome_message = "Hello! I'm Fetch Bites, your recipe assistant. I can extract recipes from Instagram posts and create printable recipe cards. Send me a recipe post link to get started!"
        
        # Sanitize message to avoid Unicode issues
        sanitized_message = self._sanitize_text(welcome_message)
        
        return self.send_message(recipient, sanitized_message)
import os
import time
import random
import logging
import threading
import json
import re
import atexit
from typing import Dict, List, Optional, Callable, Any, Tuple, Set

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
        
        # Track processed messages to avoid duplicates
        self.processed_messages = set()
        
        # Initialize Claude Vision Assistant
        self.claude_assistant = ClaudeVisionAssistant(anthropic_api_key)
        
        # Create screenshots directory if it doesn't exist
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Register cleanup handler to ensure browser is closed
        atexit.register(self.cleanup)
    
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
    
    def _create_message_hash(self, sender: str, content: str) -> str:
        """Create a unique hash for a message to track processed messages."""
        # Normalize the message content
        normalized_content = content.strip().lower()
        # Create a hash
        return f"{sender.lower()}:{normalized_content}"
    
    def _read_messages_from_conversation(self) -> List[Dict]:
        """
        Enhanced method to read messages from the current active conversation
        with multiple fallback mechanisms.
        
        Returns:
            List[Dict]: List of messages with sender and content information
        """
        try:
            # Take screenshot for visual analysis
            screenshot_path = f"{self.screenshot_dir}/conversation_messages.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Use Claude Vision to extract messages
            messages = self.claude_assistant.extract_messages(screenshot_path)
            
            if messages and len(messages) > 0:
                logger.info(f"Successfully extracted {len(messages)} messages using Claude Vision")
                return messages
            
            # If Claude Vision fails or returns no messages, try DOM-based approach
            message_containers = []
            message_selectors = [
                "div[role='row']",
                "div.x9f619.xjbqb8w",
                "div.x1tlxs6b",
                "div[data-testid='message-container']",
                "div.x78zum5", 
                "div.x1pi30zi",
                "span[dir='auto']",
                "div[role='textbox']",
            ]
            
            for selector in message_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        message_containers.extend(elements)
                except Exception as e:
                    logger.warning(f"Failed with selector {selector}: {str(e)}")
            
            # If we found elements, process them
            if message_containers:
                messages = []
                for element in message_containers:
                    try:
                        # Skip empty elements
                        if not element.text or len(element.text.strip()) == 0:
                            continue
                            
                        # Try to determine sender
                        sender = "Unknown"
                        try:
                            # Try to find an anchor element that might contain the sender name
                            sender_elements = element.find_elements(By.CSS_SELECTOR, "a, span.username")
                            for sender_elem in sender_elements:
                                if sender_elem.text and len(sender_elem.text.strip()) > 0:
                                    sender = sender_elem.text.strip()
                                    break
                        except:
                            pass
                            
                        content = element.text.strip()
                        
                        # Skip empty content
                        if content:
                            # Check if this element looks like a message
                            if len(content) >= 2 and not content.lower().startswith("active "):
                                messages.append({
                                    "sender": sender,
                                    "content": content
                                })
                    except Exception as e:
                        logger.warning(f"Error processing message element: {str(e)}")
                
                if messages:
                    logger.info(f"Extracted {len(messages)} messages using DOM approach")
                    return messages
            
            # If DOM approach fails, try aggressive JavaScript extraction
            messages_js = """
            let allMessages = [];
            
            try {
                // Try to find all text elements that could be messages
                const textElements = [];
                
                // Find all elements with text content
                function findTextElements(element, depth = 0) {
                    if (depth > 10) return; // Prevent infinite recursion
                    
                    // Skip invisible elements
                    if (element.offsetWidth === 0 || element.offsetHeight === 0) return;
                    
                    // Check if this element has direct text
                    if (element.childNodes) {
                        for (const node of element.childNodes) {
                            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                                textElements.push(element);
                                break;
                            }
                        }
                    }
                    
                    // Recursively check children
                    for (const child of element.children) {
                        findTextElements(child, depth + 1);
                    }
                }
                
                // Start from the main container that likely contains messages
                const mainContainer = document.querySelector('div[role="main"]') || document.body;
                findTextElements(mainContainer);
                
                // Process found text elements
                const processedTexts = new Set();
                
                for (const element of textElements) {
                    const text = element.textContent.trim();
                    
                    // Skip very short texts, already processed texts, or status indicators
                    if (text.length < 2 || 
                        processedTexts.has(text) || 
                        text.toLowerCase().startsWith("active ") ||
                        text.includes("instagram") ||
                        text === "..." ||
                        text === "•" ||
                        text.includes("ago")) {
                        continue;
                    }
                    
                    // Skip UI elements
                    if (text.includes("Home") && text.includes("Search") && text.includes("Explore")) {
                        continue;
                    }
                    
                    // Looks like a real message
                    processedTexts.add(text);
                    
                    // Try to find sender
                    let sender = "Unknown";
                    
                    // Check if this element or its ancestors have a username
                    let current = element;
                    for (let i = 0; i < 5; i++) {
                        if (!current) break;
                        
                        // Check for username in attributes
                        if (current.getAttribute("aria-label") && 
                            current.getAttribute("aria-label").includes("'s message")) {
                            const ariaLabel = current.getAttribute("aria-label");
                            sender = ariaLabel.split("'s message")[0];
                            break;
                        }
                        
                        // Move up the tree
                        current = current.parentElement;
                    }
                    
                    allMessages.push({
                        sender: sender,
                        content: text
                    });
                }
                
                // If we found messages, sort them by their position on the page
                if (allMessages.length > 0) {
                    allMessages.sort((a, b) => {
                        const aEl = textElements[allMessages.indexOf(a)];
                        const bEl = textElements[allMessages.indexOf(b)];
                        const aRect = aEl.getBoundingClientRect();
                        const bRect = bEl.getBoundingClientRect();
                        
                        return aRect.top - bRect.top;
                    });
                }
            } catch (e) {
                console.error("Error extracting messages:", e);
            }
            
            return allMessages;
            """
            
            js_messages = self.driver.execute_script(messages_js)
            if js_messages and len(js_messages) > 0:
                logger.info(f"Extracted {len(js_messages)} messages using aggressive JavaScript")
                return js_messages
            
            # Last resort: Extract all visible text as a single message
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if body_text and len(body_text) > 10:
                    # Try to find message-like content
                    lines = body_text.split('\n')
                    potential_messages = []
                    
                    for line in lines:
                        line = line.strip()
                        # Skip empty or very short lines
                        if not line or len(line) < 3:
                            continue
                            
                        # Skip status indicators, navigation elements
                        if (line.lower().startswith("active ") or 
                            line.lower() in ["home", "search", "explore", "reels", "messages", 
                                            "notifications", "create", "profile"]):
                            continue
                        
                        # This might be a message
                        potential_messages.append({
                            "sender": "Unknown",
                            "content": line
                        })
                    
                    if potential_messages:
                        logger.info(f"Extracted {len(potential_messages)} potential messages from body text")
                        return potential_messages
            except Exception as e:
                logger.warning(f"Failed to extract body text: {str(e)}")
            
            # If we reach here, no messages were found
            logger.warning("No messages found using any extraction method")
            return []
            
        except Exception as e:
            logger.error(f"Error reading messages: {str(e)}")
            return []

    def _process_conversation(self, conversation, index):
        """
        Process a single conversation with enhanced error recovery.
        
        Args:
            conversation (dict): Conversation data
            index (int): Conversation index
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Open conversation - use coordinates if available
            success = False
            if "x" in conversation and "y" in conversation:
                x = int(conversation["x"] * self.screen_width)
                y = int(conversation["y"] * self.screen_height)
                success = self._click_at_coordinates(x, y)
            else:
                # Fallback to index-based position
                x = int(0.2 * self.screen_width)  # 20% from left
                y = int((0.15 + (index * 0.1)) * self.screen_height)  # Position based on index
                success = self._click_at_coordinates(x, y)
            
            if not success:
                logger.warning(f"Failed to open conversation {index}")
                return False
                
            # Wait longer for conversation to load
            time.sleep(4)
            
            # Dismiss any popups that might have appeared
            self.dismiss_popups()
            
            # Read messages - try multiple times to ensure we get messages
            messages = []
            for attempt in range(3):
                messages = self._read_messages_from_conversation()
                if messages and len(messages) > 0:
                    break
                time.sleep(1)
                
            if not messages:
                logger.warning(f"No messages found in conversation {index}")
                # Go back to inbox
                self._navigate_back_to_inbox()
                return False
                
            # Process only the most recent messages to avoid duplicates
            # Use at most the 3 most recent messages
            recent_messages = messages[-3:] if len(messages) > 3 else messages
            
            for message in recent_messages:
                try:
                    # Skip messages from fetch.bites or system messages
                    sender = message.get("sender", "Unknown")
                    content = message.get("content", "")
                    
                    if not content:
                        continue
                        
                    # Skip self messages or system UI elements
                    if self._is_self_message(sender, content):
                        continue
                        
                    # Skip Instagram system messages
                    if (sender.lower() in ["instagram", "meta", "unknown"] and 
                        any(x in content.lower() for x in ["©", "active", "home", "search", "reels", "profile"])):
                        continue
                    
                    # Create a robust message hash
                    message_hash = self._create_robust_message_hash(sender, content)
                    
                    # Skip if already processed
                    if message_hash in self.processed_messages:
                        continue
                        
                    # Mark as processed
                    self.processed_messages.add(message_hash)
                    logger.info(f"Processing new message from {sender}: '{content[:30]}...'")
                    
                    # Process the message
                    self.message_callback(sender, content)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
            
            # Go back to inbox
            return self._navigate_back_to_inbox()
            
        except Exception as e:
            logger.error(f"Error processing conversation {index}: {str(e)}")
            # Try to go back to inbox
            self._navigate_back_to_inbox()
            return False

    def _navigate_back_to_inbox(self):
        """
        Navigate back to the inbox using multiple strategies.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Strategy 1: Try to find and click back button
            back_selectors = [
                "button[aria-label='Back']",
                "a[href='/direct/inbox/']",
                "svg[aria-label='Back']"
            ]
            
            for selector in back_selectors:
                try:
                    back_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if back_button.is_displayed():
                        back_button.click()
                        time.sleep(2)
                        return True
                except:
                    continue
            
            # Strategy 2: JavaScript approach
            back_js = """
            // Find back button or link
            const backButtons = Array.from(document.querySelectorAll('button, a'))
                .filter(b => 
                    b.textContent.includes('Back') || 
                    b.getAttribute('aria-label')?.includes('Back') ||
                    b.href?.includes('/direct/inbox/'));
                    
            if (backButtons.length > 0) {
                backButtons[0].click();
                return true;
            }
            
            // Try to find the back icon
            const svgElements = Array.from(document.querySelectorAll('svg'));
            for (const svg of svgElements) {
                if (svg.innerHTML.includes('polyline') || 
                    svg.getAttribute('aria-label')?.includes('Back')) {
                    // Click the parent element of the SVG (usually the button)
                    svg.parentElement.click();
                    return true;
                }
            }
            
            return false;
            """
            
            if self.driver.execute_script(back_js):
                time.sleep(2)
                return True
            
            # Strategy 3: Direct navigation to inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Error navigating back to inbox: {str(e)}")
            
            # Fallback: direct navigation
            try:
                self.driver.get("https://www.instagram.com/direct/inbox/")
                time.sleep(3)
                return True
            except:
                return False

    def _create_robust_message_hash(self, sender: str, content: str) -> str:
        """
        Create a more robust message hash that's resistant to minor variations.
        
        Args:
            sender (str): Message sender
            content (str): Message content
            
        Returns:
            str: A hash that identifies this message
        """
        import re
        
        # Normalize sender
        normalized_sender = sender.lower().strip()
        if not normalized_sender or normalized_sender in ["unknown", "user"]:
            normalized_sender = "unknown_user"
        
        # Extract just the first few words of content (ignoring timestamps, etc.)
        # This makes the hash more robust against minor content variations
        if content:
            # Remove timestamps and common metadata patterns that might change
            content = re.sub(r'\b\d+[hms] ago\b', '', content.lower())
            content = re.sub(r'\b(active|online|offline)\b', '', content)
            
            # Get just the first 5 words for the hash
            words = content.strip().split()
            if words:
                core_content = ' '.join(words[:min(5, len(words))])
            else:
                core_content = "empty_message"
        else:
            core_content = "empty_message"
        
        # Create a hash that ignores minor variations
        return f"{normalized_sender}:{core_content}"

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
        Enhanced message monitoring with better navigation, error recovery,
        and message reading capabilities.
        
        Args:
            interval_seconds (int): Interval between message checks
        """
        try:
            # Initialize driver if not already done
            if not self.driver:
                self.driver = self._setup_webdriver()
                self.login(self.driver)
            
            logger.info("Starting enhanced Instagram message monitoring...")
            
            # Track conversations to ensure we don't check the same ones repeatedly
            processed_conversations = set()
            conversation_failure_count = {}
            
            # Time when we last found a message
            last_message_time = time.time()
            
            while not self.stop_event.is_set():
                try:
                    # Check stop file
                    if os.path.exists("stop_app.txt"):
                        logger.info("Stop file detected, shutting down...")
                        break
                    
                    # If we haven't found a message in a while, refresh the page
                    current_time = time.time()
                    if current_time - last_message_time > 120:  # 2 minutes
                        logger.info("No messages found in 2 minutes, refreshing inbox")
                        self.driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(3)
                        processed_conversations.clear()  # Reset
                        conversation_failure_count.clear()
                        
                    # Dismiss any popups that might interfere
                    popup_dismissed = self.dismiss_popups()
                    if popup_dismissed:
                        time.sleep(1)  # Give time for UI to settle after popup dismissed
                    
                    # Navigate to inbox with enhanced navigation if needed
                    current_url = self.driver.current_url
                    if "direct/inbox" not in current_url and "direct/t" not in current_url:
                        logger.info("Not on inbox or conversation page, navigating to inbox")
                        if not self.navigate_to_messages():
                            logger.warning("Failed to navigate to messages, retrying...")
                            time.sleep(interval_seconds)
                            continue
                    
                    # Find conversations
                    conversations = self._find_conversations()
                    if not conversations:
                        logger.warning("No conversations found, will retry")
                        self.driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(3)
                        continue
                    
                    logger.info(f"Found {len(conversations)} conversations in inbox")
                    
                    # Check for new/unread conversations first
                    unread_conversations = [c for c in conversations if c.get("hasUnread", False)]
                    
                    # If there are unread conversations, prioritize them
                    if unread_conversations:
                        target_conversations = unread_conversations
                        logger.info(f"Found {len(unread_conversations)} unread conversations")
                    else:
                        # Otherwise, check conversations we haven't checked recently
                        unchecked_conversations = []
                        for i, convo in enumerate(conversations):
                            # Create a hash based on position and text
                            convo_id = f"{i}:{convo.get('text', '')[:20]}"
                            if convo_id not in processed_conversations:
                                unchecked_conversations.append((i, convo))
                        
                        # If all conversations have been checked, start over
                        if not unchecked_conversations:
                            logger.info("All conversations checked, resetting")
                            processed_conversations.clear()
                            time.sleep(interval_seconds)
                            continue
                            
                        # Sort by failure count (ascending) to prioritize ones that haven't failed
                        unchecked_conversations.sort(key=lambda x: conversation_failure_count.get(x[0], 0))
                        target_conversations = [convo for _, convo in unchecked_conversations]
                    
                    # Process each conversation in order of priority
                    for i, conversation in enumerate(target_conversations[:min(3, len(target_conversations))]):
                        # Create a hash to track this conversation
                        convo_id = f"{i}:{conversation.get('text', '')[:20]}"
                        
                        # Process the conversation
                        success = self._process_conversation(conversation, i)
                        
                        # If successful, mark as processed and update last message time
                        if success:
                            processed_conversations.add(convo_id)
                            last_message_time = time.time()
                            conversation_failure_count[i] = 0  # Reset failure count
                        else:
                            # Increment failure count
                            conversation_failure_count[i] = conversation_failure_count.get(i, 0) + 1
                            
                        # Ensure we're back on the inbox page
                        if "direct/inbox" not in self.driver.current_url:
                            self.driver.get("https://www.instagram.com/direct/inbox/")
                            time.sleep(2)
                    
                    # Limit processed messages cache to avoid memory bloat
                    if len(self.processed_messages) > 500:
                        # Keep only the 200 most recent messages
                        self.processed_messages = set(list(self.processed_messages)[-200:])
                    
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
            # Make sure we're stopping monitoring
            self.stop_event.set()
            
            # Attempt to gracefully close the browser
            if self.driver:
                try:
                    self.driver.close()
                except:
                    pass
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
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
    
    def _create_robust_message_hash(sender: str, content: str) -> str:
        """
        Create a more robust message hash that's resistant to minor variations.
        
        Args:
            sender (str): Message sender
            content (str): Message content
            
        Returns:
            str: A hash that identifies this message
        """
        import re
        
        # Normalize sender
        normalized_sender = sender.lower().strip()
        if not normalized_sender or normalized_sender in ["unknown", "user"]:
            normalized_sender = "unknown_user"
        
        # Extract just the first few words of content (ignoring timestamps, etc.)
        # This makes the hash more robust against minor content variations
        if content:
            # Remove timestamps and common metadata patterns that might change
            content = re.sub(r'\b\d+[hms] ago\b', '', content.lower())
            content = re.sub(r'\b(active|online|offline)\b', '', content)
            
            # Get just the first 5 words for the hash
            words = content.strip().split()
            if words:
                core_content = ' '.join(words[:min(5, len(words))])
            else:
                core_content = "empty_message"
        else:
            core_content = "empty_message"
        
        # Create a hash that ignores minor variations
        return f"{normalized_sender}:{core_content}"

    def dismiss_popups(self) -> bool:
        """
        Attempt to dismiss common Instagram popups that might interfere with navigation.
        
        Returns:
            bool: True if any popups were dismissed, False otherwise
        """
        dismissed = False
        
        try:
            # Take screenshot for analysis
            screenshot_path = f"{self.screenshot_dir}/current_screen.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Use Claude Vision to identify popups
            ui_elements = self.claude_assistant.identify_ui_elements(screenshot_path)
            
            # Check for common buttons that would indicate popups
            popup_button_texts = [
                "Not Now", "Skip", "Cancel", "Close", "Maybe Later", 
                "No Thanks", "I Understand", "OK", "Got it", "Continue"
            ]
            
            # JavaScript to find and click popup buttons
            find_buttons_js = """
            const popupTexts = arguments[0];
            let buttonFound = false;
            
            // Find buttons with matching text
            const buttons = Array.from(document.querySelectorAll('button'));
            for (const button of buttons) {
                const text = button.textContent.trim();
                if (popupTexts.some(t => text.includes(t))) {
                    button.click();
                    buttonFound = true;
                    break;
                }
            }
            
            // Try to find "X" close buttons if no text buttons found
            if (!buttonFound) {
                const closeBtns = Array.from(document.querySelectorAll('button, div'))
                    .filter(el => {
                        return (el.textContent === 'X' || el.textContent === '×' || 
                                el.getAttribute('aria-label') === 'Close' ||
                                el.classList.contains('close-btn'));
                    });
                
                if (closeBtns.length > 0) {
                    closeBtns[0].click();
                    buttonFound = true;
                }
            }
            
            return buttonFound;
            """
            
            # Execute the JavaScript to find and click popup buttons
            if self.driver.execute_script(find_buttons_js, popup_button_texts):
                dismissed = True
                time.sleep(1)  # Wait for popup to close
                logger.info("Popup dismissed")
                
            # If Claude Vision found a close button, try clicking it
            if not dismissed and ui_elements and "close_button" in ui_elements:
                x = ui_elements["close_button"]["x"]
                y = ui_elements["close_button"]["y"]
                if self._click_at_normalized_coordinates(x, y):
                    dismissed = True
                    time.sleep(1)
                    logger.info("Popup dismissed via Claude Vision")
                    
            return dismissed
            
        except Exception as e:
            logger.warning(f"Error dismissing popups: {str(e)}")
            return False

    def navigate_to_messages(self) -> bool:
        """
        Navigate to Instagram messages/inbox using multiple strategies.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First try direct URL navigation
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(3)
            
            # Check if we're in the inbox
            if "direct/inbox" in self.driver.current_url:
                return True
                
            # If that fails, try multiple methods to find the messages button
            
            # Method 1: Use standard selector for messages button
            try:
                message_selectors = [
                    "a[href='/direct/inbox/']",
                    "a[aria-label='Messenger']",
                    "a[aria-label='Messages']",
                    "svg[aria-label='Messenger']",
                    "svg[aria-label='Messages']"
                ]
                
                for selector in message_selectors:
                    try:
                        messages_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if messages_button.is_displayed():
                            messages_button.click()
                            time.sleep(2)
                            return True
                    except:
                        continue
                        
            except Exception as e:
                logger.warning(f"Standard selector for messages button failed: {str(e)}")
            
            # Method 2: Use JavaScript to find the messages button
            try:
                find_messages_js = """
                // Find links to inbox
                const inboxLinks = Array.from(document.querySelectorAll('a'))
                    .filter(a => a.href && a.href.includes('/direct/inbox'));
                    
                if (inboxLinks.length > 0) {
                    inboxLinks[0].click();
                    return true;
                }
                
                // Find by aria-label
                const messageBtns = Array.from(document.querySelectorAll('a, button, div'))
                    .filter(el => {
                        return el.getAttribute('aria-label') === 'Messages' || 
                            el.getAttribute('aria-label') === 'Messenger';
                    });
                    
                if (messageBtns.length > 0) {
                    messageBtns[0].click();
                    return true;
                }
                
                // Find by icon
                const paperPlaneIcons = Array.from(document.querySelectorAll('svg'))
                    .filter(svg => {
                        return svg.innerHTML.includes('paper-plane') || 
                            svg.innerHTML.includes('message');
                    });
                    
                if (paperPlaneIcons.length > 0) {
                    // Click the parent or grandparent of the icon
                    let clickTarget = paperPlaneIcons[0];
                    for (let i = 0; i < 3; i++) {
                        if (clickTarget.tagName === 'A' || clickTarget.tagName === 'BUTTON') {
                            break;
                        }
                        clickTarget = clickTarget.parentElement;
                    }
                    clickTarget.click();
                    return true;
                }
                
                return false;
                """
                
                if self.driver.execute_script(find_messages_js):
                    time.sleep(2)
                    return True
                    
            except Exception as e:
                logger.warning(f"JavaScript method for messages button failed: {str(e)}")
                
            # Method 3: Use Claude Vision to locate the messages button
            screenshot_path = f"{self.screenshot_dir}/home_screen.png"
            self.driver.save_screenshot(screenshot_path)
            
            ui_elements = self.claude_assistant.identify_ui_elements(screenshot_path)
            
            # Check if Claude Vision found a messages button
            if ui_elements and "messages_button" in ui_elements:
                x = ui_elements["messages_button"]["x"]
                y = ui_elements["messages_button"]["y"]
                if self._click_at_normalized_coordinates(x, y):
                    time.sleep(2)
                    return True
            
            # Method 4: Try clicking on possible message icons based on position
            # Common positions for messages in Instagram UI
            potential_positions = [
                (0.9, 0.15),  # Top right
                (0.065, 0.47),  # Left sidebar messenger icon
                (0.5, 0.1)  # Header area
            ]
            
            for pos_x, pos_y in potential_positions:
                if self._click_at_normalized_coordinates(pos_x, pos_y):
                    time.sleep(2)
                    # Verify if we navigated to inbox
                    if "direct/inbox" in self.driver.current_url:
                        return True
            
            logger.error("Failed to navigate to messages")
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to messages: {str(e)}")
            return False

    def _is_self_message(self, sender: str, content: str) -> bool:
        """
        Check if a message appears to be from the bot itself.
        
        Args:
            sender (str): Message sender
            content (str): Message content
            
        Returns:
            bool: True if this is likely a self-message, False otherwise
        """
        # Check if sender is our account
        if sender.lower() == self.username.lower():
            return True
            
        # Check for bot identifier phrases that would indicate our own messages
        bot_phrases = [
            "I'm Fetch Bites",
            "your recipe assistant",
            "turn Instagram recipe posts into",
            "beautiful, printable recipe cards",
            "send me a link to an Instagram recipe post",
            "work my magic",
            "type \"help\" to learn more"
        ]
    
        return any(phrase.lower() in content.lower() for phrase in bot_phrases)
    
    def __del__(self):
        """Destructor to ensure resources are cleaned up."""
        self.cleanup()
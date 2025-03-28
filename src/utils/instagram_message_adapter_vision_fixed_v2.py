import sys
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
from src.utils.email_simulator import mock_send_email

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def extract_email_from_message(text: str) -> Optional[str]:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return match.group(0) if match else None
    

def process_post(post_url: str) -> bool:
    from src.agents.instagram_monitor import InstagramMonitor
    from src.agents.recipe_extractor import RecipeExtractor
    from src.utils.pdf_utils import generate_pdf_and_return_path

    logger.info(f"Processing post: {post_url}")
    monitor = InstagramMonitor()
    content = monitor.extract_post_content(post_url)

    if not content or not content.get("caption"):
        logger.warning("Failed to extract content or caption from post.")
        return False

    extractor = RecipeExtractor()
    recipe = extractor.extract_recipe(content["caption"])

    if not recipe:
        logger.warning("Failed to extract recipe from caption.")
        return False

    try:
        pdf_path = generate_pdf_and_return_path(recipe)
        logger.info(f"PDF successfully generated at: {pdf_path}")
        return True
    except Exception as e:
        logger.warning(f"PDF generation failed: {e}")
        return False
    
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
        
        logger.info("InstagramMessageAdapterVision initialized.")

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
    
    def _find_unread_conversations(self):
        """
        Dynamically find unread conversations by looking for DOM elements
        that represent new messages in Instagram DMs.
        Returns a list of clickable WebElements, not coordinates.
        """
        try:
            unread_threads = self.driver.find_elements(By.XPATH, '//div[@aria-label="Unread"]')
            if not unread_threads:
                logger.info("No unread threads found via aria-label, trying fallback selector...")
                unread_threads = self.driver.find_elements(By.XPATH, '//div[contains(@aria-label, "new message")]')

            if not unread_threads:
                logger.info("Still no unread threads found using fallback.")
            else:
                logger.info(f"Found {len(unread_threads)} unread thread(s)")

            return unread_threads
        except Exception as e:
            logger.error(f"Error locating unread conversations: {e}")
            return []
            
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

    def _extract_post_url_from_attachment(self, conversation_html: str) -> Optional[str]:
        """
        Extract Instagram post URL from a shared post/reel in a conversation.
        
        Args:
            conversation_html (str): HTML content of the conversation
            
        Returns:
            str or None: Extracted post URL or None if not found
        """
        try:
            # First try to extract using JavaScript directly
            post_url_js = """
            function findPostUrl() {
                // Look for shared post containers
                const sharedPosts = document.querySelectorAll('div[role="button"]');
                
                for (const element of sharedPosts) {
                    // Check if this element contains an Instagram post link
                    const links = element.querySelectorAll('a');
                    for (const link of links) {
                        if (link.href && 
                            (link.href.includes('/p/') || 
                            link.href.includes('/reel/') || 
                            link.href.includes('/tv/'))) {
                            return link.href;
                        }
                    }
                    
                    // Sometimes the URL is in a data attribute or onclick handler
                    const dataAttributes = element.getAttributeNames();
                    for (const attr of dataAttributes) {
                        if (attr.startsWith('data-')) {
                            const value = element.getAttribute(attr);
                            if (value && 
                                (value.includes('/p/') || 
                                value.includes('/reel/') || 
                                value.includes('/tv/'))) {
                                // Extract the URL using regex
                                const urlMatch = value.match(/(https?:\/\/[^\s'"]+instagram\.com\/(?:p|reel|tv)\/[^\s'"]+)/);
                                if (urlMatch) return urlMatch[1];
                            }
                        }
                    }
                    
                    // Check onclick attributes
                    const onclickValue = element.getAttribute('onclick');
                    if (onclickValue && 
                        (onclickValue.includes('/p/') || 
                        onclickValue.includes('/reel/') || 
                        onclickValue.includes('/tv/'))) {
                        const urlMatch = onclickValue.match(/(https?:\/\/[^\s'"]+instagram\.com\/(?:p|reel|tv)\/[^\s'"]+)/);
                        if (urlMatch) return urlMatch[1];
                    }
                    
                    // Check if this element contains an image that might be from a post
                    const images = element.querySelectorAll('img');
                    for (const img of images) {
                        const src = img.getAttribute('src');
                        // Sometimes the post ID is in the image src
                        if (src && src.includes('instagram')) {
                            // Look for parent elements that might have the post link
                            let parent = img.parentElement;
                            for (let i = 0; i < 5; i++) {
                                if (!parent) break;
                                
                                const onclick = parent.getAttribute('onclick');
                                if (onclick && 
                                    (onclick.includes('/p/') || 
                                    onclick.includes('/reel/') || 
                                    onclick.includes('/tv/'))) {
                                    const urlMatch = onclick.match(/(https?:\/\/[^\s'"]+instagram\.com\/(?:p|reel|tv)\/[^\s'"]+)/);
                                    if (urlMatch) return urlMatch[1];
                                }
                                
                                parent = parent.parentElement;
                            }
                        }
                    }
                }
                
                // If we still haven't found anything, try a more generic approach
                // Look for elements that might be interactive (shared posts usually are)
                const interactiveElements = document.querySelectorAll('[role="button"], [tabindex="0"]');
                for (const element of interactiveElements) {
                    // Check if the element contains the word "shared" or "sent" indicating it's a shared post
                    const text = element.textContent.toLowerCase();
                    if ((text.includes('shared') || text.includes('sent')) && 
                        (text.includes('post') || text.includes('reel') || text.includes('video'))) {
                        // This is likely a shared post container, now try to extract the post ID
                        // Instagram post IDs typically contain a mix of letters, numbers, and underscores
                        const idPattern = /\/([A-Za-z0-9_-]{11,})\//;
                        const match = element.innerHTML.match(idPattern);
                        if (match) {
                            const postId = match[1];
                            // Construct the post URL based on the ID
                            return `https://www.instagram.com/p/${postId}/`;
                        }
                    }
                }
                
                return null;
            }
            
            return findPostUrl();
            """
            
            post_url = self.driver.execute_script(post_url_js)
            if post_url:
                logger.info(f"Found post URL in attachment: {post_url}")
                return post_url
                
            # If JavaScript approach fails, take a screenshot and try to use Claude Vision
            screenshot_path = f"{self.screenshot_dir}/shared_post.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Use Claude Vision to analyze the screenshot and look for a post URL
            logger.info("Using Claude Vision to identify shared post")
            
            # Inject this prompt for Claude Vision
            prompt = """
            This is a screenshot of an Instagram Direct Message conversation with a shared post or reel.
            
            I'm trying to extract the Instagram post or reel URL from this shared content.
            
            Look for any visual indicators of a shared post/reel, such as:
            1. A thumbnail/preview image of a post
            2. A play button indicating a video
            3. UI elements typical of shared Instagram content
            
            If you can identify an Instagram post or reel in this image, provide the following information:
            1. Is this a shared Instagram post or reel? (yes/no)
            2. Any visible post ID or URL parts you can see
            3. Any username that might be associated with the post
            4. Any caption text visible from the post
            5. Is this content likely to be a recipe? Look for food images, cooking instructions, ingredients list, etc.
            
            Format your response as JSON:
            {
                "is_shared_post": true/false,
                "post_id": "post ID if visible",
                "username": "username if visible",
                "caption_snippet": "any visible caption text",
                "is_recipe": true/false,
                "confidence": 0-100
            }
            """
            
            analysis = self.claude_assistant.analyze_instagram_content(screenshot_path)
            
            # Process Claude's analysis
            if analysis and analysis.get("is_shared_post") and analysis.get("post_id"):
                post_id = analysis.get("post_id")
                # Construct URL from post ID
                constructed_url = f"https://www.instagram.com/p/{post_id}/"
                logger.info(f"Constructed post URL from Claude Vision analysis: {constructed_url}")
                return constructed_url
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting post URL from attachment: {str(e)}")
            return None
    
    def _process_conversation(self, conversation, index):
        """
        Process a single conversation with improved attachment and message handling.
        
        Args:
            conversation (dict): Conversation data
            index (int): Conversation index
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Open conversation - use coordinates if available
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
            time.sleep(3)

            # Try clicking the shared post preview before analyzing
            expanded = self._expand_shared_post()
            # === Fallback: Claude Vision click ===
            screenshot_path = f"{self.screenshot_dir}/shared_preview_search_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            
            coords = self.claude_assistant.find_shared_post_coordinates(screenshot_path)
            if coords:
                x = int(coords["x"] * self.screen_width)
                y = int(coords["y"] * self.screen_height)
                self._click_at_coordinates(x, y)
                time.sleep(2)
                logger.info("Fallback click via Claude Vision was attempted.")
                return True
            
            logger.warning("Fallback click failed — skipping this conversation after cooldown.")
            time.sleep(5)
            return False
            
            try:
                # Try locating the first shared post/reel preview via DOM
                shared_post_previews = self.driver.find_elements(By.XPATH, '//article//div[contains(@style,"background-image")] | //div[contains(@aria-label, "Post") or contains(@aria-label, "Reel")]')

                if shared_post_previews:
                    logger.info(f"Found {len(shared_post_previews)} candidate post previews")
                    for candidate in shared_post_previews:
                        try:
                            if candidate.is_displayed():
                                candidate.click()
                                logger.info("Clicked on shared post preview successfully.")
                                time.sleep(2)
                                return True
                        except Exception as e:
                            logger.warning(f"Click attempt failed: {e}")

                if shared_post_preview:
                    shared_post_preview.click()
                    time.sleep(2)  # Let the post expand fully
                    logger.info("Clicked on shared post preview successfully.")
            except Exception as e:
                logger.warning(f"Could not click shared post preview: {e}")
            
            # Dismiss any popups that might have appeared
            self.dismiss_popups()
            
            # First, take a screenshot for analysis
            screenshot_path = f"{self.screenshot_dir}/conversation_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Use Claude Vision to analyze the focused shared post
            analysis = self._process_shared_post_preview()
            if analysis is None:
                logger.warning("Analysis object is None, skipping...")
                return False
            
            # If we found a recipe and have a post URL, process it
            post_url = analysis.get('post_url')
            if not post_url or not post_url.startswith("http") or "unable to determine" in post_url.lower():
                logger.warning("Post URL not available or unclear in Claude analysis")
                post_url = None
            
            if analysis.get('contains_recipe', False) and post_url:
                confidence = analysis.get('confidence', 0)
                logger.info(f"Found recipe post with {confidence}% confidence: {post_url}")
                
                # Process the post using test_workflow
                try:
                    # Import here to avoid circular imports
                    # First save the current directory
                    current_dir = os.getcwd()
                    
                    # Add a delay to let Chrome stabilize
                    time.sleep(1)
                    
                    # Import the function
                    # from manual_post_tester import process_post
                    # process_post is now defined locally in this file

                    if not post_url.startswith("http"):
                        logger.warning(f"Post URL invalid, skipping: {post_url}")
                        return False
                    # Process the post
                    recipe_success = process_post(post_url)
                    
                    if recipe_success:
                        logger.info(f"Successfully processed recipe from post: {post_url}")
                        # Send a confirmation message back to the user
                        self._send_message_direct(
                            "I've found a recipe in the post you shared and created a recipe card! "
                            "Would you like me to send it to your email?"
                        )
                    else:
                        logger.warning(f"Failed to process recipe from post: {post_url}")
                        # Let the user know we encountered an issue
                        self._send_message_direct(
                            "I detected a recipe in the post you shared, but couldn't process it successfully. "
                            "Could you please share a different recipe post?"
                        )
                except Exception as e:
                    logger.error(f"Error processing recipe post: {str(e)}")
                    self._send_message_direct(
                        "I encountered an error while processing the recipe post. "
                        "Could you please try sharing a different recipe?"
                    )
            elif analysis.get('contains_recipe', False) and not post_url:
                logger.warning("Recipe detected but couldn't extract post URL")
                # Try JavaScript-based URL extraction as fallback
                try:
                    post_url_js = """
                    function findPostUrl() {
                        // Look for shared post elements
                        const sharedContentElements = document.querySelectorAll('div[role="button"]');
                        for (const el of sharedContentElements) {
                            // Check if it has an image (shared posts usually do)
                            const hasImage = el.querySelectorAll('img').length > 0;
                            // Check if it has any recipe-like text
                            const text = el.textContent.toLowerCase();
                            const hasRecipeIndicators = 
                                text.includes('recipe') || 
                                text.includes('ingredients') || 
                                text.includes('cook') ||
                                text.includes('bake') ||
                                text.includes('cup') ||
                                text.includes('tbsp');
                                
                            if (hasImage && hasRecipeIndicators) {
                                // This might be a shared post - check for links
                                const links = el.querySelectorAll('a');
                                for (const link of links) {
                                    if (link.href && (link.href.includes('/p/') || link.href.includes('/reel/'))) {
                                        return link.href;
                                    }
                                }
                                
                                // If no direct link found, try to extract from onclick handlers
                                if (el.onclick || el.getAttribute('onclick')) {
                                    const onclickText = el.getAttribute('onclick') || el.onclick.toString();
                                    const urlMatch = onclickText.match(/https:\/\/www\.instagram\.com\/(p|reel)\/([A-Za-z0-9_-]+)/);
                                    if (urlMatch) {
                                        return urlMatch[0];
                                    }
                                }
                                
                                // Check for post ID in data attributes
                                const postIdMatch = Array.from(el.attributes)
                                    .filter(attr => attr.name.startsWith('data-'))
                                    .map(attr => attr.value.match(/([A-Za-z0-9_-]{10,})/))
                                    .filter(Boolean)[0];
                                    
                                if (postIdMatch) {
                                    return `https://www.instagram.com/p/${postIdMatch[1]}/`;
                                }
                            }
                        }
                        return null;
                    }
                    return findPostUrl();
                    """
                    js_url = self.driver.execute_script(post_url_js)
                    
                    if js_url:
                        logger.info(f"Found post URL using JavaScript: {js_url}")
                        post_url = js_url
                        
                        # Now process this URL
                        #from manual_post_tester import process_post
                        # process_post is now defined locally in this file

                        recipe_success = process_post(post_url)
                        
                        if recipe_success:
                            logger.info(f"Successfully processed recipe from post: {post_url}")
                            self._send_message_direct(
                                "I've found a recipe in the post you shared and created a recipe card! "
                                "Would you like me to send it to your email?"
                            )
                        else:
                            logger.warning(f"Failed to process recipe from post: {post_url}")
                            self._send_message_direct(
                                "I detected a recipe in the post you shared, but couldn't process it successfully. "
                                "Could you please share a different recipe post?"
                            )
                    else:
                        logger.warning("Failed to extract post URL even with JavaScript")
                        self._send_message_direct(
                            "I detected a recipe in the post, but couldn't access it. "
                            "Could you please share the recipe as a direct link instead?"
                        )
                        
                except Exception as e:
                    logger.error(f"JavaScript URL extraction failed: {str(e)}")
                    self._send_message_direct(
                        "I can see there's a recipe in the post you shared, but I'm having trouble accessing it. "
                        "Could you please copy and share the direct link to the recipe post?"
                    )
                    
            # Process regular messages as well
            messages = self._read_messages_from_conversation()
            
            if not messages:
                logger.warning(f"No messages found in conversation {index}")
                # Go back to inbox
                self._navigate_back_to_inbox()
                return False
            
            # Get only the latest unprocessed message
            latest_message = self._get_latest_message(messages)
            
            message_text = latest_message.get("content", "")
            email_candidate = extract_email_from_message(message_text)

            if email_candidate:
                logger.info(f"Detected email in conversation: {email_candidate}")

                if hasattr(self, "latest_generated_pdf_path") and self.latest_generated_pdf_path:
                    from src.utils.email_simulator import mock_send_email
                    mock_send_email(to=email_candidate, attachment=self.latest_generated_pdf_path)
                else:
                    logger.warning("User sent email, but no PDF was available to send.")

            # New logic to route the message via structured handler
            from src.dm_router import handle_incoming_dm
            
            if latest_message:
                sender = latest_message.get("sender", "Unknown")
                content = latest_message.get("content", "")
                
                dm_data = {
                    "from": sender,
                    "message": content,
                    "screenshot_path": screenshot_path,  # already captured above
                    "html_block": None  # Add if you capture DOM HTML
                }
                
                try:
                    logger.info(f"Routing message from {sender} through handle_incoming_dm()")
                    handled = handle_incoming_dm(dm_data)
                    if not handled:
                        logger.warning("DM router could not handle this message.")
                except Exception as e:
                    logger.error(f"Error while routing message to DM handler: {e}")
            else:
                logger.info("No new messages to process in this conversation")
            
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
        # Normalize sender
        normalized_sender = sender.lower().strip()
        if not normalized_sender or normalized_sender in ["unknown", "user"]:
            normalized_sender = "unknown_user"
        
        # Extract just the first few words of content
        if content:
            # Remove timestamps and common metadata patterns
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

    def _get_latest_message(self, messages):
        """
        Extract only the newest unprocessed message from a conversation.
        
        Args:
            messages (List[Dict]): List of messages in the conversation
            
        Returns:
            Dict or None: The newest unprocessed message or None
        """
        if not messages:
            return None
            
        # Sort messages by timestamp if available
        # Instagram often displays newest messages at the bottom
        # So the last message in the list is likely the newest
        latest_message = messages[-1]
        
        # Extract sender and content
        sender = latest_message.get("sender", "Unknown")
        content = latest_message.get("content", "")
        
        # Skip if empty or system message
        if not content or self._is_ui_element(content) or self._is_self_message(sender, content):
            return None
            
        # Create fingerprint for deduplication
        fingerprint = self._create_message_fingerprint(sender, content)
        
        # Skip if already processed
        if fingerprint in self.processed_messages:
            return None
            
        # Add to processed messages
        self.processed_messages.add(fingerprint)
        
        # Return the latest message
        return latest_message

    def _create_message_fingerprint(self, sender, content):
        """Create a unique fingerprint for a message to avoid duplicates."""
        # Clean the content and sender
        clean_sender = sender.lower().strip() if sender else "unknown"
        clean_content = content.lower().strip() if content else ""
        
        # Remove common volatile elements like timestamps
        clean_content = re.sub(r'\b\d+[hms] ago\b', '', clean_content)
        clean_content = re.sub(r'\b(active|online|offline)\b', '', clean_content)
        
        # Create a concise fingerprint
        words = clean_content.split()
        content_sample = ' '.join(words[:min(10, len(words))])
        
        # Include length as part of the fingerprint
        content_length = len(clean_content)
        
        # Create the fingerprint
        return f"{clean_sender}:{content_sample}:{content_length}"
    
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
    
    def _is_ui_element(self, content: str) -> bool:
        """Check if content appears to be UI element text rather than an actual message."""
        if not content:
            return True
            
        ui_indicators = [
            "close", "escape", "↑", "up", "↓", "down", "active", "online", 
            "seen", "read", "delivered", "typing", "home", "search", "explore"
        ]
        
        # Clean and normalize content
        normalized = content.lower().strip()
        
        # Very short texts are likely UI elements
        if len(normalized) < 3:
            return True
            
        # Check for UI indicators
        for indicator in ui_indicators:
            if indicator in normalized:
                return True
                
        # Check for timestamp patterns
        timestamp_pattern = r'\b\d+[hms] ago\b'
        if re.search(timestamp_pattern, normalized):
            return True
            
        return False

    def monitor_messages(self, interval_seconds=10):
        """
        Enhanced message monitoring focused on unread messages first.
        
        Args:
            interval_seconds (int): Interval between message checks
        """
        try:
            # Initialize driver if not already done
            if not self.driver:
                self.driver = self._setup_webdriver()
                self.login(self.driver)
            
            logger.info("Starting Instagram message monitoring...")
            
            # Track processed conversations
            processed_messages = set()
            
            while not self.stop_event.is_set():
                try:
                    # Check for stop file
                    if os.path.exists("stop_app.txt"):
                        logger.info("Stop file detected, shutting down...")
                        break
                        
                    # Navigate to inbox
                    if "direct/inbox" not in self.driver.current_url:
                        self.driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(3)
                    
                    # First check for unread conversations
                    unread_conversations = self._find_unread_conversations()
                    
                    if unread_conversations:
                        logger.info(f"Found {len(unread_conversations)} unread conversations")
                        # Process unread conversations first
                        for i, conversation in enumerate(unread_conversations):
                            self._process_conversation(conversation, i)
                    else:
                        # If no unread, check a few regular conversations
                        conversations = self._find_conversations()
                        if conversations:
                            logger.info(f"Found {len(conversations)} conversations")
                            # Just check the first few
                            for i, conversation in enumerate(conversations[:2]):
                                self._process_conversation(conversation, i)
                    
                    # Wait before next check
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Error in message monitoring loop: {str(e)}")
                    try:
                        self.driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(5)
                    except:
                        self._restart_browser()
                    time.sleep(interval_seconds * 2)
                    
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

        logger.info("Monitoring loop started.")

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

    def _process_shared_post_preview(self):
        """
        Focus the Instagram shared post (e.g., video/reel/photo), take a screenshot,
        analyze it with Claude, then dismiss the overlay.
        """
        try:
            # STEP 1: Click the shared post preview
            logger.info("Attempting to click the shared post preview for enhanced vision context...")
            shared_post = self.driver.find_element(By.XPATH, '//div[@role="button" and .//img]')
            shared_post.click()
            time.sleep(3)

            # STEP 2: Take focused screenshot
            focused_screenshot = f"{self.screenshot_dir}/focused_post_{int(time.time())}.png"
            self.driver.save_screenshot(focused_screenshot)
            logger.info(f"Captured focused post screenshot at {focused_screenshot}")

            # STEP 3: Analyze with Claude
            analysis = self.claude_assistant.analyze_instagram_content(focused_screenshot)
            logger.info(f"Claude analysis result from focused view: {analysis}")

            # STEP 4: Dismiss post overlay
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
            logger.info("Dismissed focused post view")
            return analysis

        except Exception as e:
            logger.warning(f"Could not analyze focused post preview: {str(e)}<truncated__content/>")

    def _expand_shared_post(self) -> bool:
        """
        Attempt to expand a shared Instagram post in a conversation via DOM and fallback to Claude Vision.
        Returns True if successful, False otherwise.
        """
        logger.info("Looking for shared post preview...")

        # Try DOM click first
        try:
            post_candidates = self.driver.find_elements(
                By.XPATH,
                '//div[contains(@style, "background-image") and not(contains(@style, "svg"))]'
            )

            if post_candidates:
                logger.info(f"Found {len(post_candidates)} shared post preview candidate(s)")
                for candidate in post_candidates:
                    try:
                        if candidate.is_displayed():
                            candidate.click()
                            logger.info("Clicked on shared post preview successfully.")
                            time.sleep(2)
                            return True
                    except Exception as e:
                        logger.warning(f"Post preview DOM click failed: {e}")
            else:
                logger.warning("No shared post previews found.")
        except Exception as e:
            logger.warning(f"Error during DOM preview click: {e}")

        # Fallback to Claude Vision
        logger.info("Falling back to Vision to click post preview...")
        screenshot_path = f"{self.screenshot_dir}/shared_preview_search_{int(time.time())}.png"
        self.driver.save_screenshot(screenshot_path)

        try:
            coords = self.claude_assistant.find_shared_post_coordinates(screenshot_path)
            if coords:
                x = int(coords["x"] * self.screen_width)
                y = int(coords["y"] * self.screen_height)
                self._click_at_coordinates(x, y)
                logger.info("Fallback click via Claude Vision was attempted.")
                time.sleep(2)
                return True
            else:
                logger.warning("Claude Vision could not find shared post coordinates.")
        except Exception as e:
            logger.error(f"Vision fallback failed: {e}")

        # Save screenshot for debugging
        fail_path = f"{self.screenshot_dir}/unopened_preview_{int(time.time())}.png"
        self.driver.save_screenshot(fail_path)
        logger.warning(f"Tried all post previews but none opened an overlay. Saved screenshot to {fail_path}")
        return False
            
    def run_adapter():
        """
        Entry point for running the Instagram Message Adapter.
        Instantiates the adapter with example credentials and starts monitoring.
        """
        # Replace with actual credentials and callback as needed
        adapter = InstagramMessageAdapterVision(
            username="your_username",
            password="your_password",
            message_callback=lambda sender, message: print(f"Message from {sender}: {message}"),
            headless=False
        )
        adapter.start_monitoring()

    if __name__ == "__main__":
        run_adapter()
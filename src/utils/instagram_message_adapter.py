"""
Instagram Message Adapter for the Instagram Recipe Agent.
Handles receiving and sending messages via Instagram DM.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

class InstagramMessageAdapter:
    """Adapter for interacting with Instagram direct messages."""
    
    def __init__(
        self,
        username: str,
        password: str,
        chrome_driver_path: Optional[str] = None,
        headless: bool = False,
        check_interval: int = 60  # seconds
    ):
        """Initialize the Instagram message adapter.
        
        Args:
            username: Instagram username
            password: Instagram password
            chrome_driver_path: Path to Chrome WebDriver (optional)
            headless: Whether to run in headless mode
            check_interval: How often to check for new messages (seconds)
        """
        self.username = username
        self.password = password
        self.chrome_driver_path = chrome_driver_path
        self.headless = headless
        self.check_interval = check_interval
        self.driver = None
        self.is_running = False
        self.message_handlers = []
        
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
        
        if self.chrome_driver_path:
            service = Service(self.chrome_driver_path)
        else:
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=options)
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
            
            # Wait for login form
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Enter credentials
            self.driver.find_element(By.NAME, "username").send_keys(self.username)
            self.driver.find_element(By.NAME, "password").send_keys(self.password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/direct/inbox')]"))
            )
            
            # Navigate to inbox
            self.driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(3)  # Allow page to load
            
            logger.info("Successfully logged in to Instagram")
            return True
            
        except Exception as e:
            logger.error(f"Error logging in to Instagram: {str(e)}")
            if self.driver:
                self.driver.save_screenshot("login_error.png")
            return False
            
    def register_message_handler(self, handler):
        """Register a function to handle incoming messages.
        
        Args:
            handler: Function that takes user_id and message as arguments
                    and returns a response message
        """
        self.message_handlers.append(handler)
        
    def check_new_messages(self) -> List[Dict[str, Any]]:
        """Check for new messages in the Instagram inbox.
        
        Returns:
            List of new messages with user_id and message content
        """
        try:
            # Navigate to inbox if not already there
            if "/direct/inbox/" not in self.driver.current_url:
                self.driver.get("https://www.instagram.com/direct/inbox/")
                time.sleep(2)
                
            # Look for unread message indicators
            unread_conversations = self.driver.find_elements(
                By.XPATH, 
                "//div[contains(@class, 'unread')]"
            )
            
            new_messages = []
            
            for conversation in unread_conversations:
                try:
                    # Click on the conversation
                    conversation.click()
                    time.sleep(1)
                    
                    # Get user ID (username)
                    user_id_elem = self.driver.find_element(
                        By.XPATH, 
                        "//div[contains(@role, 'dialog')]//h1"
                    )
                    user_id = user_id_elem.text
                    
                    # Get the most recent messages
                    message_elems = self.driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'message-container')]//div[contains(@class, 'message-content')]"
                    )
                    
                    if message_elems:
                        # Get the most recent message
                        message = message_elems[-1].text
                        new_messages.append({
                            "user_id": user_id,
                            "message": message
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing conversation: {str(e)}")
                    continue
                    
            return new_messages
            
        except Exception as e:
            logger.error(f"Error checking new messages: {str(e)}")
            return []
            
    def send_message(self, user_id: str, message: str) -> bool:
        """Send a message to a user.
        
        Args:
            user_id: Instagram username of the recipient
            message: Message content to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Navigate to the user's DM
            self.driver.get(f"https://www.instagram.com/direct/t/{user_id}")
            time.sleep(2)
            
            # Find message input field
            message_input = self.driver.find_element(
                By.XPATH,
                "//textarea[contains(@placeholder, 'Message')]"
            )
            
            # Type message (send in chunks to avoid rate limiting)
            for chunk in [message[i:i+20] for i in range(0, len(message), 20)]:
                message_input.send_keys(chunk)
                time.sleep(0.3)
                
            # Press enter to send
            message_input.send_keys("\n")
            time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {str(e)}")
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
                    
                    # Process new messages
                    for message_data in new_messages:
                        user_id = message_data["user_id"]
                        message = message_data["message"]
                        
                        logger.info(f"New message from {user_id}: {message}")
                        
                        # Call all registered handlers
                        for handler in self.message_handlers:
                            try:
                                response = handler(user_id, message)
                                if response:
                                    self.send_message(user_id, response)
                            except Exception as e:
                                logger.error(f"Error in message handler: {str(e)}")
                    
                    # Wait before checking again
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in message monitoring loop: {str(e)}")
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
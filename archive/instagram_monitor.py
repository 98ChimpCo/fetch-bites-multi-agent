# src/agents/instagram_monitor.py
import os
import time
import json
import re
import logging
import random
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add handler if none exist to prevent duplicates
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class InstagramMonitor:
    """
    Instagram Monitor Agent for extracting content from Instagram posts
    """
    
    def __init__(self, options=None):
        """
        Initialize Instagram monitor agent
        
        Args:
            options (dict, optional): Configuration options
        """
        # Default options
        self.options = {
            'headless': False,
            'use_cookies': True,
            'screenshot_dir': 'screenshots',
            'timeout': 30,
            'wait_time': 5,
            'max_retries': 3
        }
        
        # Update with provided options
        if options:
            self.options.update(options)
        
        # Load credentials from environment
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Instagram credentials not found in environment variables")
        
        # Create screenshot directory
        self.screenshot_dir = self.options['screenshot_dir']
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Initialize WebDriver to None - will be created when needed
        self.driver = None
        self.logged_in = False
        self.cookies_loaded = False

    def _setup_webdriver(self):
        """
        Set up Selenium WebDriver with appropriate options
        
        Returns:
            WebDriver: Configured WebDriver instance
        """
        try:
            options = webdriver.ChromeOptions()
            
            # Add anti-detection measures
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--start-maximized")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Set headless mode if configured
            if self.options['headless']:
                options.add_argument("--headless")
                options.add_argument("--window-size=1920,1080")
            
            # Create the WebDriver
            driver = webdriver.Chrome(options=options)
            
            # Set additional preferences to appear more human-like
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });
                """
            })
            
            # Set page load timeout
            driver.set_page_load_timeout(self.options['timeout'])
            
            logger.info("WebDriver set up successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to set up WebDriver: {str(e)}")
            raise

    def login(self, driver=None):
        """
        Login to Instagram
        
        Args:
            driver (WebDriver, optional): Existing WebDriver instance
            
        Returns:
            bool: True if login successful, False otherwise
        """
        # Use provided driver or create one
        if not driver:
            if not self.driver:
                self.driver = self._setup_webdriver()
            driver = self.driver
        
        if self.logged_in:
            logger.info("Already logged in to Instagram")
            return True
        
        try:
            logger.info("Logging in to Instagram...")
            
            # Navigate to Instagram
            driver.get("https://www.instagram.com/")
            
            # Try to load cookies if enabled
            if self.options['use_cookies'] and not self.cookies_loaded:
                if self._load_cookies(driver):
                    # Test if cookies worked by checking for login state
                    if self._check_login_state(driver):
                        logger.info("Successfully logged in with cookies")
                        self.logged_in = True
                        self.cookies_loaded = True
                        return True
                    else:
                        logger.info("Cookie login failed, proceeding with manual login")
                else:
                    logger.info("No valid cookies found, proceeding with manual login")
            
            # Handle cookie consent dialog if present
            self._handle_cookie_dialog(driver)
            
            # Wait for login page to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
            except TimeoutException:
                logger.warning("Username field not found with standard selector, trying JavaScript approach")
                
                # Take screenshot for debugging
                screenshot_path = os.path.join(self.screenshot_dir, "login_page.png")
                driver.save_screenshot(screenshot_path)
                
                # Use JavaScript to find and interact with login form
                login_script = """
                const usernameField = document.querySelector('input[name="username"]') || 
                                      document.querySelector('input[autocomplete="username"]');
                
                const passwordField = document.querySelector('input[name="password"]') || 
                                      document.querySelector('input[type="password"]');
                                      
                if (!usernameField || !passwordField) {
                    return false;
                }
                
                usernameField.value = arguments[0];
                passwordField.value = arguments[1];
                
                // Find and click login button
                const loginButton = Array.from(document.querySelectorAll('button')).find(
                    button => button.textContent.includes('Log In') || 
                             button.textContent.includes('Log in') || 
                             button.type === 'submit'
                );
                
                if (loginButton) {
                    loginButton.click();
                    return true;
                }
                
                return false;
                """
                
                login_successful = driver.execute_script(login_script, self.username, self.password)
                
                if not login_successful:
                    logger.error("Could not find login form elements")
                    return False
            
            # If we get here, we're using the standard approach
            try:
                # Enter username and password
                username_input = driver.find_element(By.NAME, "username")
                password_input = driver.find_element(By.NAME, "password")
                
                # Clear fields and enter credentials
                username_input.clear()
                username_input.send_keys(self.username)
                
                password_input.clear()
                password_input.send_keys(self.password)
                
                # Click login button
                login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
            except Exception as e:
                logger.error(f"Error interacting with login form: {str(e)}")
                return False
            
            # Wait for login to complete
            time.sleep(5)
            
            # Handle "Save Login Info" dialog
            self._handle_save_login_dialog(driver)
            
            # Handle "Turn on Notifications" dialog
            self._handle_notifications_dialog(driver)
            
            # Verify login was successful
            if self._check_login_state(driver):
                logger.info("Successfully logged in to Instagram")
                self.logged_in = True
                
                # Save cookies for future use
                if self.options['use_cookies']:
                    self._save_cookies(driver)
                
                return True
            else:
                logger.error("Login verification failed")
                
                # Take screenshot for debugging
                screenshot_path = os.path.join(self.screenshot_dir, "login_failed.png")
                driver.save_screenshot(screenshot_path)
                
                return False
        
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, "login_error.png")
            driver.save_screenshot(screenshot_path)
            
            return False

    def _check_login_state(self, driver):
        """
        Check if we're logged in
        
        Args:
            driver (WebDriver): WebDriver instance
            
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, "login_verification.png")
            driver.save_screenshot(screenshot_path)
            
            # Try multiple approaches to verify login
            
            # 1. Check for typical elements that appear after successful login
            login_indicators = [
                (By.CSS_SELECTOR, "svg[aria-label='Home']"),
                (By.CSS_SELECTOR, "svg[aria-label='Direct']"),
                (By.CSS_SELECTOR, "a[href='/direct/inbox/']"),
                (By.CSS_SELECTOR, "a[href='/explore/']")
            ]
            
            for selector_type, selector in login_indicators:
                try:
                    # Short timeout for each check
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    return True
                except:
                    continue
            
            # 2. Check URL
            if "instagram.com/accounts/login" not in driver.current_url:
                # 3. Check for login button (it shouldn't be present if logged in)
                try:
                    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                    login_text = login_button.text.lower()
                    
                    # If login button contains "log in" text, we're not logged in
                    if "log in" in login_text or "login" in login_text:
                        return False
                except:
                    # No login button found, might be logged in
                    pass
                
                # 4. Look for content that would only be present when logged in
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                    if "log out" in body_text or "logout" in body_text:
                        return True
                    
                    if ("suggested for you" in body_text or 
                        "following" in body_text or 
                        "activity feed" in body_text):
                        return True
                except:
                    pass
            
            # Default to not logged in if none of the checks passed
            return False
        
        except Exception as e:
            logger.error(f"Error checking login state: {str(e)}")
            return False

    def _handle_cookie_dialog(self, driver):
        """
        Handle cookie consent dialog if it appears
        
        Args:
            driver (WebDriver): WebDriver instance
        """
        try:
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, "before_cookie_dialog.png")
            driver.save_screenshot(screenshot_path)
            
            # Check if cookie dialog exists by looking for text
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            if "cookie" in body_text or "cookies" in body_text:
                logger.info("Cookie consent dialog detected")
                
                # Try clicking the accept button using different methods
                try:
                    # Method 1: Find button by text
                    accept_script = """
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const acceptButton = buttons.find(button => 
                        button.textContent.includes('Accept') || 
                        button.textContent.includes('Allow') ||
                        button.textContent.includes('Agree')
                    );
                    
                    if (acceptButton) {
                        acceptButton.click();
                        return true;
                    }
                    return false;
                    """
                    
                    accepted = driver.execute_script(accept_script)
                    
                    if accepted:
                        logger.info("Clicked accept button on cookie dialog")
                        time.sleep(1)
                    else:
                        # Method 2: Try standard selectors
                        cookie_buttons = [
                            (By.XPATH, "//button[contains(text(), 'Accept')]"),
                            (By.XPATH, "//button[contains(text(), 'Allow')]"),
                            (By.XPATH, "//button[contains(text(), 'Agree')]"),
                            (By.CSS_SELECTOR, "button.primary"),
                            (By.CSS_SELECTOR, "button.accept")
                        ]
                        
                        for selector_type, selector in cookie_buttons:
                            try:
                                button = driver.find_element(selector_type, selector)
                                button.click()
                                logger.info(f"Clicked cookie dialog button with {selector}")
                                time.sleep(1)
                                break
                            except:
                                continue
                
                except Exception as e:
                    logger.warning(f"Error handling cookie dialog: {str(e)}")
                
                logger.info("Attempted to dismiss cookie dialog")
                
                # Take screenshot after cookie dialog
                screenshot_path = os.path.join(self.screenshot_dir, "after_cookie_dialog.png")
                driver.save_screenshot(screenshot_path)
        
        except Exception as e:
            logger.warning(f"Error checking for cookie dialog: {str(e)}")

    def _handle_save_login_dialog(self, driver):
        """
        Handle "Save Login Info" dialog if it appears
        
        Args:
            driver (WebDriver): WebDriver instance
        """
        try:
            # Wait for the dialog to potentially appear
            time.sleep(2)
            
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, "save_login_dialog.png")
            driver.save_screenshot(screenshot_path)
            
            # Check if dialog exists by looking for text
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            if "save login info" in body_text or "save your login info" in body_text:
                logger.info("Save Login Info dialog detected")
                
                # Try clicking the Not Now button
                try:
                    # Method 1: Find button by text
                    not_now_script = """
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const notNowButton = buttons.find(button => 
                        button.textContent.includes('Not Now') || 
                        button.textContent.includes('Not now') ||
                        button.textContent.includes('Cancel') ||
                        button.textContent.includes('Later')
                    );
                    
                    if (notNowButton) {
                        notNowButton.click();
                        return true;
                    }
                    return false;
                    """
                    
                    clicked = driver.execute_script(not_now_script)
                    
                    if clicked:
                        logger.info("Clicked Not Now button on Save Login Info dialog")
                        time.sleep(1)
                    else:
                        # Method 2: Try standard selectors
                        not_now_buttons = [
                            (By.XPATH, "//button[contains(text(), 'Not Now')]"),
                            (By.XPATH, "//button[contains(text(), 'Not now')]"),
                            (By.XPATH, "//button[contains(text(), 'Cancel')]"),
                            (By.XPATH, "//button[contains(text(), 'Later')]")
                        ]
                        
                        for selector_type, selector in not_now_buttons:
                            try:
                                button = driver.find_element(selector_type, selector)
                                button.click()
                                logger.info(f"Clicked Save Login Info dialog button with {selector}")
                                time.sleep(1)
                                break
                            except:
                                continue
                
                except Exception as e:
                    logger.warning(f"Error handling Save Login Info dialog: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Error checking for Save Login Info dialog: {str(e)}")

    def _handle_notifications_dialog(self, driver):
        """
        Handle turn on notifications dialog if it appears
        
        Args:
            driver (WebDriver): WebDriver instance
        """
        try:
            # Wait for the dialog to potentially appear
            time.sleep(2)
            
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, "notifications_dialog.png")
            driver.save_screenshot(screenshot_path)
            
            # Check if dialog exists by looking for text
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            if "turn on notifications" in body_text or "enable notifications" in body_text:
                logger.info("Notifications dialog detected")
                
                # Try clicking the Not Now button
                try:
                    # Method 1: Find button by text
                    not_now_script = """
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const notNowButton = buttons.find(button => 
                        button.textContent.includes('Not Now') || 
                        button.textContent.includes('Not now') ||
                        button.textContent.includes('Cancel') ||
                        button.textContent.includes('Later')
                    );
                    
                    if (notNowButton) {
                        notNowButton.click();
                        return true;
                    }
                    return false;
                    """
                    
                    clicked = driver.execute_script(not_now_script)
                    
                    if clicked:
                        logger.info("Clicked Not Now button on notifications dialog")
                        time.sleep(1)
                    else:
                        # Method 2: Try standard selectors
                        not_now_buttons = [
                            (By.XPATH, "//button[contains(text(), 'Not Now')]"),
                            (By.XPATH, "//button[contains(text(), 'Not now')]"),
                            (By.XPATH, "//button[contains(text(), 'Cancel')]"),
                            (By.XPATH, "//button[contains(text(), 'Later')]")
                        ]
                        
                        for selector_type, selector in not_now_buttons:
                            try:
                                button = driver.find_element(selector_type, selector)
                                button.click()
                                logger.info(f"Clicked notifications dialog button with {selector}")
                                time.sleep(1)
                                break
                            except:
                                continue
                
                except Exception as e:
                    logger.warning(f"Error handling notifications dialog: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Error checking for notifications dialog: {str(e)}")

    def _save_cookies(self, driver):
        """
        Save cookies for future use
        
        Args:
            driver (WebDriver): WebDriver instance
        """
        try:
            # Create cookies directory if it doesn't exist
            os.makedirs('cookies', exist_ok=True)
            
            # Get cookies
            cookies = driver.get_cookies()
            
            # Save cookies to file
            with open('cookies/instagram_cookies.json', 'w') as f:
                json.dump(cookies, f)
            
            logger.info("Cookies saved successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error saving cookies: {str(e)}")
            return False

    def _load_cookies(self, driver):
        """
        Load cookies from file
        
        Args:
            driver (WebDriver): WebDriver instance
            
        Returns:
            bool: True if cookies loaded successfully, False otherwise
        """
        try:
            # Check if cookie file exists
            if not os.path.exists('cookies/instagram_cookies.json'):
                return False
            
            # Load cookies from file
            with open('cookies/instagram_cookies.json', 'r') as f:
                cookies = json.load(f)
            
            # Ensure we're on Instagram domain before setting cookies
            current_url = driver.current_url
            if "instagram.com" not in current_url:
                driver.get("https://www.instagram.com/")
                time.sleep(2)
            
            # Add cookies to browser
            for cookie in cookies:
                # Handle cookies without expiry
                if 'expiry' in cookie:
                    # Some drivers have issues with cookies' expiry format
                    try:
                        # Convert to int if it's float
                        cookie['expiry'] = int(cookie['expiry'])
                    except:
                        # Remove expiry if it causes problems
                        del cookie['expiry']
                
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Could not add cookie {cookie.get('name')}: {str(e)}")
            
            # Refresh the page
            driver.refresh()
            time.sleep(3)
            
            logger.info("Cookies loaded successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error loading cookies: {str(e)}")
            return False

    def extract_post_content(self, post_url_or_content, max_retries=3):
        """
        Extract content from an Instagram post URL or shared content
        
        Args:
            post_url_or_content (str): URL of the Instagram post or shared content
            max_retries (int): Maximum number of retries for extraction
            
        Returns:
            dict: Post content with caption, username, etc. or None if failed
        """
        # Check if input is a valid URL or direct content
        is_url = post_url_or_content.startswith('http')
        
        # Handle direct content (not a URL)
        if not is_url:
            logger.info("Processing direct content share rather than URL...")
            
            # Create a content object from the shared post
            content = {
                'caption': post_url_or_content,
                'username': self._extract_username_from_content(post_url_or_content),
                'hashtags': self._extract_hashtags_from_content(post_url_or_content),
                'recipe_indicators': self._check_recipe_indicators(post_url_or_content),
                'urls': self._extract_urls_from_content(post_url_or_content),
                'source': {
                    'platform': 'Instagram',
                    'url': 'Direct share',
                    'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            caption_length = len(content.get('caption', '')) if content.get('caption') else 0
            url_count = len(content.get('urls', [])) if content.get('urls') else 0
            logger.info(f"Extracted direct content ({caption_length} chars) and {url_count} URLs")
            
            return content
        
        # Handle URL-based extraction with existing code
        driver = None
        try:
            # Set up WebDriver if not already done
            if not self.driver:
                driver = self._setup_webdriver()
                self.login(driver)
            else:
                driver = self.driver
                
            logger.info(f"Extracting content from {post_url_or_content}...")
            
            # Implement retry logic with longer timeouts
            for attempt in range(max_retries):
                try:
                    # Navigate to the post with longer timeout
                    driver.get(post_url_or_content)
                    
                    # Take screenshot for debugging
                    screenshot_path = os.path.join(self.screenshot_dir, f"post_load_attempt_{attempt}.png")
                    driver.save_screenshot(screenshot_path)
                    
                    # Instead of waiting for specific elements, wait for the page to stabilize
                    # This is a more general approach that works even if the specific elements we expect aren't there
                    try:
                        # Wait for page to have loaded enough content to be useful
                        # This checks if a main element like body has a substantial amount of content
                        WebDriverWait(driver, 20).until(
                            lambda d: len(d.find_element(By.TAG_NAME, "body").text) > 100
                        )
                        
                        # Add a short sleep to allow dynamic content to finish loading
                        time.sleep(5)
                    except TimeoutException:
                        logger.warning(f"Page content loading timeout on attempt {attempt+1}/{max_retries}")
                        if attempt == max_retries - 1:
                            # On last attempt, try to extract what we can anyway
                            pass
                        else:
                            # On earlier attempts, retry
                            continue
                    
                    # Take another screenshot after waiting
                    screenshot_path = os.path.join(self.screenshot_dir, f"post_loaded_{attempt}.png")
                    driver.save_screenshot(screenshot_path)
                    
                    # Use a more comprehensive approach that extracts ALL text content
                    # rather than looking for specific elements
                    content = self._extract_comprehensive(driver)
                    
                    # Add debugging info about what we found
                    if content:
                        caption_length = len(content.get('caption', '')) if content.get('caption') else 0
                        url_count = len(content.get('urls', [])) if content.get('urls') else 0
                        logger.info(f"Extracted caption ({caption_length} chars) and {url_count} URLs")
                        
                        # If we have content with either a substantial caption or URLs, consider it successful
                        if (caption_length > 50 or url_count > 0):
                            return content
                    
                    # If we get here, we need to retry
                    logger.warning(f"Attempt {attempt+1}/{max_retries} failed to extract useful content")
                    time.sleep(3)  # Wait before retry
                    
                except TimeoutException:
                    logger.warning(f"Timeout on attempt {attempt+1}/{max_retries}")
                    time.sleep(3)  # Wait before retry
                    continue
                except Exception as e:
                    logger.warning(f"Error on attempt {attempt+1}/{max_retries}: {str(e)}")
                    time.sleep(3)  # Wait before retry
                    continue
            
            # If we get here, all retries failed
            logger.error("Post content extraction failed after all retries")
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract post content: {str(e)}")
            return None
        finally:
            # Only close the driver if we created it in this method
            if driver and driver != self.driver:
                driver.quit()

    def _extract_username_from_content(self, content):
        """Extract Instagram username from content.
        
        Args:
            content (str): Content to extract username from
            
        Returns:
            str: Extracted username or 'unknown'
        """
        # Try to find @username format
        username_match = re.search(r'@([\w\.]+)', content)
        if username_match:
            return username_match.group(1)
        
        # Look for known usernames
        known_usernames = ['kauscooks', 'hungry.happens', 'foodie', 'recipe']
        for username in known_usernames:
            if username.lower() in content.lower():
                return username
        
        # Try to extract username from content structure
        lines = content.split('\n')
        if lines and len(lines) > 0:
            first_line = lines[0].strip()
            # If first line is short, it might be a username
            if 0 < len(first_line) < 30 and ' ' not in first_line:
                return first_line
                
        return 'unknown'
        
    def _extract_hashtags_from_content(self, content):
        """Extract hashtags from content.
        
        Args:
            content (str): Content to extract hashtags from
            
        Returns:
            list: List of extracted hashtags
        """
        hashtags = []
        hashtag_pattern = r'#(\w+)'
        matches = re.findall(hashtag_pattern, content)
        if matches:
            hashtags.extend(matches)
        return hashtags

    def _extract_urls_from_content(self, content):
        """Extract URLs from content.
        
        Args:
            content (str): Content to extract URLs from
            
        Returns:
            list: List of extracted URLs
        """
        urls = []
        url_pattern = r'https?://[^\s)>]+'
        matches = re.findall(url_pattern, content)
        if matches:
            urls.extend(matches)
        return urls

    def _check_recipe_indicators(self, content):
        """Check if content contains recipe indicators.
        
        Args:
            content (str): Content to check
            
        Returns:
            bool: True if content contains recipe indicators
        """
        # Keywords that suggest a recipe post
        recipe_keywords = [
            'recipe', 'ingredients', 'instructions', 
            'cook', 'bake', 'roast', 'fry', 'grill', 'boil',
            'tbsp', 'tsp', 'cup', 'cups', 'oz', 'pound', 'lb',
            'minute', 'hour', 'heat', 'oven', 'stove', 'simmer',
            'mix', 'stir', 'whisk', 'blend', 'combine'
        ]
        
        # Check content for recipe keywords
        content_lower = content.lower()
        keyword_count = sum(1 for keyword in recipe_keywords if keyword in content_lower)
        
        # Recipe structure indicators
        has_ingredient_list = bool(re.search(r'ingredients?:', content, re.IGNORECASE))
        has_instruction_list = bool(re.search(r'(instructions?|directions?|steps?|method):', content, re.IGNORECASE))
        has_numbered_steps = bool(re.search(r'([1-9][0-9]?\.|[1-9][0-9]?\))', content))
        has_measurements = bool(re.search(r'([0-9]+\s*(cup|tbsp|tsp|oz|g|kg|ml|l))', content, re.IGNORECASE))
        
        # Return True if sufficient indicators are present
        return keyword_count >= 2 or has_ingredient_list or has_instruction_list or has_numbered_steps or has_measurements

    def _extract_comprehensive(self, driver):
        """
        Extract ALL text content and URLs from a post using JavaScript
        
        Args:
            driver: WebDriver instance
            
        Returns:
            dict: Post content including caption, username, urls, etc.
        """
        try:
            # Use JavaScript to extract as much information as possible
            script = """
            function extractEverything() {
                let result = {
                    caption: null,
                    username: null,
                    timestamp: null,
                    hashtags: [],
                    urls: [],           // New: extract all URLs
                    recipe_indicators: false // New: detect if content looks like a recipe
                };
                
                // Get all text from the page
                let allPageText = document.body.innerText;
                
                // Store all page text as a fallback caption
                result.caption = allPageText;
                
                // Look for more specific caption content
                // Try multiple approaches to find a more focused caption
                
                // 1. Look for article element (common container for post content)
                const article = document.querySelector('article');
                if (article) {
                    // Get substantial text blocks
                    const textElements = article.querySelectorAll('h1, h2, p, span, div');
                    
                    // Look for longest substantial text element that might be the caption
                    let bestCaption = '';
                    for (const el of textElements) {
                        const text = el.textContent.trim();
                        // Keep the longest substantial text block
                        if (text.length > 50 && text.length > bestCaption.length) {
                            bestCaption = text;
                        }
                    }
                    
                    if (bestCaption.length > 50) {
                        result.caption = bestCaption;
                    }
                    
                    // Look for username
                    const usernameElements = article.querySelectorAll('a');
                    for (const el of usernameElements) {
                        if (el.href && el.href.includes('/')) {
                            const possibleUsername = el.href.split('/').filter(s => s).pop();
                            if (possibleUsername && possibleUsername.length > 0 && possibleUsername.length < 30) {
                                result.username = possibleUsername;
                                break;
                            }
                        }
                    }
                }
                
                // Extract all URLs from page
                const urlRegex = /(https?:\\/\\/[^\\s]+)/g;
                const allUrls = allPageText.match(urlRegex) || [];
                result.urls = allUrls;
                
                // Extract hashtags from caption
                if (result.caption) {
                    const hashtagRegex = /#([a-zA-Z0-9_]+)/g;
                    let match;
                    while ((match = hashtagRegex.exec(result.caption)) !== null) {
                        result.hashtags.push(match[1]);
                    }
                }
                
                // Check for recipe indicators
                const recipeIndicators = [
                    'ingredient', 'ingredients', 
                    'cup', 'tbsp', 'tsp', 'tablespoon', 'teaspoon',
                    'recipe', 'instruction', 
                    'cook', 'bake', 'mix', 'stir',
                    'oz', 'gram', 'g', 'pound', 'lb'
                ];
                
                // Check if any indicators are found in the caption
                result.recipe_indicators = recipeIndicators.some(indicator => 
                    result.caption.toLowerCase().includes(indicator)
                );
                
                return result;
            }
            
            return extractEverything();
            """
            
            content = driver.execute_script(script)
            return content
        except Exception as e:
            logger.error(f"Comprehensive extraction failed: {str(e)}")
            return None

    def _extract_with_javascript(self, driver):
        """
        Extract post content using JavaScript execution
        
        Args:
            driver: WebDriver instance
            
        Returns:
            dict: Post content or None if failed
        """
        try:
            # Use JavaScript to extract content more flexibly
            script = """
            function extractPostContent() {
                let result = {
                    caption: null,
                    username: null,
                    timestamp: null,
                    hashtags: []
                };
                
                // Try multiple ways to get the caption
                
                // 1. Look for article element and find text content
                const article = document.querySelector('article');
                if (article) {
                    // Find all text nodes with significant content
                    const textElements = article.querySelectorAll('h1, h2, p, span, div');
                    
                    for (const el of textElements) {
                        const text = el.textContent.trim();
                        if (text.length > 50) {
                            // This might be the caption
                            result.caption = text;
                            break;
                        }
                    }
                    
                    // Look for username
                    const usernameElements = article.querySelectorAll('a');
                    for (const el of usernameElements) {
                        if (el.href && el.href.includes('/')) {
                            const possibleUsername = el.href.split('/').filter(s => s).pop();
                            if (possibleUsername && possibleUsername.length > 0 && possibleUsername.length < 30) {
                                result.username = possibleUsername;
                                break;
                            }
                        }
                    }
                    
                    // Extract hashtags from caption
                    if (result.caption) {
                        const hashtagRegex = /#([a-zA-Z0-9_]+)/g;
                        let match;
                        while ((match = hashtagRegex.exec(result.caption)) !== null) {
                            result.hashtags.push(match[1]);
                        }
                    }
                }
                
                // If we couldn't find caption, get all text and look for longest section
                if (!result.caption) {
                    let allText = '';
                    const textElements = document.querySelectorAll('h1, h2, p, span, div');
                    
                    // Find the longest text element
                    let longestText = '';
                    for (const el of textElements) {
                        const text = el.textContent.trim();
                        if (text.length > longestText.length) {
                            longestText = text;
                        }
                        
                        // Append to all text if substantial
                        if (text.length > 20) {
                            allText += text + '\\n';
                        }
                    }
                    
                    // Use the longest text if it's substantial
                    if (longestText.length > 50) {
                        result.caption = longestText;
                    } else if (allText.length > 50) {
                        // Otherwise use all collected text
                        result.caption = allText;
                    }
                }
                
                return result;
            }
            
            return extractPostContent();
            """
            
            content = driver.execute_script(script)
            return content
        except Exception as e:
            logger.error(f"JavaScript extraction failed: {str(e)}")
            return None

    def _extract_with_selectors(self, driver):
        """
        Extract post content using various CSS selectors
        
        Args:
            driver: WebDriver instance
            
        Returns:
            dict: Post content or None if failed
        """
        content = {
            'caption': None,
            'username': None,
            'timestamp': None,
            'hashtags': []
        }
        
        try:
            # Try multiple approaches to get caption
            caption_selectors = [
                "div[data-testid='post-caption']", 
                "span[data-testid='post-caption']",
                "div.C4VMK span",  # Classic caption selector
                "div._a9zs",       # Another caption selector
                "h1",              # Sometimes captions are in headings
                "article span",
                "article div"
            ]
            
            for selector in caption_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text
                        if text and len(text) > 50:
                            content['caption'] = text
                            break
                    if content['caption']:
                        break
                except:
                    continue
            
            # Try to get username
            username_selectors = [
                "a.ZIAjV",
                "a.notranslate",
                "a[tabindex='0']",
                "header a"
            ]
            
            for selector in username_selectors:
                try:
                    username_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if username_element:
                        # Extract username from element
                        href = username_element.get_attribute("href")
                        if href and "/" in href:
                            content['username'] = href.split("/")[-2]
                        else:
                            content['username'] = username_element.text
                        break
                except:
                    continue
            
            # Extract hashtags from caption
            if content['caption']:
                hashtag_regex = r'#(\w+)'
                hashtags = re.findall(hashtag_regex, content['caption'])
                content['hashtags'] = hashtags
            
            return content
        except Exception as e:
            logger.error(f"Selector-based extraction failed: {str(e)}")
            return None
    
    def extract_recipes_from_account(self, account_username, post_limit=10):
        """
        Extract recipes from a specific Instagram account
        
        Args:
            account_username (str): Instagram account username
            post_limit (int): Maximum number of posts to analyze
            
        Returns:
            list: List of extracted recipes
        """
        driver = None
        try:
            # Set up WebDriver if not already done
            if not self.driver:
                driver = self._setup_webdriver()
                self.login(driver)
            else:
                driver = self.driver
            
            logger.info(f"Extracting recipes from account: {account_username}")
            
            # Navigate to the account page
            account_url = f"https://www.instagram.com/{account_username}/"
            driver.get(account_url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, f"account_page_{account_username}.png")
            driver.save_screenshot(screenshot_path)
            
            # Extract post URLs
            post_urls = []
            scroll_count = 0
            max_scrolls = 5
            
            while len(post_urls) < post_limit and scroll_count < max_scrolls:
                # Extract post URLs from current view
                new_urls = driver.execute_script("""
                    const links = Array.from(document.querySelectorAll('a'));
                    return links
                        .filter(link => link.href.includes('/p/') || link.href.includes('/reel/'))
                        .map(link => link.href);
                """)
                
                # Add new unique URLs to our list
                for url in new_urls:
                    if url not in post_urls:
                        post_urls.append(url)
                
                # Log progress
                logger.info(f"Found {len(post_urls)} posts so far")
                
                # If we have enough posts, break
                if len(post_urls) >= post_limit:
                    break
                
                # Scroll down to load more posts
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                scroll_count += 1
            
            # Limit to requested number
            post_urls = post_urls[:post_limit]
            
            # Process each post
            recipes = []
            for url in post_urls:
                try:
                    content = self.extract_post_content(url)
                    if content and content.get('caption'):
                        # Add post URL to content
                        content['url'] = url
                        recipes.append(content)
                except Exception as e:
                    logger.error(f"Error extracting content from {url}: {str(e)}")
                    continue
            
            logger.info(f"Extracted {len(recipes)} potential recipes from {account_username}")
            return recipes
        
        except Exception as e:
            logger.error(f"Failed to extract recipes from account: {str(e)}")
            return []
        finally:
            # Only close the driver if we created it in this method
            if driver and driver != self.driver:
                driver.quit()

    def is_recipe_post(self, post_url):
        """
        Check if a post is likely a recipe post based on content analysis
        
        Args:
            post_url (str): URL of the Instagram post
            
        Returns:
            bool: True if post is likely a recipe, False otherwise
        """
        try:
            # Extract content from post
            content = self.extract_post_content(post_url)
            
            if not content or not content.get('caption'):
                return False
                
            # Keywords that suggest a recipe post
            recipe_keywords = [
                'recipe', 'ingredients', 'instructions', 
                'cook', 'bake', 'roast', 'fry', 'grill', 'boil',
                'tbsp', 'tsp', 'cup', 'cups', 'oz', 'pound', 'lb',
                'minute', 'hour', 'heat', 'oven', 'stove', 'simmer',
                'mix', 'stir', 'whisk', 'blend', 'combine'
            ]
            
            # Check caption for recipe keywords
            caption = content['caption'].lower()
            keyword_count = sum(1 for keyword in recipe_keywords if keyword in caption)
            
            # Check hashtags for recipe-related tags
            recipe_hashtags = ['recipe', 'cooking', 'baking', 'homemade', 'foodie', 'chef', 'cook', 'baker']
            hashtag_matches = sum(1 for tag in content['hashtags'] if any(kw in tag.lower() for kw in recipe_hashtags))
            
            # Recipe structure indicators
            has_ingredient_list = bool(re.search(r'ingredients?:', caption, re.IGNORECASE))
            has_instruction_list = bool(re.search(r'(instructions?|directions?|steps?|method):', caption, re.IGNORECASE))
            has_numbered_steps = bool(re.search(r'([1-9][0-9]?\.|[1-9][0-9]?\))', caption))
            has_measurements = bool(re.search(r'([0-9]+\s*(cup|tbsp|tsp|oz|g|kg|ml|l))', caption, re.IGNORECASE))
            
            # Score the post based on recipe indicators
            recipe_score = keyword_count + (hashtag_matches * 2)
            if has_ingredient_list: recipe_score += 5
            if has_instruction_list: recipe_score += 5
            if has_numbered_steps: recipe_score += 3
            if has_measurements: recipe_score += 4
            
            # Log the recipe score
            logger.info(f"Recipe score for post: {recipe_score}")
            
            # Return True if score exceeds threshold
            return recipe_score >= 5
            
        except Exception as e:
            logger.error(f"Error checking if post is recipe: {str(e)}")
            return False
    
    def find_recipe_posts(self, account_username=None, limit=10):
        """
        Find posts that contain recipes
        
        Args:
            account_username (str, optional): Username to search for recipes
            limit (int): Maximum number of posts to analyze
            
        Returns:
            list: List of recipe post URLs
        """
        try:
            # Get post URLs either from account or feed
            if account_username:
                # Extract posts from specific account
                all_posts = self.extract_recipes_from_account(account_username, limit=limit*2)
                post_urls = [post['url'] for post in all_posts if 'url' in post]
            else:
                # Extract posts from feed
                post_urls = self.extract_post_urls_from_feed(limit=limit*2)
            
            # Filter to find recipe posts
            recipe_posts = []
            for url in post_urls[:limit*2]:
                try:
                    if self.is_recipe_post(url):
                        recipe_posts.append(url)
                        logger.info(f"Found recipe post: {url}")
                        
                        # If we have enough recipes, break
                        if len(recipe_posts) >= limit:
                            break
                except Exception as e:
                    logger.warning(f"Error processing {url}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(recipe_posts)} recipe posts")
            return recipe_posts
        
        except Exception as e:
            logger.error(f"Error finding recipe posts: {str(e)}")
            return []
    
    def extract_post_urls_from_feed(self, limit=10):
        """
        Extract post URLs from the Instagram feed
        
        Args:
            limit (int): Maximum number of posts to extract
            
        Returns:
            list: List of post URLs
        """
        try:
            if not self.driver:
                self.driver = self._setup_webdriver()
                
            if not self.logged_in:
                self.login()
                
            logger.info("Extracting post URLs from feed...")
            
            # Navigate to the Instagram homepage
            self.driver.get("https://www.instagram.com/")
            
            # Wait for feed to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, "feed.png")
            self.driver.save_screenshot(screenshot_path)
            
            post_urls = []
            scroll_count = 0
            max_scrolls = 5
            
            while len(post_urls) < limit and scroll_count < max_scrolls:
                # Extract post URLs with JavaScript
                new_urls = self.driver.execute_script("""
                    const links = Array.from(document.querySelectorAll('a'));
                    return links
                        .filter(link => 
                            link.href.includes('/p/') || 
                            link.href.includes('/reel/')
                        )
                        .map(link => link.href);
                """)
                
                # Add new unique URLs
                for url in new_urls:
                    if url not in post_urls:
                        post_urls.append(url)
                
                logger.info(f"Found {len(post_urls)} posts so far")
                
                # If we have enough posts, break
                if len(post_urls) >= limit:
                    break
                    
                # Scroll down to load more
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                scroll_count += 1
            
            # Limit to requested number
            post_urls = post_urls[:limit]
            
            logger.info(f"Extracted {len(post_urls)} post URLs from feed")
            return post_urls
        
        except Exception as e:
            logger.error(f"Failed to extract posts from feed: {str(e)}")
            return []
    
    def extract_full_post_data(self, post_url):
        """
        Extract comprehensive data from an Instagram post
        
        Args:
            post_url (str): URL of the Instagram post
            
        Returns:
            dict: Full post data including content, type, images, etc.
        """
        try:
            # Extract basic content
            content = self.extract_post_content(post_url)
            
            if not content:
                return None
                
            # Determine post type
            post_type = self.get_post_type(post_url)
            
            # Extract image URLs
            image_urls = self.extract_image_urls(post_url)
            
            # Combine all data
            full_data = {
                **content,
                'url': post_url,
                'post_type': post_type,
                'image_urls': image_urls,
                'is_recipe': self.is_recipe_post(post_url),
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return full_data
            
        except Exception as e:
            logger.error(f"Error extracting full post data: {str(e)}")
            return None
    
    def get_post_type(self, post_url):
        """
        Determine the type of Instagram post (image, carousel, video, reel)
        
        Args:
            post_url (str): URL of the Instagram post
            
        Returns:
            str: Post type ('image', 'carousel', 'video', 'reel', or 'unknown')
        """
        try:
            # Load the post if not already using this driver
            current_url = self.driver.current_url
            if post_url not in current_url:
                self.driver.get(post_url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            
            # Give more time for content to load
            time.sleep(2)
            
            # Use JavaScript to detect post type
            post_type = self.driver.execute_script("""
                // Look for indicators of carousel posts
                const hasCarouselIndicators = document.querySelector('div[role="button"][tabindex="0"][aria-label="Next"]') !== null;
                
                // Look for video elements
                const hasVideo = document.querySelector('video') !== null;
                
                // Look for play button
                const hasPlayButton = document.querySelector('button[aria-label*="Play"]') !== null;
                
                // Check URL for reel indicator
                const isReel = window.location.href.includes('/reel/');
                
                if (isReel) {
                    return 'reel';
                } else if (hasCarouselIndicators) {
                    return 'carousel';
                } else if (hasVideo || hasPlayButton) {
                    return 'video';
                } else {
                    return 'image';
                }
            """)
            
            logger.info(f"Detected post type: {post_type}")
            return post_type
        
        except Exception as e:
            logger.error(f"Error determining post type: {str(e)}")
            return 'unknown'
    
    def extract_image_urls(self, post_url):
        """
        Extract image URLs from an Instagram post
        
        Args:
            post_url (str): URL of the Instagram post
            
        Returns:
            list: List of image URLs
        """
        try:
            # Load the post if not already using this driver
            current_url = self.driver.current_url
            if post_url not in current_url:
                self.driver.get(post_url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            
            # Take screenshot for debugging
            screenshot_path = os.path.join(self.screenshot_dir, "image_extraction.png")
            self.driver.save_screenshot(screenshot_path)
            
            # Determine post type
            post_type = self.get_post_type(post_url)
            
            # Extract images based on post type
            if post_type == 'carousel':
                # Extract all images in carousel
                image_urls = []
                
                # First get the current image
                current_image = self.driver.execute_script("""
                    const images = document.querySelectorAll('img[srcset]');
                    for (const img of images) {
                        // Skip small images like profile pictures
                        if (img.naturalWidth > 300) {
                            return img.src;
                        }
                    }
                    return null;
                """)
                
                if current_image:
                    image_urls.append(current_image)
                
                # Try to navigate through carousel to get all images
                has_next = True
                while has_next:
                    # Click next button
                    has_next = self.driver.execute_script("""
                        const nextButton = document.querySelector('div[role="button"][tabindex="0"][aria-label="Next"]');
                        if (nextButton) {
                            nextButton.click();
                            return true;
                        }
                        return false;
                    """)
                    
                    if has_next:
                        # Wait for next image to load
                        time.sleep(1)
                        
                        # Get the current image
                        current_image = self.driver.execute_script("""
                            const images = document.querySelectorAll('img[srcset]');
                            for (const img of images) {
                                // Skip small images like profile pictures
                                if (img.naturalWidth > 300) {
                                    return img.src;
                                }
                            }
                            return null;
                        """)
                        
                        if current_image and current_image not in image_urls:
                            image_urls.append(current_image)
                
                return image_urls
                
            else:
                # Single image, video thumbnail, or reel thumbnail
                image_url = self.driver.execute_script("""
                    const images = document.querySelectorAll('img[srcset]');
                    for (const img of images) {
                        // Skip small images like profile pictures
                        if (img.naturalWidth > 300) {
                            return img.src;
                        }
                    }
                    return null;
                """)
                
                return [image_url] if image_url else []
                
        except Exception as e:
            logger.error(f"Error extracting image URLs: {str(e)}")
            return []
    
    def close(self):
        """Close the WebDriver and clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None
                self.logged_in = False

# Example usage if run directly
if __name__ == "__main__":
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Instagram Monitor Agent')
    parser.add_argument('--post', type=str, help='Instagram post URL to extract')
    parser.add_argument('--account', type=str, help='Instagram account to extract recipes from')
    parser.add_argument('--monitor', type=str, help='Comma-separated list of accounts to monitor')
    parser.add_argument('--interval', type=int, default=3600, help='Monitoring interval in seconds')
    parser.add_argument('--limit', type=int, default=5, help='Number of posts to extract')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    # Create Instagram monitor agent
    instagram = InstagramMonitor({
        'headless': args.headless,
        'screenshot_dir': 'screenshots',
        'timeout': 45,
        'wait_time': 10,
        'max_retries': 3
    })
    
    try:
        if args.post:
            # Extract content from a single post
            content = instagram.extract_post_content(args.post)
            if content:
                # Save content to file
                with open('post_content.json', 'w') as f:
                    json.dump(content, f, indent=2)
                print(f"Content extracted and saved to post_content.json")
            else:
                print(f"Failed to extract content from {args.post}")
                
        elif args.account:
            # Extract recipes from an account
            recipes = instagram.extract_recipes_from_account(args.account, post_limit=args.limit)
            if recipes:
                # Save recipes to file
                with open(f'recipes_{args.account}.json', 'w') as f:
                    json.dump(recipes, f, indent=2)
                print(f"Extracted {len(recipes)} recipes and saved to recipes_{args.account}.json")
            else:
                print(f"Failed to extract recipes from {args.account}")
                
        elif args.monitor:
            # Monitor accounts for new recipe posts
            accounts = args.monitor.split(',')
            
            # Define callback function
            def on_recipe_found(post_data):
                # Save post data to file
                filepath = instagram.save_post_data_to_file(post_data, 'recipes')
                print(f"New recipe found: {post_data['url']}")
                
                # Download images
                for img_url in post_data['image_urls']:
                    instagram.download_image(img_url, 'recipe_images')
            
            # Start monitoring
            instagram.monitor_accounts(accounts, interval=args.interval, callback=on_recipe_found)
            
        else:
            # No action specified
            print("No action specified. Use --post, --account, or --monitor")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the Instagram agent
        instagram.close()
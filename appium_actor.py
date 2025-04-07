import os
import json
import time
import datetime
import logging
import smtplib
import traceback
import select
import sys
import re
from time import sleep
from appium import webdriver
from dotenv import load_dotenv
from appium.options.ios import XCUITestOptions
from selenium.common.exceptions import InvalidSessionIdException, NoSuchElementException
from email.message import EmailMessage
from src.agents.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator

# Set up logging - reduced verbosity
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("appium_log.txt"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Function to initialize the driver
def init_driver():
    logger.info("Initializing Appium driver...")
    load_dotenv()
    options = XCUITestOptions()
    options.device_name = "iPhone"
    options.platform_version = "18.3"
    options.udid = "00008101-000A4D320A28001E"
    options.bundle_id = "com.burbn.instagram"
    options.xcode_org_id = "6X85PLZ26L"
    options.xcode_signing_id = "Apple Developer"
    options.set_capability("showXcodeLog", True)
    options.set_capability("usePrebuiltWDA", True)
    try:
        driver_instance = webdriver.Remote("http://127.0.0.1:4723", options=options)
        logger.info("Driver initialized successfully.")
        return driver_instance
    except Exception as e:
        logger.error(f"Failed to initialize driver: {e}")
        logger.error(traceback.format_exc())
        raise

# Functions to load/save user memory (onboarded users)
def load_user_memory(path="user_memory.json"):
    try:
        with open(path, "r") as f:
            memory = json.load(f)
            logger.info(f"Loaded memory for {len(memory)} users")
            return memory
    except (FileNotFoundError, json.JSONDecodeError):
        logger.info("No existing user memory found, creating new memory")
        return {}

def save_user_memory(data, path="user_memory.json"):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("User memory saved successfully")

# Helper function to wait for an element using a locator
def wait_for_element(find_func, locator, timeout=10, poll_frequency=0.5):
    end_time = time.time() + timeout
    while True:
        try:
            element = find_func(locator)
            return element
        except NoSuchElementException:
            if time.time() > end_time:
                logger.error(f"Timeout waiting for element: {locator}")
                raise
            sleep(poll_frequency)

# New helper function to wait for an element using a no-argument lambda
def wait_for_element_func(func, timeout=10, poll_frequency=0.5, description="element"):
    logger.info(f"Waiting for {description}, timeout: {timeout}s")
    end_time = time.time() + timeout
    while True:
        try:
            element = func()
            logger.info(f"{description} found successfully")
            return element
        except NoSuchElementException:
            if time.time() > end_time:
                logger.error(f"Timeout waiting for {description}")
                raise
            sleep(poll_frequency)

def minimal_verify_dm_inbox(driver, timeout=10):
    """
    Minimal state verification for the DM inbox.
    Tries to locate the DM inbox indicator using a timeout.
    Returns True if found, False otherwise.
    """
    try:
        wait_for_element_func(lambda: driver.find_element("-ios predicate string", 
            "name == 'direct-inbox-view'"), timeout, description="DM inbox indicator")
        logger.info("DM inbox state verified.")
        return True
    except Exception as e:
        logger.warning(f"DM inbox indicator not found within {timeout} seconds: {e}")
        return False
    
def strict_verify_dm_inbox(driver, timeout=10):
    """
    Strict state verification for the DM inbox.
    This function first calls minimal_verify_dm_inbox and then checks for the presence of at least one DM thread element.
    Logs a warning if no threads are found, but does not raise an exception.
    """
    try:
        minimal_verify_dm_inbox(driver, timeout)
        threads = driver.find_elements("xpath", "//XCUIElementTypeCell")
        if threads and len(threads) > 0:
            logger.info("Strict DM inbox verification successful: DM threads found.")
        else:
            logger.warning("Strict DM inbox verification: No DM threads found.")
    except Exception as e:
        logger.error(f"Strict DM inbox verification failed: {e}")

# Take screenshot for debugging
def take_screenshot(driver, name):
    filename = f"screenshots/{name}_{int(time.time())}.png"
    os.makedirs("screenshots", exist_ok=True)
    driver.get_screenshot_as_file(filename)
    return filename

# Save caption to a file
def save_caption(caption_text, user_id):
    caption_filename = f"captions/caption_{user_id}_{int(time.time())}.txt"
    os.makedirs("captions", exist_ok=True)
    with open(caption_filename, "w") as f:
        f.write(caption_text)
    logger.info(f"Caption saved to {caption_filename}")
    return caption_filename

# Updated send_pdf_email function with SMTP_SSL fallback
def send_pdf_email(recipient_email, pdf_path):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_sender = os.getenv("EMAIL_SENDER")
    
    msg = EmailMessage()
    msg['Subject'] = "Your Recipe PDF"
    msg['From'] = email_sender
    msg['To'] = recipient_email
    msg.set_content("Please find attached your recipe PDF. Enjoy your meal!")
    
    with open(pdf_path, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(pdf_path)
    msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)
    
    try:
        with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as smtp:
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(msg)
        logger.info(f"PDF emailed successfully to {recipient_email}")
    except Exception as ssl_error:
        logger.error(f"SMTP_SSL failed: {ssl_error}, trying SMTP with STARTTLS")
        with smtplib.SMTP(smtp_server, int(smtp_port)) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(msg)
        logger.info(f"PDF emailed successfully to {recipient_email} using STARTTLS")

# --- Helper Function for Onboarding using DM Row Avatar ---
def extract_handle_from_thread(thread):
    """
    Extract the Instagram handle from the DM thread by parsing the avatar element's label.
    Example label might look like: "docteurzed. Profile picture"
    We'll strip out the trailing ". Profile picture" to isolate the actual handle.
    """
    try:
        # Adjust the locator to match the avatar element in your DM list rows.
        avatar = thread.find_element("-ios class chain", 
                                     "**/XCUIElementTypeOther[`name == \"avatar-front-image-view\"`]")
        # Instead of get_attribute("name") or get_attribute("value"), use "label" now.
        label_value = avatar.get_attribute("label")
        if label_value:
            # label_value often looks like "<username>. Profile picture"
            # We'll remove the trailing ". Profile picture" if it exists.
            handle = label_value.replace(". Profile picture", "").strip()
            # If your usernames sometimes include periods (e.g., "chef.dwight"), 
            # this approach will still keep them. Only the trailing substring is removed.
            return handle
        else:
            logger.warning("Avatar element found but label is empty.")
            return None
    except Exception as e:
        logger.error(f"Error extracting handle from thread: {e}")
        return None

def extract_recipe_from_content(content, recipe_agent):
    """Process content to extract recipe using multiple strategies"""
    
    # Strategy 1: Extract from URLs if present
    if 'caption' in content and content['caption']:
        # Extract URLs with better pattern matching
        import re
        # This pattern should capture complete URLs with paths like the original code
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w./%]+)*'
        urls = re.findall(url_pattern, content['caption'])
        
        # Log URLs for debugging
        if urls:
            logger.info(f"Found {len(urls)} URLs in caption: {urls}")
            
            for url in urls:
                # Skip Instagram and common social media URLs
                if any(domain in url for domain in ['instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com']):
                    continue
                
                try:
                    # Use the recipe_agent's extract_recipe_from_url method
                    logger.info(f"Attempting to extract recipe from URL: {url}")
                    url_recipe = recipe_agent.extract_recipe_from_url(url)
                    if url_recipe:
                        logger.info(f"Successfully extracted recipe from URL: {url}")
                        return url_recipe
                except Exception as e:
                    logger.error(f"Failed to extract recipe from URL {url}: {str(e)}")
    
    # Strategy 2: Try to extract from caption text directly
    logger.info("Trying to extract recipe from caption text...")
    if 'caption' in content and content['caption']:
        try:
            return recipe_agent.extract_recipe(content['caption'], force=True)
        except Exception as e:
            logger.error(f"Failed to extract recipe from caption: {str(e)}")
    
    return None

def click_thread_with_fallbacks(driver, thread):
    """Click on thread with multiple fallback strategies"""
    try:
        # Strategy 1: Direct click on the thread element
        thread.click()
        logger.info("Direct click on thread successful")
        return True
    except Exception as e:
        logger.warning(f"Direct click failed: {str(e)}")
        
        # Strategy 2: Find the name inside the thread and click that
        try:
            name_elements = thread.find_elements("-ios class chain", 
                "**/XCUIElementTypeStaticText[`name CONTAINS \"user-name-label\"`]")
            if name_elements:
                name_elements[0].click()
                logger.info("Click on name element successful")
                return True
        except Exception as e2:
            logger.warning(f"Name element click failed: {str(e2)}")
            
        # Strategy 3: Get coordinates and tap
        try:
            rect = thread.rect
            x = rect['x'] + rect['width'] // 2
            y = rect['y'] + rect['height'] // 2
            driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
            logger.info("Tap on thread coordinates successful")
            return True
        except Exception as e3:
            logger.error(f"All click strategies failed: {str(e3)}")
            return False

def is_in_conversation_thread(driver):
    """Check if we're currently in a conversation thread"""
    try:
        # Look for message input field
        input_exists = len(driver.find_elements("-ios predicate string", 
            "type == 'XCUIElementTypeTextView' AND visible == 1")) > 0
            
        # Look for back button
        back_exists = len(driver.find_elements("-ios predicate string", 
            "name == \"direct_thread_back_button\"")) > 0
            
        return input_exists and back_exists
    except Exception as e:
        logger.error(f"Error checking conversation thread state: {str(e)}")
        return False

def navigate_back_to_dm_list(driver):
    """Navigate back to DM list with fallbacks"""
    logger.info("Returning to inbox...")
    try:
        back_button = driver.find_element("-ios predicate string", 
            "name == \"direct_thread_back_button\"")
        back_button.click()
        sleep(2)
        logger.info("Successfully returned to DM inbox using back button")
        return True
    except Exception as back_error:
        logger.error(f"Error using back button: {str(back_error)}")
        
        # Try alternate selectors
        try:
            # Try finding by accessibility ID
            buttons = driver.find_elements("accessibility id", "direct_thread_back_button")
            if buttons:
                buttons[0].click()
                sleep(2)
                logger.info("Used accessibility ID to return to inbox")
                return True
            
            # Try first button in navigation bar
            back_buttons = driver.find_elements("-ios class chain", 
                "**/XCUIElementTypeNavigationBar/**/XCUIElementTypeButton[1]")
            if back_buttons:
                back_buttons[0].click()
                sleep(2)
                logger.info("Used first navigation bar button to return to inbox")
                return True
                
            logger.error("All back button strategies failed")
            return False
        except Exception as alt_back_error:
            logger.error(f"Alternative back button strategies failed: {str(alt_back_error)}")
            return False

def ensure_in_dm_list(driver):
    """Make sure we're in the DM list view, navigate there if not"""
    try:
        # Check if already in DM list
        if minimal_verify_dm_inbox(driver, timeout=3):
            return True
            
        # Try to navigate back to DM list
        try:
            # Try back button if available
            back_buttons = driver.find_elements("-ios class chain", 
                "**/XCUIElementTypeButton[`name CONTAINS \"back\" OR label CONTAINS \"Back\"`]")
            if back_buttons:
                back_buttons[0].click()
                sleep(2)
                
                # Check if we're now in the DM list
                if minimal_verify_dm_inbox(driver, timeout=3):
                    return True
        except Exception as back_error:
            logger.warning(f"Back button navigation failed: {str(back_error)}")
        
        # Direct navigation as last resort
        driver.get("instagram://direct/inbox")
        sleep(3)
        return minimal_verify_dm_inbox(driver, timeout=5)
    except Exception as e:
        logger.error(f"Failed to ensure in DM list: {str(e)}")
        return False

# Define onboarding messages once for reuse
onboarding_messages = [
    "Hey! I'm your recipe assistant. If you send me a shared recipe post, I'll extract the full recipe and send you back a clean PDF copy.",
    "Just paste or forward any Instagram recipe post. I'll do the rest — no sign-up needed.",
    "Want your recipes saved or emailed to you? Just say \"email me\" and I'll set that up."
]

def process_unread_threads(driver, user_memory):
    """Find and process unread threads with a more robust approach"""
    logger.info("Scanning for unread messages (every 5 seconds)...")
    
    # Multiple strategies to find unread threads
    unread_threads = []
    
    # Strategy 1: Try XPath with Unseen attribute (current approach)
    try:
        xpath_threads = driver.find_elements("xpath", "//XCUIElementTypeCell[.//*[@name='Unseen']]")
        if xpath_threads:
            logger.info(f"Found {len(xpath_threads)} unread thread(s) using XPath")
            unread_threads = xpath_threads
    except Exception as e:
        logger.warning(f"XPath strategy failed: {str(e)}")
    
    # Strategy 2: Look for blue dots using class chain
    if not unread_threads:
        try:
            blue_dot_threads = driver.find_elements("-ios class chain", 
                "**/XCUIElementTypeCell[./**/XCUIElementTypeOther[`name CONTAINS \"Unseen\"`]]")
            if blue_dot_threads:
                logger.info(f"Found {len(blue_dot_threads)} unread thread(s) using blue dot class chain")
                unread_threads = blue_dot_threads
        except Exception as e:
            logger.warning(f"Blue dot strategy failed: {str(e)}")
    
    # Strategy 3: Look for conversation cells with specific naming patterns
    if not unread_threads:
        try:
            name_threads = driver.find_elements("-ios class chain", 
                "**/XCUIElementTypeCell[./**/XCUIElementTypeStaticText[`name CONTAINS \"user-name-label\"`]]")
            if name_threads:
                logger.info(f"Found {len(name_threads)} thread(s) using name label")
                unread_threads = name_threads
        except Exception as e:
            logger.warning(f"Name label strategy failed: {str(e)}")
    
    logger.info(f"Found {len(unread_threads)} thread(s) in total")
    if not unread_threads:
        logger.info("No unread messages found. Will scan again in 5 seconds...")
        return
    
    # Process each thread
    for i, thread in enumerate(unread_threads):
        logger.info(f"Processing thread {i+1} of {len(unread_threads)}")
        try:
            # Get user ID before clicking the thread
            user_id = extract_handle_from_thread(thread)
            
            # Fallback to timestamp-based ID if extraction fails
            if not user_id or user_id.lower() in ["audio-call", "video-call", "call", "direct"]:
                logger.warning("Could not extract proper user handle; using fallback ID")
                user_id = f"user_{int(time.time())}"
            
            logger.info(f"Identified user: {user_id}")
            
            # Try multiple click strategies to open the thread
            if not click_thread_with_fallbacks(driver, thread):
                logger.error(f"Failed to click thread {i+1} after multiple attempts")
                continue
            
            sleep(2)  # Wait for thread to load
            
            # Check if the thread opened successfully
            if not is_in_conversation_thread(driver):
                logger.error("Failed to enter conversation thread. Returning to inbox...")
                ensure_in_dm_list(driver)
                continue
            
            # -- Begin thread content processing --
            
            # Check if user is onboarded
            is_onboarded = user_memory.get(user_id, {}).get("state") == "onboarded"
            logger.info(f"User {user_id} onboarded: {is_onboarded}")
            
            # Handle onboarding if needed
            if not is_onboarded:
                logger.info(f"Onboarding user {user_id}...")
                for msg in onboarding_messages:
                    try:
                        text_input = driver.find_element(
                            "-ios predicate string", 
                            "type == 'XCUIElementTypeTextView' AND visible == 1"
                        )
                        text_input.send_keys(msg)
                        sleep(1)
                        send_button = driver.find_element(
                            "-ios class chain",
                            "**/XCUIElementTypeButton[`name == \"send button\"`]"
                        )
                        send_button.click()
                        sleep(2)
                    except Exception as msg_error:
                        logger.error(f"Error sending onboarding message: {msg_error}")
                
                # Update user state to onboarded
                user_memory[user_id] = {
                    "state": "onboarded",
                    "last_updated": str(datetime.datetime.now())
                }
                save_user_memory(user_memory)
                logger.info(f"User {user_id} has been onboarded")
            else:
                logger.info(f"User {user_id} is already onboarded")
            
            # Scroll to bottom of conversation to see most recent messages
            logger.info("Scrolling to bottom of conversation to see most recent messages...")
            try:
                driver.execute_script('mobile: scroll', {'direction': 'down', 'toVisible': True})
                sleep(1)  # Short delay after scrolling
            except Exception as scroll_error:
                logger.error(f"Error scrolling to bottom: {scroll_error}")
            
            # Check for shared recipe post
            logger.info("Checking for shared recipe post...")
            try:
                # Find potential shared posts
                post_selectors = [
                    "**/XCUIElementTypeCell[`name == \"ig-direct-portrait-xma-message-bubble-view\"`]",
                    "**/XCUIElementTypeCell[`name CONTAINS \"message-bubble\"`]"
                ]
                post_element = None
                for selector in post_selectors:
                    elements = driver.find_elements("-ios class chain", selector)
                    if elements:
                        post_element = elements[0]
                        break
                
                if not post_element:
                    logger.info("No shared post found in this conversation")
                    # Navigate back to inbox after processing
                    navigate_back_to_dm_list(driver)
                    continue
                
                # Process shared post
                logger.info("Found a shared post, opening it...")
                try:
                    # Use a short tap instead of click
                    rect = post_element.rect
                    x = rect['x'] + rect['width'] // 2
                    y = rect['y'] + rect['height'] // 2
                    driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
                    logger.info("Tapped on post with mobile: tap command")
                except Exception as tap_error:
                    logger.error(f"Error with tap action: {tap_error}")
                    # Fallback to standard click
                    try:
                        post_element.click()
                        logger.info("Used fallback click() method")
                    except Exception as click_error:
                        logger.error(f"Fallback click also failed: {click_error}")
                        navigate_back_to_dm_list(driver)
                        continue
                
                sleep(3)  # Wait for post to open
                
                # Check if caption needs expansion
                logger.info("Checking if caption needs expansion...")
                try:
                    # Try to find caption expansion elements
                    more_button_selectors = [
                        "-ios predicate string", "name CONTAINS 'More' AND visible==true",
                        "-ios class chain", "**/XCUIElementTypeButton[`name CONTAINS \"More\"`]",
                        "-ios class chain", "**/XCUIElementTypeStaticText[`name CONTAINS \"... more\"`]",
                        "xpath", "//XCUIElementTypeStaticText[contains(@name, '... more')]"
                    ]
                    
                    more_button = None
                    for i in range(0, len(more_button_selectors), 2):
                        try:
                            finder_method = more_button_selectors[i]
                            selector = more_button_selectors[i+1]
                            elements = driver.find_elements(finder_method, selector)
                            if elements:
                                more_button = elements[0]
                                logger.info(f"Found caption expansion element using: {finder_method} -> {selector}")
                                break
                        except Exception as selector_err:
                            continue
                    
                    if more_button:
                        logger.info("Tapping on 'More' to expand caption...")
                        # Use precise tap instead of click
                        rect = more_button.rect
                        x = rect['x'] + rect['width'] // 2
                        y = rect['y'] + rect['height'] // 2
                        driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
                        logger.info("Caption expanded successfully")
                        sleep(2)  # Wait for expansion animation
                    else:
                        logger.info("No caption expansion element found - caption may already be expanded")
                        
                    # Alternative approach - try tapping on the caption text itself
                    if not more_button:
                        try:
                            caption_text_elements = driver.find_elements("class name", "XCUIElementTypeStaticText")
                            potential_captions = [elem for elem in caption_text_elements 
                                                if elem.get_attribute("value") and len(elem.get_attribute("value")) > 30]
                            
                            if potential_captions:
                                # Tap on the longest caption text
                                potential_captions.sort(key=lambda elem: len(elem.get_attribute("value") or ""), reverse=True)
                                caption_elem = potential_captions[0]
                                
                                rect = caption_elem.rect
                                x = rect['x'] + rect['width'] // 2
                                y = rect['y'] + rect['height'] // 2
                                driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
                                logger.info("Tapped on caption text to expand")
                                sleep(2)  # Wait for expansion
                        except Exception as caption_tap_err:
                            logger.warning(f"Failed to tap on caption text: {caption_tap_err}")
                            
                except Exception as expansion_err:
                    logger.warning(f"Error during caption expansion attempt: {expansion_err}")
                
                # Extract recipe caption
                logger.info("Extracting recipe caption...")
                static_text_elements = driver.find_elements("class name", "XCUIElementTypeStaticText")
                all_texts = []
                for element in static_text_elements:
                    text = element.get_attribute("value") or element.get_attribute("name") or element.get_attribute("label") or ""
                    if len(text) > 10:
                        all_texts.append((len(text), text))
                
                caption_text = None
                if all_texts:
                    all_texts.sort(reverse=True)
                    if all_texts[0][0] > 100:
                        caption_text = all_texts[0][1]
                        logger.info(f"Successfully extracted caption ({len(caption_text)} chars)")
                
                # Try scrolling if no caption found
                if not caption_text:
                    logger.info("Trying to scroll to reveal more content...")
                    try:
                        driver.execute_script('mobile: swipe', {'direction': 'up'})
                        logger.info("Swipe performed successfully")
                    except Exception as swipe_error:
                        logger.error(f"Error performing swipe: {swipe_error}")
                        try:
                            driver.execute_script('mobile: scroll', {'direction': 'up'})
                            logger.info("Alternative scroll executed")
                        except Exception as scroll_error:
                            logger.error(f"Scroll also failed: {scroll_error}")
                    
                    sleep(2)
                    static_text_elements = driver.find_elements("class name", "XCUIElementTypeStaticText")
                    longest_text = ""
                    for element in static_text_elements:
                        text = element.get_attribute("value") or element.get_attribute("name") or element.get_attribute("label") or ""
                        if len(text) > len(longest_text):
                            longest_text = text
                    if len(longest_text) > 100:
                        caption_text = longest_text
                        logger.info(f"Found caption after scroll ({len(caption_text)} chars)")
                
                # Process caption if found
                if caption_text:
                    save_caption(caption_text, user_id)
                    
                    # Exit expanded post view before recipe processing
                    logger.info("Exiting expanded post view after caption extraction...")
                    try:
                        reel_back_button = driver.find_element(
                            "-ios class chain",
                            "**/XCUIElementTypeButton[`name == \"back-button\" OR name == \"close-button\" OR label == \"Close\"`]"
                        )
                        reel_back_button.click()
                        sleep(2)
                        logger.info("Successfully exited post view before recipe processing.")
                    except Exception as reel_back_err:
                        logger.error(f"Error exiting expanded post view: {reel_back_err}")
                        logger.info("Trying fallback method to exit expanded post view...")
                        try:
                            driver.execute_script('mobile: swipe', {'direction': 'right'})
                            sleep(2)
                            logger.info("Swipe fallback performed successfully.")
                        except Exception as fallback_swipe_err:
                            logger.error(f"Fallback swipe also failed: {fallback_swipe_err}")
                    
                    # Process recipe
                    logger.info("Proceeding with recipe extraction from caption...")
                    extractor = RecipeExtractor()
                    content = {
                        'caption': caption_text,
                        'urls': re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', caption_text)
                    }
                    recipe_details = extract_recipe_from_content(content, extractor)

                    if not recipe_details:
                        logger.error("Recipe extraction failed: No details extracted.")
                        navigate_back_to_dm_list(driver)
                        continue
                    
                    logger.info("Recipe extraction successful.")
                    
                    # Generate PDF
                    logger.info("Generating PDF from extracted recipe details...")
                    pdf_gen = PDFGenerator(output_dir="./pdfs")
                    pdf_path = pdf_gen.generate_pdf(recipe_details)
                    logger.info(f"PDF generated at: {pdf_path}")
                    
                    # Email and message handling
                    try:
                        user_record = user_memory.get(user_id, {})
                        user_email = user_record.get("email")
                        
                        if not user_email:
                            logger.info("No email on record for this user. Prompting for email address...")
                            text_input = driver.find_element(
                                "-ios predicate string",
                                "type == 'XCUIElementTypeTextView' AND visible == 1"
                            )
                            prompt_message = "Please share your email address to receive your recipe PDF."
                            text_input.send_keys(prompt_message)
                            sleep(1)
                            send_button = driver.find_element(
                                "-ios class chain",
                                "**/XCUIElementTypeButton[`name == \"send button\"`]"
                            )
                            send_button.click()
                            sleep(2)
                            
                            # For testing purposes - in production you would implement logic
                            # to wait for and detect the user's email response
                            user_email = input("Enter email address received from DM reply: ").strip()
                            
                            if user_email:
                                user_record["email"] = user_email
                                user_memory[user_id] = user_record
                                save_user_memory(user_memory)
                                logger.info(f"User {user_id} email updated: {user_email}")
                            else:
                                logger.warning("No email address provided. Skipping email sending.")
                        
                        if user_email:
                            logger.info("Sending PDF to user's email...")
                            send_pdf_email(user_email, pdf_path)
                            logger.info("PDF sent via email successfully.")
                            
                            # Send confirmation message
                            try:
                                text_input = driver.find_element(
                                    "-ios predicate string",
                                    "type == 'XCUIElementTypeTextView' AND visible == 1"
                                )
                                confirmation_message = "Your recipe PDF has been emailed to you!"
                                text_input.send_keys(confirmation_message)
                                sleep(1)
                                send_button = driver.find_element(
                                    "-ios class chain",
                                    "**/XCUIElementTypeButton[`name == \"send button\"`]"
                                )
                                send_button.click()
                                sleep(2)
                            except Exception as send_err:
                                logger.error(f"Error sending confirmation message: {send_err}")
                        else:
                            try:
                                text_input = driver.find_element(
                                    "-ios predicate string",
                                    "type == 'XCUIElementTypeTextView' AND visible == 1"
                                )
                                fallback_message = "Your recipe PDF is ready! (Please provide your email for the PDF attachment)"
                                text_input.send_keys(fallback_message)
                                sleep(1)
                                send_button = driver.find_element(
                                    "-ios class chain",
                                    "**/XCUIElementTypeButton[`name == \"send button\"`]"
                                )
                                send_button.click()
                                sleep(2)
                            except Exception as fallback_err:
                                logger.error(f"Error sending fallback message: {fallback_err}")
                    except Exception as messaging_error:
                        logger.error(f"Error in messaging process: {messaging_error}")
                else:
                    logger.error("Caption text extraction failed; skipping recipe extraction.")
                    # Exit expanded post view if no caption was found
                    try:
                        reel_back_button = driver.find_element(
                            "-ios class chain",
                            "**/XCUIElementTypeButton[`name == \"Back\" OR name == \"close-button\" OR label == \"Close\"`]"
                        )
                        reel_back_button.click()
                        sleep(2)
                    except Exception as exit_err:
                        logger.error(f"Failed to exit post view: {exit_err}")
                        try:
                            driver.execute_script('mobile: swipe', {'direction': 'right'})
                            sleep(2)
                        except:
                            pass
            except Exception as post_error:
                logger.error(f"Error processing post: {post_error}")
                logger.error(traceback.format_exc())
                take_screenshot(driver, f"thread_{i+1}_post_processing_error")
            
            # -- End thread content processing --
            
            # Navigate back to inbox after processing
            navigate_back_to_dm_list(driver)
            
        except Exception as thread_error:
            logger.error(f"Failed to process thread: {str(thread_error)}")
            # Try to get back to DM list
            ensure_in_dm_list(driver)

logger.info("Starting Instagram Recipe Extractor")

try:
    driver = init_driver()
    user_memory = load_user_memory()

    logger.info("Waiting for Instagram app to load...")
    sleep(5)

    logger.info("Navigating to DMs...")
    try:
        dm_button = driver.find_element("-ios predicate string", "name == 'direct-inbox'")
        dm_button.click()
        sleep(3)
        minimal_verify_dm_inbox(driver)
    except Exception as nav_error:
        logger.warning(f"DM button not found or click failed, falling back to deep link: {nav_error}")
        try:
            driver.get("instagram://direct/inbox")
            sleep(3)
            minimal_verify_dm_inbox(driver)
        except Exception as deep_link_error:
            logger.error(f"Deep link navigation to DM inbox failed: {deep_link_error}")
            raise

    logger.info("Starting message scanning loop")
    scan_interval = 5  # seconds
    last_scan_time = time.time()

    while True:
        try:
            current_time = time.time()
            # Check if it's time for a new scan
            if current_time - last_scan_time >= scan_interval:
                last_scan_time = current_time
                process_unread_threads(driver, user_memory)
                
            # Check for user input without blocking (q to quit)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = sys.stdin.readline().strip()
                if user_input.lower() == 'q':
                    logger.info("Exiting scanning loop.")
                    break
            
            # Sleep a short amount to prevent CPU hogging
            sleep(1)
        
        except InvalidSessionIdException:
            logger.error("Session terminated. Reinitializing driver...")
            driver = init_driver()
            logger.info("Navigating to DMs after reinitialization...")
            try:
                dm_button = driver.find_element("-ios predicate string", "name == 'direct-inbox'")
                dm_button.click()
                sleep(3)
            except Exception as nav_error:
                logger.error(f"Failed to navigate to DMs after reinitialization: {nav_error}")
        except Exception as e:
            logger.error(f"Unexpected error in scanning loop: {e}")
            logger.error(traceback.format_exc())
            sleep(10)
    
    logger.info("Exiting application...")
    try:
        driver.quit()
    except Exception as e:
        logger.error(f"Failed to quit driver: {e}")
except Exception as global_error:
    logger.critical(f"Critical error: {global_error}")
    logger.critical(traceback.format_exc())
    try:
        driver.quit()
    except:
        pass

logger.info("Script execution complete")
from src.agents.pdf_cache import PDFCache, get_post_hash
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
from archive.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator
from PIL import Image
from PIL import ImageDraw

# -----------------------------------------------------------
# Global set to keep track of processed post hashes
post_hash_set = set()
# Utility: Verify shared post preview element with screenshot and bounding box
# -----------------------------------------------------------

def verify_shared_post_preview_element(driver):
    """
    Verifies if the shared recipe preview element is reliably returned using XPath.
    Logs presence, rect, and captures a screenshot with bounding box overlay.
    """
    try:
        logger.info("Verifying preview element using XPath...")
        xpath = '(//XCUIElementTypeCell[@name="ig-direct-portrait-xma-message-bubble-view"])[1]/XCUIElementTypeOther'
        element = driver.find_element("xpath", xpath)
        rect = element.rect
        logger.info(f"Found preview element with rect: {rect}")

        # Capture screenshot and draw bounding box
        os.makedirs("verification", exist_ok=True)
        screenshot_path = "verification/verification_screenshot.png"
        driver.get_screenshot_as_file(screenshot_path)
        img = Image.open(screenshot_path)
        draw = ImageDraw.Draw(img)
        box = [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']]
        draw.rectangle(box, outline="red", width=5)
        boxed_path = "verification/preview_box_overlay.png"
        img.save(boxed_path)
        logger.info(f"Saved screenshot with bounding box overlay to: {boxed_path}")
    except Exception as e:
        logger.error(f"Failed to verify preview element: {e}")
from analytics_logger_sheets import log_usage_event

# Set up logging - reduced verbosity
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("appium_log.txt"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# Utility: Classify user message for smarter onboarding
# -----------------------------------------------------------
def classify_user_message(text):
    if not text:
        return "unknown"
    text_lower = text.strip().lower()
    if any(greet in text_lower for greet in ["hi", "hello", "hey", "what's up"]):
        return "greeting"
    if "instagram.com" in text_lower or "http" in text_lower:
        return "recipe_post"
    if any(ext in text_lower for ext in ["mp4", "mov", "video"]):
        return "video"
    return "unknown"

# -----------------------------------------------------------
# Utility: Extract last user message for classification
# -----------------------------------------------------------
def get_most_recent_user_message(driver):
    try:
        elements = driver.find_elements("class name", "XCUIElementTypeStaticText")
        candidate_texts = []
        for elem in elements:
            value = elem.get_attribute("value") or elem.get_attribute("name") or ""
            if 5 < len(value) < 500:
                candidate_texts.append((elem.location['y'], value))
        if candidate_texts:
            candidate_texts.sort(reverse=True)
            return candidate_texts[0][1]
        return None
    except Exception as e:
        logger.warning(f"Failed to extract recent user message: {e}")
        return None

# -----------------------------------------------------------
# Utility: Check if image is mostly black
# -----------------------------------------------------------
def is_mostly_black(image, threshold=15, percentage=0.9):
    grayscale = image.convert("L")
    histogram = grayscale.histogram()
    black_pixel_count = sum(histogram[:threshold])
    total_pixels = image.width * image.height
    return (black_pixel_count / total_pixels) >= percentage

# -----------------------------------------------------------
# Utility: Extract image from shared post using dynamic preview element rect
# -----------------------------------------------------------
def extract_post_image(driver, user_id):
    try:
        # Take full screenshot before any messages shift layout
        os.makedirs("images", exist_ok=True)
        full_path = f"images/full_screenshot_{user_id}.png"
        driver.get_screenshot_as_file(full_path)
        img = Image.open(full_path)

        # Dynamically search for all matching preview elements by name attribute
        elements = driver.find_elements("xpath", "//XCUIElementTypeCell")
        preview_candidates = []
        for el in elements:
            name_attr = el.get_attribute("name") or ""
            if "ig-direct-portrait-xma-message-bubble-view" in name_attr:
                rect = el.rect
                if rect and "y" in rect:
                    preview_candidates.append((rect["y"], el))

        if not preview_candidates:
            logger.warning("No preview element found with expected name")
            return None

        # Select the element with the largest y value (lowest on the screen)
        preview_candidates.sort(reverse=True)
        preview_element = preview_candidates[0][1]
        rect = preview_element.rect

        # --- Determine screen scale factor using known iPhone resolution logic ---
        scale_factor = 3.0  # Hardcoded for iPhone 12 Pro Max @3x
        logger.info(f"Using fixed screen scale factor: {scale_factor:.2f}")

        # Clamp to safe bounds and scale to pixel values
        x = int(rect["x"] * scale_factor)
        y = int(max(0, rect["y"]) * scale_factor)
        width = int(rect["width"] * scale_factor)
        height = int(rect["height"] * scale_factor)

        # Debug log for screenshot and element rect
        logger.info(f"Screenshot taken at {full_path}, preview element rect: {rect}")

        # Crop and save using scaled coordinates
        cropped = img.crop((x, y, x + width, y + height))
        cropped_path = f"images/post_image_{user_id}.png"
        cropped.save(cropped_path)
        logger.info(f"Saved cropped post image for {user_id}")
        return cropped_path
    except Exception as e:
        logger.warning(f"Dynamic image scraping failed: {e}")
        return None
    
# -----------------------------------------------------------
# Driver Initialization and User Memory Management
# -----------------------------------------------------------
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

# -----------------------------------------------------------
# Helper Functions for UI Interaction and Waiting
# -----------------------------------------------------------
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
        wait_for_element_func(lambda: driver.find_element("-ios predicate string", "name == 'direct-inbox-view'"), timeout, description="DM inbox indicator")
        logger.info("DM inbox state verified.")
        return True
    except Exception as e:
        logger.warning(f"DM inbox indicator not found within {timeout} seconds: {e}")
        take_screenshot(driver, "dm_inbox_failure")
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

def take_screenshot(driver, name):
    filename = f"screenshots/{name}_{int(time.time())}.png"
    os.makedirs("screenshots", exist_ok=True)
    driver.get_screenshot_as_file(filename)
    return filename

def save_caption(caption_text, user_id):
    caption_filename = f"captions/caption_{user_id}_{int(time.time())}.txt"
    os.makedirs("captions", exist_ok=True)
    with open(caption_filename, "w") as f:
        f.write(caption_text)
    logger.info(f"Caption saved to {caption_filename}")
    return caption_filename

# -----------------------------------------------------------
# Email Sending and Extraction Helpers
# -----------------------------------------------------------
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

def extract_email_from_conversation(driver):
    """
    Scan static text elements in the conversation for a valid email address.
    Returns the first detected valid email, if any.
    """
    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    static_text_elements = driver.find_elements("class name", "XCUIElementTypeStaticText")
    for element in static_text_elements:
        text = element.get_attribute("value") or element.get_attribute("name") or element.get_attribute("label") or ""
        matches = re.findall(email_pattern, text)
        if matches:
            logger.info(f"Found email(s) in conversation: {matches}")
            return matches[0]
    return None

# -----------------------------------------------------------
# DM Handling Helpers: Extracting User Handle, Recipe Extraction, and Clicking Threads
# -----------------------------------------------------------
def extract_handle_from_thread(thread):
    """
    Extract the Instagram handle from the DM thread by parsing the avatar element's label.
    For example, if the label is "chef.julia. Profile picture", it removes the trailing text.
    """
    try:
        avatar = thread.find_element("-ios predicate string", "name == 'inbox_row_front_avatar' AND label CONTAINS 'Profile picture'")
        label_value = avatar.get_attribute("label")
        if label_value:
            handle = label_value.replace(". Profile picture", "").strip()
            return handle
        else:
            logger.warning("Avatar element found but label is empty.")
            return None
    except Exception as e:
        logger.error(f"Error extracting handle from thread: {e}")
        return None

def extract_recipe_from_content(content, recipe_agent):
    """
    Process content (usually a caption) to extract recipe details.
    First, attempt URL extraction; if that fails, fall back to processing the text directly.
    """
    if 'caption' in content and content['caption']:
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        urls = re.findall(url_pattern, content['caption'])
        if urls:
            logger.info(f"Found {len(urls)} URLs in caption: {urls}")
            for url in urls:
                if any(domain in url for domain in ['instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com']):
                    continue
                try:
                    logger.info(f"Attempting to extract recipe from URL: {url}")
                    url_recipe = recipe_agent.extract_recipe_from_url(url)
                    if url_recipe:
                        logger.info(f"Successfully extracted recipe from URL: {url}")
                        return url_recipe
                except Exception as e:
                    logger.error(f"Failed to extract recipe from URL {url}: {str(e)}")
    logger.info("Trying to extract recipe from caption text...")
    if 'caption' in content and content['caption']:
        try:
            return recipe_agent.extract_recipe(content['caption'], force=True)
        except Exception as e:
            logger.error(f"Failed to extract recipe from caption: {str(e)}")
    return None

def click_thread_with_fallbacks(driver, thread):
    """
    Click on a DM thread using multiple strategies.
    Tries a direct click, then attempts clicking a name element, and finally a coordinate-based tap.
    """
    try:
        thread.click()
        logger.info("Direct click on thread successful")
        return True
    except Exception as e:
        logger.warning(f"Direct click failed: {str(e)}")
        try:
            name_elements = thread.find_elements("-ios class chain", 
                "**/XCUIElementTypeStaticText[`name CONTAINS \"user-name-label\"`]")
            if name_elements:
                name_elements[0].click()
                logger.info("Click on name element successful")
                return True
        except Exception as e2:
            logger.warning(f"Name element click failed: {str(e2)}")
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
    """
    Determine if the app is currently in a DM conversation thread.
    It checks for the presence of a visible text input and a back button.
    """
    try:
        input_exists = len(driver.find_elements("-ios predicate string", 
            "type == 'XCUIElementTypeTextView' AND visible == 1")) > 0
        back_exists = len(driver.find_elements("-ios predicate string", 
            "name == \"direct_thread_back_button\"")) > 0
        return input_exists and back_exists
    except Exception as e:
        logger.error(f"Error checking conversation thread state: {str(e)}")
        return False

def navigate_back_to_dm_list(driver):
    """
    Navigate back to the DM list view using multiple fallback strategies.
    """
    logger.info("Returning to inbox...")
    try:
        back_button = driver.find_element("-ios predicate string", "name == \"direct_thread_back_button\"")
        back_button.click()
        sleep(2)
        logger.info("Successfully returned to DM inbox using back button")
        return True
    except Exception as back_error:
        logger.error(f"Error using back button: {str(back_error)}")
        try:
            buttons = driver.find_elements("accessibility id", "direct_thread_back_button")
            if buttons:
                buttons[0].click()
                sleep(2)
                logger.info("Used accessibility ID to return to inbox")
                return True
            back_buttons = driver.find_elements("-ios class chain", "**/XCUIElementTypeNavigationBar/**/XCUIElementTypeButton[1]")
            if back_buttons:
                back_buttons[0].click()
                sleep(2)
                logger.info("Used first navigation bar button to return to inbox")
                return True
            logger.error("All back button strategies failed")
            # Insert minimal_verify_dm_inbox fallback check
            if minimal_verify_dm_inbox(driver, timeout=3):
                logger.info("Inbox already detected despite back button failure.")
                return True
            # --- Deep-link fallback ---
            logger.info("Attempting deep-link fallback to DM inbox...")
            try:
                driver.get("instagram://direct/inbox")
                sleep(3)
                if minimal_verify_dm_inbox(driver, timeout=3):
                    logger.info("Deep-link fallback succeeded.")
                    return True
                else:
                    logger.warning("Deep-link fallback failed to verify inbox.")
            except Exception as deep_link_err:
                logger.error(f"Deep-link attempt failed: {deep_link_err}")
            return False
        except Exception as alt_back_error:
            logger.error(f"Alternative back button strategies failed: {str(alt_back_error)}")
            # Insert minimal_verify_dm_inbox fallback check
            if minimal_verify_dm_inbox(driver, timeout=3):
                logger.info("Inbox already detected despite back button failure.")
                return True
            # --- Deep-link fallback ---
            logger.info("Attempting deep-link fallback to DM inbox...")
            try:
                driver.get("instagram://direct/inbox")
                sleep(3)
                if minimal_verify_dm_inbox(driver, timeout=3):
                    logger.info("Deep-link fallback succeeded.")
                    return True
                else:
                    logger.warning("Deep-link fallback failed to verify inbox.")
            except Exception as deep_link_err:
                logger.error(f"Deep-link attempt failed: {deep_link_err}")
            return False

def ensure_in_dm_list(driver):
    """
    Ensure that the app is displaying the DM inbox.
    If not, attempts navigation via back buttons or deep linking.
    """
    try:
        if minimal_verify_dm_inbox(driver, timeout=3):
            return True
        try:
            back_buttons = driver.find_elements("-ios class chain", "**/XCUIElementTypeButton[`name CONTAINS \"back\" OR label CONTAINS \"Back\"`]")
            if back_buttons:
                back_buttons[0].click()
                sleep(2)
                if minimal_verify_dm_inbox(driver, timeout=3):
                    return True
        except Exception as back_error:
            logger.warning(f"Back button navigation failed: {str(back_error)}")
        driver.get("instagram://direct/inbox")
        sleep(3)
        return minimal_verify_dm_inbox(driver, timeout=5)
    except Exception as e:
        logger.error(f"Failed to ensure in DM list: {str(e)}")
        return False

# -----------------------------------------------------------
# Onboarding and Messaging Flow Constants
# -----------------------------------------------------------
onboarding_messages = [
    "Hey! I'm your recipe assistant. If you send me a shared recipe post, I'll extract the full recipe and send you back a clean PDF copy.",
    "Just paste or forward any Instagram recipe post. I'll do the rest — no sign-up needed.",
    "Want your recipes saved or emailed to you? Just say \"email me\" and I'll set that up."
]

# -----------------------------------------------------------
# Main Processing Function: process_unread_threads
# -----------------------------------------------------------
def process_unread_threads(driver, user_memory):
    """
    Scan for unread threads using multiple strategies, process each thread, and handle recipe extraction.
    Implements state management for onboarding and email collection.
    """
    logger.info("Scanning for unread messages (every 5 seconds)...")
    
    unread_threads = []
    
    # Strategy 1: XPath with Unseen attribute
    try:
        xpath_threads = driver.find_elements("xpath", "//XCUIElementTypeCell[.//*[@name='Unseen']]")
        if xpath_threads:
            logger.info(f"Found {len(xpath_threads)} unread thread(s) using XPath")
            unread_threads = xpath_threads
    except Exception as e:
        logger.warning(f"XPath strategy failed: {str(e)}")
    
    # Strategy 2: Blue dot (class chain)
    if not unread_threads:
        try:
            blue_dot_threads = driver.find_elements("-ios class chain", "**/XCUIElementTypeCell[./**/XCUIElementTypeOther[`name CONTAINS \"Unseen\"`]]")
            if blue_dot_threads:
                logger.info(f"Found {len(blue_dot_threads)} unread thread(s) using blue dot class chain")
                unread_threads = blue_dot_threads
        except Exception as e:
            logger.warning(f"Blue dot strategy failed: {str(e)}")
    
    # Strategy 3: Name label strategy
    if not unread_threads:
        try:
            name_threads = driver.find_elements("-ios class chain", "**/XCUIElementTypeCell[./**/XCUIElementTypeStaticText[`name CONTAINS \"user-name-label\"`]]")
            if name_threads:
                logger.info(f"Found {len(name_threads)} thread(s) using name label")
                unread_threads = name_threads
        except Exception as e:
            logger.warning(f"Name label strategy failed: {str(e)}")
    
    logger.info(f"Found {len(unread_threads)} thread(s) in total")
    if not unread_threads:
        logger.info("No unread messages found. Will scan again in 5 seconds...")
        return
    
    pdf_cache = PDFCache()
    for i, thread in enumerate(unread_threads):
        logger.info(f"Processing thread {i+1} of {len(unread_threads)}")
        try:
            user_id = extract_handle_from_thread(thread)
            if not user_id or user_id.lower() in ["audio-call", "video-call", "call", "direct"]:
                logger.warning("Could not extract proper user handle; using fallback ID")
                timestamp_id = f"user_{int(time.time())}"
                user_id = user_id or timestamp_id
            logger.info(f"Identified user: {user_id}")
            
            if not click_thread_with_fallbacks(driver, thread):
                logger.error(f"Failed to click thread {i+1} after multiple attempts")
                continue

            # --- Capture preview image as soon as we enter the DM thread ---
            preview_image_path = extract_post_image(driver, user_id)

            sleep(2)  # Wait for thread to load
            if not is_in_conversation_thread(driver):
                logger.error("Failed to enter conversation thread. Returning to inbox...")
                ensure_in_dm_list(driver)
                continue
            verify_shared_post_preview_element(driver)
            
            # --- Process thread content ---
            user_record = user_memory.get(user_id, {})
            if user_record.get("state") not in ["onboarded", "email_captured", "completed"]:
                logger.info(f"Onboarding user {user_id}...")
                for msg in onboarding_messages:
                    try:
                        text_input = driver.find_element("-ios predicate string", "type == 'XCUIElementTypeTextView' AND visible == 1")
                        text_input.send_keys(msg)
                        sleep(1)
                        send_button = driver.find_element("-ios class chain", "**/XCUIElementTypeButton[`name == \"send button\"`]")
                        send_button.click()
                        sleep(2)
                    except Exception as msg_error:
                        logger.error(f"Error sending onboarding message: {msg_error}")
                # Defensive: reload user_record to preserve existing keys before updating state
                user_record = user_memory.get(user_id, {})
                user_record["state"] = "onboarded"
                user_record["last_updated"] = str(datetime.datetime.now())
                user_memory[user_id] = user_record
                save_user_memory(user_memory)
                logger.info(f"User {user_id} has been onboarded")
                # Return to DM list after onboarding
                navigate_back_to_dm_list(driver)
                continue
            else:
                logger.info(f"User {user_id} is already onboarded")
            
            logger.info("Scrolling to bottom of conversation to see most recent messages...")
            try:
                driver.execute_script('mobile: scroll', {'direction': 'down', 'toVisible': True})
                sleep(1)
            except Exception as scroll_error:
                logger.error(f"Error scrolling to bottom: {scroll_error}")
            
            logger.info("Checking for shared recipe post...")
            try:
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
                    navigate_back_to_dm_list(driver)
                    continue
                logger.info("Found a shared post, opening it...")
                try:
                    rect = post_element.rect
                    x = rect['x'] + rect['width'] // 2
                    y = rect['y'] + rect['height'] // 2
                    driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
                    logger.info("Tapped on post with mobile: tap command")
                    # Insert prepping message after tapping on post
                    try:
                        text_input = driver.find_element("-ios predicate string", "type == 'XCUIElementTypeTextView' AND visible == 1")
                        prepping_message = "Hey, I see you've shared a recipe post. Hang tight — I'm turning it into a recipe card for you!"
                        text_input.send_keys(prepping_message)
                        sleep(1)
                        send_button = driver.find_element("-ios class chain", "**/XCUIElementTypeButton[`name == \"send button\"`]")
                        send_button.click()
                        sleep(2)
                    except Exception as prep_msg_error:
                        logger.error(f"Failed to send processing message: {prep_msg_error}")
                except Exception as tap_error:
                    logger.error(f"Error with tap action: {tap_error}")
                    try:
                        post_element.click()
                        logger.info("Used fallback click() method")
                    except Exception as click_error:
                        logger.error(f"Fallback click also failed: {click_error}")
                        navigate_back_to_dm_list(driver)
                        continue
                sleep(3)
                
                logger.info("Checking if caption needs expansion...")
                try:
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
                        rect = more_button.rect
                        x = rect['x'] + rect['width'] // 2
                        y = rect['y'] + rect['height'] // 2
                        driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
                        logger.info("Caption expanded successfully")
                        sleep(2)
                    else:
                        logger.info("No caption expansion element found - caption may already be expanded")
                        # Alternative: try tapping on the caption text
                        try:
                            caption_text_elements = driver.find_elements("class name", "XCUIElementTypeStaticText")
                            potential_captions = [elem for elem in caption_text_elements if elem.get_attribute("value") and len(elem.get_attribute("value")) > 30]
                            if potential_captions:
                                potential_captions.sort(key=lambda elem: len(elem.get_attribute("value") or ""), reverse=True)
                                caption_elem = potential_captions[0]
                                rect = caption_elem.rect
                                x = rect['x'] + rect['width'] // 2
                                y = rect['y'] + rect['height'] // 2
                                driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
                                logger.info("Tapped on caption text to expand")
                                sleep(2)
                        except Exception as caption_tap_err:
                            logger.warning(f"Failed to tap on caption text: {caption_tap_err}")
                except Exception as expansion_err:
                    logger.warning(f"Error during caption expansion attempt: {expansion_err}")
                
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
                
                if caption_text:
                    save_caption(caption_text, user_id)

                    # --- Hash-based deduplication and PDF cache logic ---
                    layout_version = "v1"
                    post_hash = get_post_hash(caption_text, user_id, layout_version)
                    
                    # Fixed exists() call - removed unnecessary layout_version parameter
                    if pdf_cache.exists(post_hash):
                        logger.info(f"Post hash {post_hash} already processed. Skipping extraction.")
                        # Load from PDF cache using correct instance method
                        cached_pdf_path = pdf_cache.load_pdf_path(post_hash)
                        if cached_pdf_path:
                            logger.info(f"Sending cached PDF: {cached_pdf_path}")
                            user_record = user_memory.get(user_id, {})
                            user_email = user_record.get("email")
                            if user_email:
                                send_pdf_email(user_email, cached_pdf_path)
                            try:
                                text_input = driver.find_element("-ios predicate string", "type == 'XCUIElementTypeTextView' AND visible == 1")
                                confirmation_message = "Your recipe PDF has been emailed to you!"
                                text_input.send_keys(confirmation_message)
                                sleep(1)
                                send_button = driver.find_element("-ios class chain", "**/XCUIElementTypeButton[`name == \"send button\"`]")
                                send_button.click()
                                sleep(2)
                            except Exception as send_err:
                                logger.error(f"Error sending confirmation message: {send_err}")
                            navigate_back_to_dm_list(driver)
                            continue
                        else:
                            logger.warning(f"No cached PDF found for {post_hash}, continuing with full extraction.")

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
                        try:
                            driver.execute_script('mobile: swipe', {'direction': 'right'})
                            sleep(2)
                            logger.info("Swipe fallback performed successfully.")
                        except Exception as fallback_swipe_err:
                            logger.error(f"Fallback swipe also failed: {fallback_swipe_err}")

                    logger.info("Proceeding with recipe extraction from caption...")
                    extractor = RecipeExtractor()
                    content = {
                        'caption': caption_text,
                        'urls': re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', caption_text)
                    }
                    
                    # Only try to load cached recipe if it exists
                    if pdf_cache.exists(post_hash):
                        logger.info(f"Loaded recipe details from cache for hash {post_hash}")
                        recipe_details = pdf_cache.load_recipe_details(post_hash)
                    else:
                        recipe_details = extract_recipe_from_content(content, extractor)
                        if not recipe_details:
                            logger.error("Recipe extraction failed: No details extracted.")
                            navigate_back_to_dm_list(driver)
                            continue
                    
                    logger.info("Recipe extraction successful.")

                    logger.info("Generating PDF from extracted recipe details...")
                    pdf_gen = PDFGenerator(output_dir="./pdfs")
                    
                    # Handle the return value from generate_pdf correctly
                    pdf_path_result = pdf_gen.generate_pdf(recipe_details, image_path=preview_image_path)
                    
                    # Check if result is a tuple (path, is_cached) or just a string path
                    if isinstance(pdf_path_result, tuple):
                        pdf_path, is_cached = pdf_path_result
                    else:
                        pdf_path = pdf_path_result
                        is_cached = False
                    
                    # Immediately after generating the PDF, check validity
                    if not isinstance(pdf_path, str) or not os.path.isfile(pdf_path):
                        logger.error(f"PDF path is invalid: {pdf_path}")
                        continue
                    
                    logger.info(f"PDF generated at: {pdf_path}")
                    
                    # Store in cache if not already cached
                    if not is_cached and not pdf_cache.exists(post_hash):
                        pdf_cache.set(post_hash, user_id, caption_text, recipe_details, pdf_path)
                        pdf_cache.save()
                    
                    log_usage_event(
                        user_id=user_id,
                        url=content['urls'][0] if content['urls'] else "unknown",
                        cuisine=recipe_details.get("cuisine", "unknown"),
                        meal_format=recipe_details.get("meal_format", "unknown")
                    )

                    # Add to processed post hash set after successful PDF generation and send
                    post_hash_set.add(post_hash)
                    try:
                        user_record = user_memory.get(user_id, {})
                        user_email = user_record.get("email")

                        if not user_email:
                            logger.info("No email on record for this user. Prompting for email address...")
                            text_input = driver.find_element("-ios predicate string", "type == 'XCUIElementTypeTextView' AND visible == 1")
                            prompt_message = "Please share your email address to receive your recipe PDF."
                            text_input.send_keys(prompt_message)
                            sleep(1)
                            send_button = driver.find_element("-ios class chain", "**/XCUIElementTypeButton[`name == \"send button\"`]")
                            try:
                                send_button.click()
                                sleep(2)
                            except Exception as confirm_err:
                                logger.error(f"Failed to send confirmation/fallback: {confirm_err}")
                            # Only navigate back after message sent and no exception
                            navigate_back_to_dm_list(driver)
                            # For demonstration, we ask for the email on the console.
                            # In production, you would wait for the user to reply in the DM.
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
                            try:
                                text_input = driver.find_element("-ios predicate string", "type == 'XCUIElementTypeTextView' AND visible == 1")
                                confirmation_message = "Your recipe PDF has been emailed to you!"
                                text_input.send_keys(confirmation_message)
                                sleep(1)
                                send_button = driver.find_element("-ios class chain", "**/XCUIElementTypeButton[`name == \"send button\"`]")
                                try:
                                    send_button.click()
                                    sleep(2)
                                except Exception as confirm_err:
                                    logger.error(f"Failed to send confirmation/fallback: {confirm_err}")
                                # Only navigate back after message sent and no exception
                                navigate_back_to_dm_list(driver)
                            except Exception as send_err:
                                logger.error(f"Error sending confirmation message: {send_err}")
                            user_record["state"] = "completed"
                            user_memory[user_id] = user_record
                            save_user_memory(user_memory)
                        else:
                            try:
                                text_input = driver.find_element("-ios predicate string", "type == 'XCUIElementTypeTextView' AND visible == 1")
                                fallback_message = "Your recipe PDF is ready! (Please provide your email for the PDF attachment)"
                                text_input.send_keys(fallback_message)
                                sleep(1)
                                send_button = driver.find_element("-ios class chain", "**/XCUIElementTypeButton[`name == \"send button\"`]")
                                try:
                                    send_button.click()
                                    sleep(2)
                                except Exception as confirm_err:
                                    logger.error(f"Failed to send confirmation/fallback: {confirm_err}")
                                # Only navigate back after message sent and no exception
                                navigate_back_to_dm_list(driver)
                            except Exception as fallback_err:
                                logger.error(f"Error sending fallback message: {fallback_err}")
                    except Exception as messaging_error:
                        logger.error(f"Error in messaging process: {messaging_error}")
                else:
                    logger.error("Caption text extraction failed; skipping recipe extraction.")
                    try:
                        reel_back_button = driver.find_element("-ios class chain", "**/XCUIElementTypeButton[`name == \"Back\" OR name == \"close-button\" OR label == \"Close\"`]")
                        reel_back_button.click()
                        sleep(2)
                    except Exception as exit_err:
                        logger.error(f"Failed to exit post view: {exit_err}")
                        try:
                            driver.execute_script('mobile: swipe', {'direction': 'right'})
                            sleep(2)
                        except Exception:
                            pass
            except Exception as post_error:
                logger.error(f"Error processing post: {post_error}")
                logger.error(traceback.format_exc())
                take_screenshot(driver, f"thread_{i+1}_post_processing_error")
            
            navigate_back_to_dm_list(driver)
            
        except Exception as thread_error:
            logger.error(f"Failed to process thread: {str(thread_error)}")
            ensure_in_dm_list(driver)
    
    logger.info("Finished processing current unread threads.")

# -----------------------------------------------------------
# Main Loop
# -----------------------------------------------------------
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
            if current_time - last_scan_time >= scan_interval:
                last_scan_time = current_time
                process_unread_threads(driver, user_memory)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = sys.stdin.readline().strip()
                if user_input.lower() == 'q':
                    logger.info("Exiting scanning loop.")
                    break
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
import os
import json
import time
import datetime
import logging
import smtplib
import traceback
import select
import sys
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

logger.info("Starting Instagram Recipe Extractor")

try:
    driver = init_driver()
    user_memory = load_user_memory()

    logger.info("Waiting for Instagram app to load...")
    sleep(5)

    logger.info("Navigating to DMs...")
    dm_button = driver.find_element("-ios predicate string", "name == 'direct-inbox'")
    dm_button.click()
    sleep(3)

    logger.info("Starting message scanning loop")
    scan_interval = 30  # seconds
    last_scan_time = time.time()

    while True:
        try:
            current_time = time.time()
            # Check if it's time for a new scan
            if current_time - last_scan_time >= scan_interval:
                logger.info(f"Scanning for unread messages (every {scan_interval} seconds)...")
                last_scan_time = current_time
                
                unread_threads = driver.find_elements("xpath", "//XCUIElementTypeCell[.//*[@name='Unseen']]")
                logger.info(f"Found {len(unread_threads)} unread thread(s)")
                
                if len(unread_threads) == 0:
                    logger.info(f"No unread messages found. Will scan again in {scan_interval} seconds...")
                else:
                    for i, thread in enumerate(unread_threads):
                        logger.info(f"Processing unread thread {i+1} of {len(unread_threads)}")
                        try:
                            thread.click()
                            sleep(2)
                            
                            # First look for the conversation title/header (which usually contains the username)
                            try:
                                # Try to find the conversation title from the navigation bar text
                                title_elements = driver.find_elements("-ios class chain", 
                                    "**/XCUIElementTypeNavigationBar/XCUIElementTypeStaticText")
                                
                                user_id = None
                                if title_elements:
                                    title_text = title_elements[0].get_attribute("value") or title_elements[0].get_attribute("name")
                                    # Ignore system-generated titles like "audio-call" or similar
                                    if title_text and not title_text.lower() in ["audio-call", "video-call", "call", "direct"]:
                                        user_id = title_text
                                        logger.info(f"User ID identified from title: {user_id}")
                                
                                # If we couldn't find a suitable title, try the avatar method
                                if not user_id or user_id.lower() in ["audio-call", "video-call", "call", "direct"]:
                                    avatar_button = driver.find_element(
                                        "-ios class chain",
                                        "**/XCUIElementTypeOther[`name == \"direct-thread-view\"`]/**/XCUIElementTypeButton[`name == \"avatar-front-image-view\"`]"
                                    )
                                    avatar_button.click()
                                    sleep(2)
                                    
                                    # Now look for username elements on profile page
                                    username_elements = driver.find_elements("-ios class chain", 
                                        "**/XCUIElementTypeNavigationBar/XCUIElementTypeStaticText")
                                    if username_elements:
                                        # The first text element in navigation bar is likely the username
                                        user_id = username_elements[0].get_attribute("value") or username_elements[0].get_attribute("name")
                                        logger.info(f"User ID identified from profile: {user_id}")
                                        
                                    # Exit the profile view
                                    profile_back_button = driver.find_element(
                                        "-ios class chain",
                                        "**/XCUIElementTypeButton[`name == \"profile-back-button\"`]"
                                    )
                                    profile_back_button.click()
                                    sleep(2)
                                    
                            except Exception as avatar_error:
                                logger.error(f"Error getting user ID: {avatar_error}")
                                
                            # Fallback - use thread ID or timestamp if we couldn't get a proper username
                            if not user_id or user_id.lower() in ["audio-call", "video-call", "call", "direct"]:
                                user_id = f"user_{int(time.time())}"
                                logger.warning(f"Could not identify proper username, using fallback ID: {user_id}")
                            
                            if not user_id:
                                logger.warning("Could not identify user ID from navigation bar.")
                                user_id = f"unknown_user_{int(time.time())}"
                            
                            try:
                                back_button = driver.find_element(
                                    "-ios class chain",
                                    "**/XCUIElementTypeButton[`name == \"profile-back-button\"`]"
                                )
                                back_button.click()
                                sleep(2)
                            except Exception as back_error:
                                logger.error(f"Error finding/clicking back button: {back_error}")
                            
                            is_onboarded = user_memory.get(user_id, {}).get("state") == "onboarded"
                            logger.info(f"User {user_id} onboarded: {is_onboarded}")
                            
                            if not is_onboarded:
                                logger.info(f"Onboarding user {user_id}...")
                                onboarding_messages = [
                                    "Hey! I'm your recipe assistant. If you send me a shared recipe post, I'll extract the full recipe and send you back a clean PDF copy.",
                                    "Just paste or forward any Instagram recipe post. I'll do the rest — no sign-up needed.",
                                    "Want your recipes saved or emailed to you? Just say \"email me\" and I'll set that up."
                                ]
                                for msg in onboarding_messages:
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
                                user_memory[user_id] = {
                                    "state": "onboarded",
                                    "last_updated": str(datetime.datetime.now())
                                }
                                save_user_memory(user_memory)
                                logger.info(f"User {user_id} has been onboarded")
                            else:
                                logger.info(f"User {user_id} is already onboarded")
                            
                            if is_onboarded:
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
                                        raise Exception("No shared post found")
                                    
                                    logger.info("Found a shared post, opening it...")
                                    post_element.click()
                                    sleep(3)
                                    
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
                                        window_size = driver.get_window_size()
                                        start_x = window_size['width'] // 2
                                        start_y = int(window_size['height'] * 0.75)
                                        end_x = start_x
                                        end_y = int(window_size['height'] * 0.25)
                                        try:
                                            # Fix: Use mobile script commands instead of TouchAction
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
                                        logger.info("Proceeding with recipe extraction from caption...")
                                        extractor = RecipeExtractor()
                                        recipe_details = extractor.extract_recipe(caption_text, force=True)
                                        if not recipe_details:
                                            logger.error("Recipe extraction failed: No details extracted.")
                                            raise Exception("Recipe extraction failed")
                                        logger.info("Recipe extraction successful.")
                                        
                                        logger.info("Generating PDF from extracted recipe details...")
                                        pdf_gen = PDFGenerator(output_dir="./pdfs")
                                        pdf_path = pdf_gen.generate_pdf(recipe_details)
                                        logger.info(f"PDF generated at: {pdf_path}")
                                        
                                        # Exit the expanded post view BEFORE sending any DM message
                                        logger.info("Exiting expanded post view before sending any messages...")
                                        try:
                                            reel_back_button = driver.find_element(
                                                "-ios class chain",
                                                "**/XCUIElementTypeButton[`name == \"Back\" OR name == \"close-button\" OR label == \"Close\"`]"
                                            )
                                            reel_back_button.click()
                                            sleep(2)
                                            logger.info("Successfully tapped reel back/close button.")
                                        except Exception as reel_back_err:
                                            logger.error(f"Error exiting expanded post view: {reel_back_err}")
                                            logger.info("Trying fallback method to exit expanded post view...")
                                            try:
                                                # Fix: Use mobile script commands for swiping
                                                driver.execute_script('mobile: swipe', {'direction': 'right'})
                                                sleep(2)
                                                logger.info("Swipe fallback performed successfully.")
                                            except Exception as fallback_swipe_err:
                                                logger.error(f"Fallback swipe also failed: {fallback_swipe_err}")
                                                logger.info("Trying direct navigation to DM inbox...")
                                                try:
                                                    driver.get("instagram://direct/thread")
                                                    sleep(3)
                                                    logger.info("Direct navigation to thread attempted.")
                                                except Exception as direct_nav_err:
                                                    logger.error(f"Direct navigation also failed: {direct_nav_err}")

                                        # Fix: Improved error handling for session termination
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
                                                # Instead of console input, you would capture DM reply automatically.
                                                # For now, simulate with input() as a placeholder.
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
                                                
                                                # Check if session is still valid before trying to send confirmation
                                                try:
                                                    driver.find_element("-ios predicate string", "type == 'XCUIElementTypeTextView'")
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
                                                except InvalidSessionIdException:
                                                    logger.error("Session terminated after sending email. Reinitializing driver...")
                                                    driver = init_driver()
                                                    logger.info("Navigating to DMs after reinitialization...")
                                                    dm_button = driver.find_element("-ios predicate string", "name == 'direct-inbox'")
                                                    dm_button.click()
                                                    sleep(3)
                                                    continue
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
                                        except InvalidSessionIdException:
                                            logger.error("Session terminated during email/messaging. Reinitializing driver...")
                                            driver = init_driver()
                                            logger.info("Navigating to DMs after reinitialization...")
                                            dm_button = driver.find_element("-ios predicate string", "name == 'direct-inbox'")
                                            dm_button.click()
                                            sleep(3)
                                            continue
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
                            
                            logger.info("Returning to inbox...")
                            try:
                                # Try only DM thread back button - this goes back one step
                                back_button = driver.find_element(
                                    "-ios class chain",
                                    "**/XCUIElementTypeButton[`name == \"back-button\"`]"
                                )
                                back_button.click()
                                sleep(2)
                                logger.info("Returned to DM list successfully")
                            except Exception as back_error:
                                logger.error(f"Error returning to inbox: {back_error}")
                                try:
                                    # Only use direct navigation as fallback
                                    driver.get("instagram://direct/inbox")
                                    sleep(3)
                                    logger.info("Direct navigation to inbox attempted.")
                                except Exception as nav_error:
                                    logger.error(f"Direct navigation to inbox failed: {nav_error}")
                            
                        except Exception as thread_error:
                            logger.error(f"Failed to process thread: {thread_error}")
                            try:
                                driver.get("instagram://direct/inbox")
                                sleep(3)
                            except:
                                logger.warning("Failed to recover from thread processing error")
                            sleep(2)
                
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
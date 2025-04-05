import os
import json
import time
import datetime
from time import sleep
from appium import webdriver
from dotenv import load_dotenv
from appium.options.ios import XCUITestOptions
from selenium.common.exceptions import InvalidSessionIdException, NoSuchElementException
import logging

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

# Helper function to wait for an element
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

# Take screenshot only when needed for debugging important issues
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

# Main script execution
logger.info("Starting Instagram Recipe Extractor")

try:
    # Initialize driver and load onboarded user memory
    driver = init_driver()
    user_memory = load_user_memory()

    # Wait for the app to load
    logger.info("Waiting for Instagram app to load...")
    sleep(5)

    # Tap the DM button
    logger.info("Navigating to DMs...")
    dm_button = driver.find_element("-ios predicate string", "name == 'direct-inbox'")
    dm_button.click()
    sleep(3)

    # Main continuous scanning loop
    logger.info("Starting message scanning loop")
    while True:
        try:
            # Scan for unread conversations
            unread_threads = driver.find_elements(
                "xpath",
                "//XCUIElementTypeCell[.//*[@name='Unseen']]"
            )
            logger.info(f"Found {len(unread_threads)} unread thread(s)")
            
            if len(unread_threads) == 0:
                logger.info("No unread messages found. Sleeping for 60 seconds...")
                sleep(60)
                continue  # Go back to the start of the loop
            
            # Process each unread thread
            for i, thread in enumerate(unread_threads):
                logger.info(f"Processing unread thread {i+1} of {len(unread_threads)}")
                try:
                    # Click the thread to open it
                    thread.click()
                    sleep(2)
                
                    # Get user ID from the avatar button
                    try:
                        avatar_button = driver.find_element(
                            "-ios class chain",
                            "**/XCUIElementTypeOther[`name == \"direct-thread-view\"`]/**/XCUIElementTypeButton[`name == \"avatar-front-image-view\"`]"
                        )
                        avatar_button.click()
                        sleep(2)
                        
                        # Find user ID from navigation bar
                        nav_buttons = driver.find_elements(
                            "-ios class chain",
                            "**/XCUIElementTypeNavigationBar/XCUIElementTypeButton"
                        )
                        
                        user_id = None
                        for btn in nav_buttons:
                            btn_name = btn.get_attribute("name")
                            if btn_name and btn_name != "profile-back-button":
                                user_id = btn_name
                                logger.info(f"User ID identified: {user_id}")
                                break
                        
                        # Go back to thread
                        back_button = driver.find_element(
                            "-ios class chain",
                            "**/XCUIElementTypeButton[`name == \"profile-back-button\"`]"
                        )
                        back_button.click()
                        sleep(2)
                    except Exception as avatar_error:
                        logger.error(f"Error getting user ID: {avatar_error}")
                        user_id = f"unknown_user_{int(time.time())}"
            
                    # Check if the user is already onboarded
                    is_onboarded = user_memory.get(user_id, {}).get("state") == "onboarded"
                    logger.info(f"User {user_id} onboarded: {is_onboarded}")
            
                    # Onboarding logic for new users
                    if not is_onboarded:
                        logger.info(f"Onboarding user {user_id}...")
                        onboarding_messages = [
                            "Hey! I'm your recipe assistant. If you send me a shared recipe post, I'll extract the full recipe and send you back a clean PDF copy.",
                            "Just paste or forward any Instagram recipe post. I'll do the rest — no sign-up needed.",
                            "Want your recipes saved or emailed to you? Just say \"email me\" and I'll set that up."
                        ]
            
                        # Send each onboarding message
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
            
                        # Mark user as onboarded
                        user_memory[user_id] = {
                            "state": "onboarded",
                            "last_updated": str(datetime.datetime.now())
                        }
                        save_user_memory(user_memory)
                        logger.info(f"User {user_id} has been onboarded")
                    else:
                        logger.info(f"User {user_id} is already onboarded")
            
                    # Recipe post processing for onboarded users
                    if is_onboarded:
                        logger.info("Checking for shared recipe post...")
                        
                        try:
                            # Find shared post
                            post_selectors = [
                                "**/XCUIElementTypeCell[`name == \"ig-direct-portrait-xma-message-bubble-view\"`]",
                                "**/XCUIElementTypeCell[`name CONTAINS \"message-bubble\"`]",
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
                            
                            # Extract caption
                            logger.info("Extracting recipe caption...")
                            
                            # Get all static text elements and find the longest
                            static_text_elements = driver.find_elements("class name", "XCUIElementTypeStaticText")
                            
                            all_texts = []
                            for element in static_text_elements:
                                text = element.get_attribute("value") or element.get_attribute("name") or element.get_attribute("label") or ""
                                if len(text) > 10:  # Only consider reasonably long texts
                                    all_texts.append((len(text), text))
                            
                            caption_text = None
                            if all_texts:
                                all_texts.sort(reverse=True)  # Sort by length (descending)
                                if all_texts[0][0] > 100:  # If we have a long text (likely a caption)
                                    caption_text = all_texts[0][1]
                                    logger.info(f"Successfully extracted caption ({len(caption_text)} chars)")
                            
                            # If no caption found, try scrolling to reveal more
                            if not caption_text:
                                logger.info("Trying to scroll to reveal more content...")
                                
                                # Scroll down
                                window_size = driver.get_window_size()
                                start_x = window_size['width'] // 2
                                start_y = window_size['height'] * 3 // 4
                                end_x = start_x
                                end_y = window_size['height'] // 4
                                
                                from appium.webdriver.common.touch_action import TouchAction
                                action = TouchAction(driver)
                                action.press(x=start_x, y=start_y).wait(500).move_to(x=end_x, y=end_y).release().perform()
                                sleep(2)
                                
                                # Try element extraction again after scroll
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
                                # Save the caption to a file
                                save_caption(caption_text, user_id)
                                
                                # Here you would process the recipe and generate PDF
                                logger.info("Processing recipe extraction...")
                                sleep(2)  # Simulate processing time

                                # Return to conversation
                                logger.info("Returning to conversation...")
                                try:
                                    # Try different back button selectors
                                    back_selectors = [
                                        "**/XCUIElementTypeButton[`name == \"back-button\"`]",
                                        "**/XCUIElementTypeButton[`name CONTAINS \"back\"`]",
                                        "**/XCUIElementTypeButton[`label == \"Back\"`]"
                                    ]
                                    
                                    for selector in back_selectors:
                                        elements = driver.find_elements("-ios class chain", selector)
                                        if elements:
                                            elements[0].click()
                                            logger.info("Returned to conversation")
                                            sleep(2)
                                            break
                                except Exception as back_error:
                                    logger.error(f"Error returning to conversation: {back_error}")
                                
                                # Send response message
                                try:
                                    text_input = driver.find_element(
                                        "-ios predicate string",
                                        "type == 'XCUIElementTypeTextView' AND visible == 1"
                                    )
                                    response_message = "Here's your recipe PDF! (Placeholder - recipe extraction successful)"
                                    text_input.send_keys(response_message)
                                    sleep(1)
                                    
                                    send_button = driver.find_element(
                                        "-ios class chain",
                                        "**/XCUIElementTypeButton[`name == \"send button\"`]"
                                    )
                                    send_button.click()
                                    logger.info("Recipe PDF response sent")
                                    sleep(2)
                                except Exception as response_error:
                                    logger.error(f"Error sending response: {response_error}")
                            else:
                                logger.error("Failed to extract caption")
                        except Exception as post_error:
                            logger.error(f"Error processing post: {post_error}")
                    
                    # Go back to the inbox to process next thread
                    logger.info("Returning to inbox...")
                    try:
                        back_button = driver.find_element(
                            "-ios class chain",
                            "**/XCUIElementTypeButton[`name == \"back-button\"`]"
                        )
                        back_button.click()
                        sleep(2)
                    except Exception as back_error:
                        logger.error(f"Error returning to inbox: {back_error}")
                        # Try direct navigation as last resort
                        try:
                            driver.get("instagram://direct/inbox")
                            sleep(3)
                        except:
                            logger.warning("Failed to navigate back to inbox")
                
                except Exception as thread_error:
                    logger.error(f"Failed to process thread: {thread_error}")
                    # Try to recover
                    try:
                        driver.get("instagram://direct/inbox")
                        sleep(3)
                    except:
                        logger.warning("Failed to recover")
            
            # After processing all unread threads, ask if the user wants to quit
            logger.info("Completed processing current threads. Scanning again...")
            exit_choice = input("Press 'q' to quit scanning, or press Enter to continue: ")
            if exit_choice.lower() == 'q':
                logger.info("Exiting scanning loop.")
                break
            
            sleep(2)
        
        except InvalidSessionIdException:
            logger.error("Session terminated. Reinitializing driver...")
            driver = init_driver()
        except Exception as e:
            logger.error(f"Unexpected error in scanning loop: {e}")
            sleep(10)

    # Cleanup
    logger.info("Exiting application...")
    try:
        driver.quit()
    except Exception as e:
        logger.error(f"Failed to quit driver: {e}")

except Exception as global_error:
    logger.critical(f"Critical error: {global_error}")
    try:
        driver.quit()
    except:
        pass

logger.info("Script execution complete")
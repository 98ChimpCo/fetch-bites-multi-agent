"""
Comment Detection Tester - A standalone script to test Instagram comment detection

This script can be used to debug and test the comment detection functionality
without running the entire flow. It can help isolate issues with comment extraction.
"""

import os
import time
import logging
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from dotenv import load_dotenv
from time import sleep
from PIL import Image, ImageDraw

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("comment_test_log.txt"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Helper functions from improved_dm_post_parser
def is_potential_recipe(text):
    """Check if text contains recipe-like content based on keywords and patterns."""
    if not text or len(text) < 80:
        return False
    
    cooking_keywords = ["bake", "mix", "preheat", "min", "tbsp", "cup", "oven", 
                       "combine", "chop", "stir", "flour", "sugar", "cook", 
                       "recipe", "ingredient", "heat", "minute", "butter"]
    
    has_keyword = any(word in text.lower() for word in cooking_keywords)
    has_number = any(char.isdigit() for char in text)
    
    # Extra check for common recipe patterns
    has_recipe_pattern = False
    if any(pattern in text.lower() for pattern in ["gram", "g ", "ml", "cup", "tablespoon", "tsp", "tbsp"]):
        has_recipe_pattern = True
    
    return (has_keyword and has_number) or has_recipe_pattern

def open_comments_section(driver):
    """Click on the comments button to open the comments section."""
    try:
        logger.info("Looking for comments button...")
        # Take screenshot before
        os.makedirs("debug_screenshots", exist_ok=True)
        driver.get_screenshot_as_file("debug_screenshots/before_comment_click.png")
        
        # Try multiple selectors for the comments button
        selectors = [
            (AppiumBy.ACCESSIBILITY_ID, 'Comments'),
            (AppiumBy.IOS_CLASS_CHAIN, '**/XCUIElementTypeButton[`name CONTAINS "comment" OR label CONTAINS "comment"`]'),
            (AppiumBy.XPATH, '//XCUIElementTypeButton[contains(@name, "comment")]')
        ]
        
        for selector_type, selector in selectors:
            try:
                comment_buttons = driver.find_elements(selector_type, selector)
                if comment_buttons:
                    logger.info(f"Found comment button using {selector_type}: {selector}")
                    
                    # Debug: Highlight the button in screenshot
                    screenshot_path = "debug_screenshots/comment_button_found.png"
                    driver.get_screenshot_as_file(screenshot_path)
                    img = Image.open(screenshot_path)
                    draw = ImageDraw.Draw(img)
                    rect = comment_buttons[0].rect
                    box = [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']]
                    draw.rectangle(box, outline="red", width=5)
                    img.save("debug_screenshots/comment_button_highlighted.png")
                    
                    # Use a very short tap duration to avoid triggering reactions
                    rect = comment_buttons[0].rect
                    x = rect['x'] + rect['width'] // 2
                    y = rect['y'] + rect['height'] // 2
                    driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 0.01})
                    logger.info("Tapped on comments button")
                    sleep(2)  # Wait for comments to load
                    
                    # Take screenshot after
                    driver.get_screenshot_as_file("debug_screenshots/after_comment_click.png")
                    return True
            except Exception as button_err:
                logger.warning(f"Failed with selector {selector_type}: {selector} - {button_err}")
                continue
                
        # Another way: look for "View all X comments" text
        try:
            view_comments_elem = driver.find_element(AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeStaticText[`name CONTAINS "View" AND name CONTAINS "comment"`]')
            if view_comments_elem:
                logger.info("Found 'View comments' text element")
                
                # Debug: Highlight the text element
                screenshot_path = "debug_screenshots/view_comments_found.png"
                driver.get_screenshot_as_file(screenshot_path)
                img = Image.open(screenshot_path)
                draw = ImageDraw.Draw(img)
                rect = view_comments_elem.rect
                box = [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']]
                draw.rectangle(box, outline="blue", width=5)
                img.save("debug_screenshots/view_comments_highlighted.png")
                
                # Tap on this element
                rect = view_comments_elem.rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 0.01})
                logger.info("Tapped on 'View comments' text")
                sleep(2)
                
                # Take screenshot after
                driver.get_screenshot_as_file("debug_screenshots/after_view_comments_click.png")
                return True
        except Exception as view_comments_err:
            logger.warning(f"Failed to find 'View comments' element: {view_comments_err}")
        
        logger.error("Could not find comments button with any selector")
        return False
    except Exception as e:
        logger.error(f"Error opening comments section: {e}")
        return False

def dump_ui_hierarchy(driver, filename="ui_hierarchy.txt"):
    """Save the entire UI hierarchy to a file for debugging."""
    try:
        hierarchy = driver.page_source
        with open(filename, "w") as f:
            f.write(hierarchy)
        logger.info(f"UI hierarchy saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to dump UI hierarchy: {e}")

def find_comment_elements(driver):
    """Find and analyze potential comment elements."""
    best_candidate = ""
    try:
        logger.info("Analyzing UI for comment elements...")
        
        # Log UI hierarchy for debugging
        dump_ui_hierarchy(driver)
        
        # Look for collection views (comments are usually in a collection view)
        collection_views = driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeCollectionView")
        logger.info(f"Found {len(collection_views)} collection views")
        
        for i, view in enumerate(collection_views):
            try:
                # Describe this collection view
                view_rect = view.rect
                logger.info(f"Collection view {i}: Size {view_rect['width']}x{view_rect['height']} at position ({view_rect['x']},{view_rect['y']})")
                
                # Look for cells in this collection view
                cells = view.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeCell")
                logger.info(f"Collection view {i} has {len(cells)} cells")
                
                # Look at the first few cells
                for j, cell in enumerate(cells[:5]):  # Limit to first 5 cells for brevity
                    cell_rect = cell.rect
                    logger.info(f"  Cell {j}: Size {cell_rect['width']}x{cell_rect['height']} at position ({cell_rect['x']},{cell_rect['y']})")
                    
                    # Look for text in this cell
                    text_elements = cell.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeStaticText")
                    logger.info(f"  Cell {j} has {len(text_elements)} text elements")
                    
                    for k, text_elem in enumerate(text_elements):
                        text = text_elem.get_attribute("value") or text_elem.get_attribute("name")
                        if text:
                            # Show a preview of the text (first 50 chars)
                            preview = text[:50] + "..." if len(text) > 50 else text
                            logger.info(f"    Text element {k}: '{preview}'")
                            
                            # If it looks like a recipe, log more details
                            if len(text) > 80 and is_potential_recipe(text):
                                if len(text) > len(best_candidate):
                                    best_candidate = text
                                logger.info(f"    POTENTIAL RECIPE FOUND in collection view {i}, cell {j}, text element {k}")
                                logger.info(f"    Text length: {len(text)} characters")
                                # Save this text to a file for inspection
                                recipe_text_path = f"debug_screenshots/potential_recipe_cv{i}_cell{j}_elem{k}.txt"
                                with open(recipe_text_path, "w") as f:
                                    f.write(text)
                                logger.info(f"    Recipe text saved to {recipe_text_path}")
            except Exception as view_err:
                logger.error(f"Error analyzing collection view {i}: {view_err}")
        
        # As a final scan, look for any static text that might be a recipe
        all_text = driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeStaticText")
        logger.info(f"Found {len(all_text)} total text elements in the UI")
        
        for i, text_elem in enumerate(all_text):
            try:
                text = text_elem.get_attribute("value") or text_elem.get_attribute("name")
                if text and len(text) > 100:  # Only consider substantial text
                    # If it looks like a recipe, log it
                    if is_potential_recipe(text):
                        if len(text) > len(best_candidate):
                            best_candidate = text
                        logger.info(f"POTENTIAL RECIPE FOUND in standalone text element {i}")
                        logger.info(f"Text length: {len(text)} characters")
                        # Save this text to a file for inspection
                        recipe_text_path = f"debug_screenshots/potential_recipe_standalone_elem{i}.txt"
                        with open(recipe_text_path, "w") as f:
                            f.write(text)
                        logger.info(f"Recipe text saved to {recipe_text_path}")
            except Exception as text_err:
                continue
    
    except Exception as e:
        logger.error(f"Error finding comment elements: {e}")
    return best_candidate if best_candidate else None

def test_comment_detection():
    """Main function to test comment detection."""
    logger.info("Starting Instagram comment detection test")
    
    # Initialize driver
    load_dotenv()
    options = XCUITestOptions()
    options.device_name = "iPhone"
    options.platform_version = "18.3"
    options.udid = "00008101-000A4D320A28001E"  # Update this with your device UDID
    options.bundle_id = "com.burbn.instagram"
    options.xcode_org_id = "6X85PLZ26L"  # Update with your Team ID
    options.xcode_signing_id = "Apple Developer"
    options.set_capability("showXcodeLog", True)
    options.set_capability("usePrebuiltWDA", True)
    
    try:
        driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
        logger.info("Driver initialized successfully")
        
        # Ask for post URL
        post_url = input("Enter Instagram post URL to test (or press Enter to navigate manually): ")
        
        if post_url:
            # Open the post URL directly
            logger.info(f"Opening post URL: {post_url}")
            driver.get(post_url)
            sleep(5)  # Wait for post to load
        else:
            logger.info("Manual navigation mode. Navigate to a post and then press Enter.")
            input("Press Enter when you've navigated to a post...")
        
        # Take a screenshot of the current state
        os.makedirs("debug_screenshots", exist_ok=True)
        driver.get_screenshot_as_file("debug_screenshots/initial_state.png")
        
        # Try to open comments section
        logger.info("Attempting to open comments section...")
        if open_comments_section(driver):
            logger.info("Comments section opened successfully")
            sleep(3)  # Wait for comments to load
            
            # Take a screenshot of the comments state
            driver.get_screenshot_as_file("debug_screenshots/comments_opened.png")
            
            # Find and analyze comment elements
            find_comment_elements(driver)
        else:
            logger.error("Failed to open comments section")
        
        logger.info("Testing complete. Check the logs and debug_screenshots folder for results.")
        input("Press Enter to exit...")
    
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    test_comment_detection()

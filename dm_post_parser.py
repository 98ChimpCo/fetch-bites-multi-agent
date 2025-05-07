import logging
from appium.webdriver.common.appiumby import AppiumBy
from time import sleep
from PIL import Image, ImageDraw
import os

logger = logging.getLogger(__name__)

def is_potential_recipe(text):
    """
    Check if text contains recipe-like content based on keywords and patterns.
    """
    if not text or len(text) < 80:
        return False
    
    cooking_keywords = ["bake", "mix", "preheat", "min", "tbsp", "cup", "oven", 
                       "combine", "chop", "stir", "flour", "sugar", "cook", 
                       "recipe", "ingredient", "heat", "minute", "butter",
                       "focaccia", "dough", "salt", "pepper", "oil", 
                       "tablespoon", "teaspoon"]
    
    has_keyword = any(word in text.lower() for word in cooking_keywords)
    has_number = any(char.isdigit() for char in text)
    
    # Extra check for common recipe patterns
    has_recipe_pattern = False
    if any(pattern in text.lower() for pattern in ["gram", "g ", "ml", "cup", "tablespoon", "tsp", "tbsp", "pinch"]):
        has_recipe_pattern = True
    
    return (has_keyword and has_number) or has_recipe_pattern

def dump_ui_hierarchy(driver, filename="ui_hierarchy.txt"):
    """Save the entire UI hierarchy to a file for debugging."""
    try:
        hierarchy = driver.page_source
        os.makedirs("debug_logs", exist_ok=True)
        with open(f"debug_logs/{filename}", "w") as f:
            f.write(hierarchy)
        logger.info(f"UI hierarchy saved to debug_logs/{filename}")
    except Exception as e:
        logger.error(f"Failed to dump UI hierarchy: {e}")

def open_comments_section(driver):
    """
    Click on the comments button to open the comments section.
    Returns True if successful, False otherwise.
    """
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
        
        # If comment button not found, try looking for numeric comment indicators
        try:
            # Look for text showing comment count (e.g., "1899 comments")
            comment_texts = driver.find_elements(AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeStaticText[`name CONTAINS "comment" AND name CONTAINS[c] "1" OR name CONTAINS[c] "2" OR name CONTAINS[c] "3" OR name CONTAINS[c] "4" OR name CONTAINS[c] "5" OR name CONTAINS[c] "6" OR name CONTAINS[c] "7" OR name CONTAINS[c] "8" OR name CONTAINS[c] "9"`]')
            
            if comment_texts:
                label = comment_texts[0].get_attribute("name") or comment_texts[0].get_attribute("value") or ""
                logger.info(f"Found comment count text: '{label}'")
                
                # Debug: Highlight the element in screenshot
                screenshot_path = "debug_screenshots/comment_count_found.png"
                driver.get_screenshot_as_file(screenshot_path)
                img = Image.open(screenshot_path)
                draw = ImageDraw.Draw(img)
                rect = comment_texts[0].rect
                box = [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']]
                draw.rectangle(box, outline="blue", width=5)
                img.save("debug_screenshots/comment_count_highlighted.png")
                
                # Tap on this element
                rect = comment_texts[0].rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 0.01})
                logger.info(f"Tapped on comment count text: '{label}'")
                sleep(2)
                
                # Take screenshot after
                driver.get_screenshot_as_file("debug_screenshots/after_comment_count_click.png")
                return True
        except Exception as text_err:
            logger.warning(f"Failed to interact with comment count text: {text_err}")
            
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
        
        # Look for specific pinned comment mention
        try:
            pinned_text = driver.find_element(AppiumBy.IOS_CLASS_CHAIN, 
                '**/XCUIElementTypeStaticText[`name CONTAINS "RECIPE pinned"`]')
            if pinned_text:
                logger.info("Found 'RECIPE pinned' text, clicking on it")
                # Debug: Highlight the pinned text
                screenshot_path = "debug_screenshots/recipe_pinned_found.png"
                driver.get_screenshot_as_file(screenshot_path)
                img = Image.open(screenshot_path)
                draw = ImageDraw.Draw(img)
                rect = pinned_text.rect
                box = [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']]
                draw.rectangle(box, outline="green", width=5)
                img.save("debug_screenshots/recipe_pinned_highlighted.png")
                
                # Click on this text
                rect = pinned_text.rect
                x = rect['x'] + rect['width'] // 2
                y = rect['y'] + rect['height'] // 2
                driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 0.01})
                logger.info("Tapped on pinned recipe text")
                sleep(2)
                
                # Take screenshot after
                driver.get_screenshot_as_file("debug_screenshots/after_pinned_recipe_click.png")
                return True
        except Exception as pinned_err:
            logger.warning(f"Failed to find pinned recipe text: {pinned_err}")
        
        logger.error("Could not find comments button or text with any selector")
        # Dump UI hierarchy for debugging
        dump_ui_hierarchy(driver, "comments_button_failure.txt")
        return False
    except Exception as e:
        logger.error(f"Error opening comments section: {e}")
        return False

def find_pinned_recipe_comment(driver):
    """
    Scan all visible comment cells in collection views to find one containing recipe text.
    """
    try:
        logger.info("Looking for pinned recipe comment...")
        # Take screenshot of current state
        os.makedirs("debug_screenshots", exist_ok=True)
        driver.get_screenshot_as_file("debug_screenshots/before_comment_scan.png")
        
        # Dump UI hierarchy for debugging
        dump_ui_hierarchy(driver, "comment_scan.txt")
        
        # Look for collection views (comments are usually in a collection view)
        collection_views = driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeCollectionView")
        logger.info(f"Found {len(collection_views)} collection views")
        
        if not collection_views:
            logger.warning("No collection views found.")
            return None

        for i, cv in enumerate(collection_views):
            logger.info(f"Inspecting Collection View {i}")
            try:
                # Save a screenshot with this collection view highlighted
                screenshot_path = f"debug_screenshots/collection_view_{i}.png"
                driver.get_screenshot_as_file(screenshot_path)
                img = Image.open(screenshot_path)
                draw = ImageDraw.Draw(img)
                rect = cv.rect
                box = [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']]
                draw.rectangle(box, outline="blue", width=5)
                img.save(f"debug_screenshots/collection_view_{i}_highlighted.png")
                
                comment_cells = cv.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeCell")
                logger.info(f"  Collection view {i} has {len(comment_cells)} cells")

                for j, cell in enumerate(comment_cells):
                    # For the first few cells, save a debug screenshot
                    if j < 3:
                        screenshot_path = f"debug_screenshots/cell_{i}_{j}.png"
                        driver.get_screenshot_as_file(screenshot_path)
                        img = Image.open(screenshot_path)
                        draw = ImageDraw.Draw(img)
                        rect = cell.rect
                        box = [rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']]
                        draw.rectangle(box, outline="red", width=5)
                        img.save(f"debug_screenshots/cell_{i}_{j}_highlighted.png")
                    
                    static_texts = cell.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeStaticText")
                    logger.info(f"  Cell {j} has {len(static_texts)} text elements")

                    for k, elem in enumerate(static_texts):
                        text = elem.get_attribute("name") or elem.get_attribute("value") or ""
                        if len(text) > 10:  # Only log substantial text
                            preview = text[:50] + "..." if len(text) > 50 else text
                            logger.info(f"    Text element {k}: '{preview}'")
                        
                        if len(text) > 150 and is_potential_recipe(text):
                            logger.info(f"    POTENTIAL RECIPE FOUND in collection view {i}, cell {j}, element {k}")
                            logger.info(f"    Text length: {len(text)} characters")
                            # Save this text to a file for inspection
                            os.makedirs("debug_logs", exist_ok=True)
                            recipe_text_path = f"debug_logs/potential_recipe_cv{i}_cell{j}_elem{k}.txt"
                            with open(recipe_text_path, "w") as f:
                                f.write(text)
                            logger.info(f"    Recipe text saved to {recipe_text_path}")
                            return text
            except Exception as inner_err:
                logger.warning(f"Failed to process collection view {i}: {inner_err}")
                continue

        # As backup, scan all freestanding static texts
        logger.info("Scanning all static text elements as fallback...")
        all_text_elements = driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeStaticText")
        logger.info(f"Found {len(all_text_elements)} total text elements")
        
        for idx, elem in enumerate(all_text_elements):
            text = elem.get_attribute("name") or elem.get_attribute("value") or ""
            
            # Only process substantial text
            if len(text) > 100:
                preview = text[:50] + "..." if len(text) > 50 else text
                logger.info(f"Text element {idx}: '{preview}'")
                
                if is_potential_recipe(text):
                    logger.info(f"POTENTIAL RECIPE FOUND in standalone text element {idx}")
                    logger.info(f"Text length: {len(text)} characters")
                    # Save this text to a file for inspection
                    os.makedirs("debug_logs", exist_ok=True)
                    recipe_text_path = f"debug_logs/potential_recipe_standalone_elem{idx}.txt"
                    with open(recipe_text_path, "w") as f:
                        f.write(text)
                    logger.info(f"Recipe text saved to {recipe_text_path}")
                    return text

        logger.warning("No recipe text found in any collection view or text element.")
        return None
    except Exception as e:
        logger.error(f"Error finding recipe comment: {e}")
        return None

def extract_caption(driver):
    """
    Extract the post caption and comments.
    Returns a tuple of (caption_text, comments_list).
    """
    try:
        # Extract caption
        static_text_elements = driver.find_elements(AppiumBy.CLASS_NAME, "XCUIElementTypeStaticText")
        potential_captions = []
        
        for element in static_text_elements:
            text = element.get_attribute("value") or element.get_attribute("name")
            if text and len(text) > 20:  # Filter out UI labels, buttons, etc.
                potential_captions.append((len(text), text))
        
        caption_text = None
        if potential_captions:
            # Sort by length, longest first
            potential_captions.sort(reverse=True)
            caption_text = potential_captions[0][1]
            logger.info(f"Extracted caption: {caption_text[:50]}...")
        else:
            logger.warning("No potential caption found")
            caption_text = ""
        
        # Extract comments
        comments = []
        
        # Try to open comments section
        open_comments_section(driver)
        sleep(2)  # Wait for comments to load
        
        # Find comments in the comments section
        comment_text = find_pinned_recipe_comment(driver)
        if comment_text:
            comments.append(comment_text)
            logger.info(f"Found comment with {len(comment_text)} characters")
        
        return caption_text, comments
    except Exception as e:
        logger.error(f"Error extracting caption and comments: {e}")
        return "", []
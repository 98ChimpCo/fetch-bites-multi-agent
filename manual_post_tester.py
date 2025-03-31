# test_workflow.py
import os
import time
import json
import logging
import argparse
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Import our agents
from src.agents.instagram_monitor import InstagramMonitor
from src.agents.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator
from src.workflows.recipe_from_post import process_post_url

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add handler if none exist to prevent duplicates
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Prevent child loggers from propagating to parent
for name in ['src.agents.instagram_monitor', 'src.agents.recipe_extractor', 'src.agents.pdf_generator']:
    child_logger = logging.getLogger(name)
    child_logger.propagate = False
    
logger = logging.getLogger('recipe_workflow')

def extract_from_caption(content, recipe_agent, force=False):
    """Extract recipe from caption text"""
    if not content.get('caption'):
        return None
        
    logger.info(f"Trying to extract recipe from caption text (force={force})")
    try:
        return recipe_agent.extract_recipe(content['caption'], force=force)
    except Exception as ex:
        logger.warning(f"Caption extraction failed: {str(ex)}")
        return None

def extract_with_force_if_indicated(content, recipe_agent):
    """Extract with force flag if recipe indicators are present"""
    if not content.get('recipe_indicators') or not content.get('caption'):
        return None
        
    logger.info("Content appears to contain recipe indicators, trying general extraction")
    try:
        return recipe_agent.extract_recipe(content['caption'], force=True)
    except Exception as ex:
        logger.warning(f"Forced extraction failed: {str(ex)}")
        return None

def sanitize_recipe_data(recipe_data):
    """
    Sanitize recipe data to ensure compatibility with PDF generation
    
    Args:
        recipe_data (dict): Recipe data to sanitize
        
    Returns:
        dict: Sanitized recipe data
    """
    if not recipe_data:
        return None
        
    # Create a deep copy to avoid modifying the original
    import copy
    sanitized = copy.deepcopy(recipe_data)
    
    # Helper function to sanitize strings
    def sanitize_str(s):
        if not s or not isinstance(s, str):
            return s
        # Replace problematic characters
        return (s.replace('\u2022', '*')  # Bullet point
                 .replace('\u2019', "'")   # Right single quotation mark
                 .replace('\u2018', "'")   # Left single quotation mark
                 .replace('\u201c', '"')   # Left double quotation mark
                 .replace('\u201d', '"')   # Right double quotation mark
                 .replace('\u2013', '-')   # En dash
                 .replace('\u2014', '--')  # Em dash
                 .replace('\u2026', '...') # Ellipsis
               )
    
    # Sanitize all string fields
    sanitized['title'] = sanitize_str(sanitized.get('title', ''))
    sanitized['description'] = sanitize_str(sanitized.get('description', ''))
    
    # Sanitize ingredients
    if 'ingredients' in sanitized and sanitized['ingredients']:
        for i, ingredient in enumerate(sanitized['ingredients']):
            if isinstance(ingredient, dict):
                for key in ingredient:
                    ingredient[key] = sanitize_str(ingredient[key])
            elif isinstance(ingredient, str):
                sanitized['ingredients'][i] = sanitize_str(ingredient)
    
    # Sanitize instructions
    if 'instructions' in sanitized and sanitized['instructions']:
        sanitized['instructions'] = [sanitize_str(step) for step in sanitized['instructions']]
    
    # Sanitize time fields
    time_fields = ['prep_time', 'cook_time', 'total_time']
    for field in time_fields:
        if field in sanitized:
            sanitized[field] = sanitize_str(sanitized[field])
    
    # Sanitize servings
    if 'servings' in sanitized:
        sanitized['servings'] = sanitize_str(sanitized['servings'])
    
    return sanitized

def extra_sanitize_recipe_data(recipe_data):
    """More aggressive sanitization for problematic recipe data"""
    if not recipe_data:
        return None
    
    # Create a deep copy
    import copy
    sanitized = copy.deepcopy(recipe_data)
    
    # Remove all non-ASCII characters as a last resort
    def strict_sanitize(s):
        if not s or not isinstance(s, str):
            return s
        return ''.join(c for c in s if ord(c) < 128)
    
    # Apply strict sanitization to all string fields
    sanitized['title'] = strict_sanitize(sanitized.get('title', ''))
    sanitized['description'] = strict_sanitize(sanitized.get('description', ''))
    
    # Sanitize ingredients
    if 'ingredients' in sanitized and sanitized['ingredients']:
        for i, ingredient in enumerate(sanitized['ingredients']):
            if isinstance(ingredient, dict):
                for key in ingredient:
                    ingredient[key] = strict_sanitize(ingredient[key])
            elif isinstance(ingredient, str):
                sanitized['ingredients'][i] = strict_sanitize(ingredient)
    
    # Sanitize instructions
    if 'instructions' in sanitized and sanitized['instructions']:
        sanitized['instructions'] = [strict_sanitize(step) for step in sanitized['instructions']]
    
    # Sanitize time fields
    time_fields = ['prep_time', 'cook_time', 'total_time']
    for field in time_fields:
        if field in sanitized:
            sanitized[field] = strict_sanitize(sanitized[field])
    
    # Sanitize servings
    if 'servings' in sanitized:
        sanitized['servings'] = strict_sanitize(sanitized['servings'])
    
    return sanitized

def process_account(username, post_limit=5):
    """Process multiple posts from an account"""
    logger.info(f"Processing account: {username}")
    
    # Create Instagram monitor agent
    instagram_agent = InstagramMonitor({
        'headless': False,
        'screenshot_dir': 'screenshots',
        'timeout': 45,
        'wait_time': 10,
        'max_retries': 3
    })
    
    try:
        # Extract posts from account
        posts = instagram_agent.extract_recipes_from_account(username, post_limit=post_limit)
        
        if not posts:
            logger.error(f"Failed to extract posts from {username}")
            return False
        
        logger.info(f"Extracted {len(posts)} posts from {username}")
        
        # Process each post
        for post in posts:
            post_url = post.get('url')
            if post_url:
                logger.info(f"Processing post: {post_url}")
                process_post_url(post_url)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing account: {str(e)}")
        return False
    finally:
        # Close the Instagram agent
        instagram_agent.close()

def process_direct_url(post_url):
    """
    Process a single Instagram post URL with improved extraction for debugging
    """
    logger.info(f"Processing post: {post_url}")
    
    driver = None
    try:
        # Set up Chrome options with anti-detection measures
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Create screenshot directory
        os.makedirs('screenshots', exist_ok=True)
        
        # Initialize WebDriver
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)  # Increased timeout
        
        # Set additional anti-detection preferences
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """
        })
        
        logger.info("WebDriver set up successfully")
        
        # Load Instagram credentials
        username = os.getenv('INSTAGRAM_USERNAME')
        password = os.getenv('INSTAGRAM_PASSWORD')
        
        if not username or not password:
            raise ValueError("Instagram credentials not found in environment variables")
        
        # Login to Instagram
        driver.get("https://www.instagram.com/")
        
        # Handle cookie consent if it appears
        try:
            time.sleep(3)
            driver.save_screenshot("screenshots/before_cookie.png")
            
            # Check if cookie dialog exists
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "cookie" in body_text or "cookies" in body_text:
                logger.info("Cookie consent dialog detected")
                
                # Try to find and click accept button
                cookie_script = """
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
                
                driver.execute_script(cookie_script)
                logger.info("Attempted to dismiss cookie dialog")
                time.sleep(2)
        except Exception as e:
            logger.warning(f"Error handling cookie dialog: {str(e)}")
        
        # Wait for login form and enter credentials
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Enter credentials
            username_input = driver.find_element(By.NAME, "username")
            password_input = driver.find_element(By.NAME, "password")
            
            username_input.clear()
            username_input.send_keys(username)
            
            password_input.clear()
            password_input.send_keys(password)
            
            # Click login button
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            logger.info("Login credentials submitted")
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            driver.save_screenshot("screenshots/login_error.png")
            return False
        
        # Wait for login to complete
        time.sleep(5)
        
        # Handle "Save Login Info" dialog if it appears
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "save login info" in body_text or "save your login info" in body_text:
                logger.info("Save Login Info dialog detected")
                
                # Try to find and click Not Now button
                not_now_script = """
                const buttons = Array.from(document.querySelectorAll('button'));
                const notNowButton = buttons.find(button => 
                    button.textContent.includes('Not Now') || 
                    button.textContent.includes('Not now') ||
                    button.textContent.includes('Later')
                );
                
                if (notNowButton) {
                    notNowButton.click();
                    return true;
                }
                return false;
                """
                
                driver.execute_script(not_now_script)
                logger.info("Attempted to dismiss Save Login Info dialog")
                time.sleep(2)
        except Exception as e:
            logger.warning(f"Error handling Save Login Info dialog: {str(e)}")
        
        # Handle "Turn on Notifications" dialog if it appears
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "turn on notifications" in body_text or "enable notifications" in body_text:
                logger.info("Notifications dialog detected")
                
                # Try to find and click Not Now button
                not_now_script = """
                const buttons = Array.from(document.querySelectorAll('button'));
                const notNowButton = buttons.find(button => 
                    button.textContent.includes('Not Now') || 
                    button.textContent.includes('Not now') ||
                    button.textContent.includes('Later')
                );
                
                if (notNowButton) {
                    notNowButton.click();
                    return true;
                }
                return false;
                """
                
                driver.execute_script(not_now_script)
                logger.info("Attempted to dismiss notifications dialog")
                time.sleep(2)
        except Exception as e:
            logger.warning(f"Error handling notifications dialog: {str(e)}")
        
        # Verify login was successful
        logger.info("Verifying login...")
        driver.save_screenshot("screenshots/after_login.png")
        
        # Now navigate to the post with increased timeout and better error handling
        logger.info(f"Navigating to post: {post_url}")
        
        # Implement retry logic for post navigation
        max_retries = 3
        content = None
        
        for attempt in range(max_retries):
            try:
                # Navigate to the post
                driver.get(post_url)
                
                # Take screenshot for debugging
                driver.save_screenshot(f"screenshots/post_load_attempt_{attempt}.png")
                
                # Wait longer for post content to load - this is the key fix
                try:
                    # Wait for article element
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )
                    
                    # Additional wait for content to fully render
                    time.sleep(5)
                    
                    # Take another screenshot after waiting
                    driver.save_screenshot(f"screenshots/post_loaded_{attempt}.png")
                except TimeoutException:
                    logger.warning(f"Timeout waiting for article element on attempt {attempt+1}")
                    continue
                
                # Extract content using JavaScript for more reliable extraction
                content = driver.execute_script("""
                    function extractContent() {
                        let result = {
                            caption: null,
                            username: null,
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
                    
                    return extractContent();
                """)
                
                # If content was successfully extracted, break the retry loop
                if content and content.get('caption'):
                    logger.info(f"Successfully extracted content on attempt {attempt+1}")
                    break
                    
                logger.warning(f"No content found on attempt {attempt+1}, retrying...")
                time.sleep(3)  # Wait before retry
                
            except Exception as e:
                logger.warning(f"Error on attempt {attempt+1}: {str(e)}")
                driver.save_screenshot(f"screenshots/extraction_error_{attempt}.png")
                time.sleep(3)  # Wait before retry
                continue
        
        # Check if content was successfully extracted
        if not content or not content.get('caption'):
            logger.error("Failed to extract content after all retries")
            return False
            
        logger.info(f"Successfully extracted content ({len(content['caption'])} chars)")
        
        # Save the extracted content for inspection
        with open('extracted_content.json', 'w') as f:
            json.dump(content, f, indent=2)
            
        # Extract recipe from content using your RecipeExtractor
        recipe_agent = RecipeExtractor()
        recipe_data = recipe_agent.extract_recipe(content['caption'])
        
        if not recipe_data:
            logger.error(f"Failed to extract recipe from content")
            return False
            
        # Generate PDF
        pdf_agent = PDFGenerator()
        pdf_path = pdf_agent.generate_pdf(recipe_data)
        
        logger.info(f"PDF generated: {pdf_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing post: {str(e)}")
        if driver:
            driver.save_screenshot("screenshots/fatal_error.png")
        return False
        
    finally:
        # Always close the driver
        if driver:
            driver.quit()
            logger.info("WebDriver closed")

def main():
    """Main function to run the extraction test"""
    parser = argparse.ArgumentParser(description='Instagram Recipe Extractor')
    parser.add_argument('--url', type=str, help='Instagram post URL to process')
    parser.add_argument('--account', type=str, help='Instagram account to process')
    parser.add_argument('--direct', action='store_true', help='Use direct extraction method (for debugging)')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of posts to process')
    
    args = parser.parse_args()
    
    if args.url:
        if args.direct:
            # Use direct extraction method for debugging
            process_direct_url(args.url)
        else:
            # Use standard agent-based method
            process_post_url(args.url)
    elif args.account:
        # Process account
        process_account(args.account, args.limit)
    else:
        # Ask for post URL or use example
        custom_url = input("Enter an Instagram post URL to process (or press Enter to use examples): ")
        
        if custom_url:
            process_post_url(custom_url)
        else:
            # Example Instagram post URLs to test
            example_posts = [
                "https://www.instagram.com/p/DF5-zP5Ovlb/",
                "https://www.instagram.com/p/DGYqcZ4vspg/",
            ]
            
            # Process each example post
            for post_url in example_posts:
                logger.info(f"\n{'=' * 50}")
                success = process_post_url(post_url)
                logger.info(f"Post processing {'successful' if success else 'failed'}")
                time.sleep(5)  # Wait between posts

if __name__ == "__main__":
    main()
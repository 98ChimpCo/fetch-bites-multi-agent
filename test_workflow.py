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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('recipe_workflow')

def process_post(post_url):
    """Process a single Instagram post URL"""
    logger.info(f"Processing post: {post_url}")
    
    # Create Instagram monitor agent
    instagram_agent = InstagramMonitor({
        'headless': False,
        'screenshot_dir': 'screenshots',
        'timeout': 45,  # Increased timeout
        'wait_time': 10,  # Longer wait time
        'max_retries': 3
    })
    
    try:
        # Extract content from post
        content = instagram_agent.extract_post_content(post_url)
        
        if not content or not content.get('caption'):
            logger.error(f"Failed to extract content from {post_url}")
            return False
        
        logger.info(f"Successfully extracted content ({len(content['caption'])} chars)")
        
        # Save the content to a file for inspection
        with open('extracted_content.json', 'w') as f:
            json.dump(content, f, indent=2)
        
        # Extract recipe from content
        recipe_agent = RecipeExtractor()
        recipe_data = recipe_agent.extract_recipe(content['caption'])
        
        if not recipe_data:
            logger.error(f"Failed to extract recipe from {post_url}")
            return False
        
        logger.info(f"Recipe extracted: {recipe_data['title']}")
        
        # Save recipe data to file
        with open('extracted_recipe.json', 'w') as f:
            json.dump(recipe_data, f, indent=2)
        
        # Generate PDF
        pdf_agent = PDFGenerator(output_dir='pdfs')
        pdf_path = pdf_agent.generate_pdf(recipe_data)
        
        if pdf_path:
            logger.info(f"PDF generated: {pdf_path}")
            return True
        else:
            logger.error("Failed to generate PDF")
            return False
            
    except Exception as e:
        logger.error(f"Error processing post: {str(e)}")
        return False
    finally:
        # Close the Instagram agent
        instagram_agent.close()

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
                process_post(post_url)
        
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
            process_post(args.url)
    elif args.account:
        # Process account
        process_account(args.account, args.limit)
    else:
        # Ask for post URL or use example
        custom_url = input("Enter an Instagram post URL to process (or press Enter to use examples): ")
        
        if custom_url:
            process_post(custom_url)
        else:
            # Example Instagram post URLs to test
            example_posts = [
                "https://www.instagram.com/p/DF5-zP5Ovlb/",
                "https://www.instagram.com/p/DGYqcZ4vspg/",
            ]
            
            # Process each example post
            for post_url in example_posts:
                logger.info(f"\n{'=' * 50}")
                success = process_post(post_url)
                logger.info(f"Post processing {'successful' if success else 'failed'}")
                time.sleep(5)  # Wait between posts

if __name__ == "__main__":
    main()
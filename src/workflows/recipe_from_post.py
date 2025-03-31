import os, time, json, logging
from src.agents.instagram_monitor import InstagramMonitor
from src.agents.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator
from src.utils.pdf_utils import generate_pdf_and_return_path
from src.utils.recipe_utils import sanitize_recipe_data, extra_sanitize_recipe_data

logger = logging.getLogger(__name__)

def process_post_url(post_url: str):
    """Handles post content extraction, recipe parsing, and PDF generation."""
    logger.info(f"Processing post: {post_url}")
    
    # Initialize agents to None for safe cleanup in finally block
    instagram_agent = None
    recipe_agent = None
    pdf_agent = None
    success = False
    
    try:
        # Create Instagram monitor agent with increased timeouts
        instagram_agent = InstagramMonitor({
            'headless': False,
            'screenshot_dir': 'screenshots',
            'timeout': 60,    # Increased timeout
            'wait_time': 15,  # Increased wait time
            'max_retries': 3
        })
        
        # Extract content from post with retry mechanism
        content = None
        extraction_attempts = 0
        max_extraction_attempts = 3
        
        while not content and extraction_attempts < max_extraction_attempts:
            try:
                extraction_attempts += 1
                logger.info(f"Content extraction attempt {extraction_attempts}/{max_extraction_attempts}")
                content = instagram_agent.extract_post_content(post_url)
                
                if not content:
                    logger.warning(f"No content extracted on attempt {extraction_attempts}")
                    if extraction_attempts < max_extraction_attempts:
                        time.sleep(2 * extraction_attempts)  # Exponential backoff
            except Exception as ex:
                logger.warning(f"Extraction attempt {extraction_attempts} failed: {str(ex)}")
                if extraction_attempts < max_extraction_attempts:
                    time.sleep(2 * extraction_attempts)  # Exponential backoff
        
        if not content:
            logger.error(f"Failed to extract content from {post_url} after {max_extraction_attempts} attempts")
            return False
        
        logger.info(f"Successfully extracted content")
        
        # Save the content to a file for inspection
        try:
            with open('extracted_content.json', 'w') as f:
                json.dump(content, f, indent=2)
        except Exception as ex:
            logger.warning(f"Could not save content to file: {str(ex)}")
        
        # Create recipe extractor
        recipe_agent = RecipeExtractor()
        recipe_data = None
        
        # Try multiple approaches to extract the recipe in a specified order
        extraction_methods = [
            # Method 1: Extract from external URLs (often most reliable)
            lambda: extract_from_urls(content, recipe_agent),
            
            # Method 2: Extract from caption with standard approach
            lambda: extract_from_caption(content, recipe_agent),
            
            # Method 3: Extract with force flag if recipe indicators present
            lambda: extract_with_force_if_indicated(content, recipe_agent, force=True)
        ]
        
        # Try each method in sequence until one succeeds
        for extraction_method in extraction_methods:
            try:
                recipe_data = extraction_method()
                if recipe_data:
                    break
            except Exception as ex:
                logger.warning(f"Recipe extraction method failed: {str(ex)}")
                continue
        
        if not recipe_data:
            logger.error(f"Failed to extract recipe using all methods")
            return False
        
        logger.info(f"Recipe extracted: {recipe_data.get('title', 'Untitled')}")
        
        # Sanitize recipe data for PDF generation
        sanitized_recipe_data = sanitize_recipe_data(recipe_data)
        
        # Save recipe data to file
        try:
            with open('extracted_recipe.json', 'w') as f:
                json.dump(recipe_data, f, indent=2)
        except Exception as ex:
            logger.warning(f"Could not save recipe data to file: {str(ex)}")
        
        # Generate PDF with retry mechanism
        pdf_agent = PDFGenerator(output_dir='pdfs')
        pdf_path = None
        
        pdf_attempts = 0
        max_pdf_attempts = 2
        
        while not pdf_path and pdf_attempts < max_pdf_attempts:
            try:
                pdf_attempts += 1
                logger.info(f"PDF generation attempt {pdf_attempts}/{max_pdf_attempts}")
                pdf_path = pdf_agent.generate_pdf(sanitized_recipe_data)
                
                if not pdf_path and pdf_attempts < max_pdf_attempts:
                    logger.warning(f"PDF generation failed on attempt {pdf_attempts}, retrying...")
                    time.sleep(1)
            except Exception as ex:
                logger.warning(f"PDF generation attempt {pdf_attempts} failed: {str(ex)}")
                if pdf_attempts < max_pdf_attempts:
                    # Try with further sanitized data on second attempt
                    sanitized_recipe_data = extra_sanitize_recipe_data(sanitized_recipe_data)
                    time.sleep(1)
        
        if pdf_path:
            logger.info(f"PDF generated: {pdf_path}")
            success = True
        else:
            logger.error("Failed to generate PDF after all attempts")
            # Continue processing even if PDF fails - we still extracted the recipe
            success = True
            
        return success
            
    except Exception as e:
        logger.error(f"Error processing post: {str(e)}")
        # Take a screenshot if possible for debugging
        try:
            if instagram_agent and instagram_agent.driver:
                screenshot_path = os.path.join('screenshots', f"error_{int(time.time())}.png")
                instagram_agent.driver.save_screenshot(screenshot_path)
                logger.info(f"Error screenshot saved to {screenshot_path}")
        except:
            pass
        return False
    finally:
        # Close the Instagram agent safely
        if instagram_agent:
            try:
                instagram_agent.close()
            except Exception as ex:
                logger.warning(f"Error closing Instagram agent: {str(ex)}")

# Helper functions for the refactored process_post function
def extract_from_urls(content, recipe_agent):
    """Extract recipe from URLs in content"""
    if not content.get('urls') or len(content.get('urls', [])) == 0:
        return None
        
    logger.info(f"Found {len(content['urls'])} URLs in content, trying to extract recipe from them")
    
    for url in content['urls']:
        # Skip Instagram and common social media URLs
        if any(domain in url for domain in ['instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com']):
            continue
            
        try:
            # Try to extract recipe from this URL
            url_recipe = recipe_agent.extract_recipe_from_url(url)
            if url_recipe:
                logger.info(f"Successfully extracted recipe from URL: {url}")
                return url_recipe
        except Exception as ex:
            logger.warning(f"Failed to extract recipe from URL {url}: {str(ex)}")
            continue
            
    return None

def extract_from_caption(content, recipe_agent):
    """Stub for extracting recipe from caption text"""
    caption = content.get("caption", "")
    return recipe_agent.extract_recipe_from_text(caption)

def extract_with_force_if_indicated(content, recipe_agent, force=False):
    """Fallback strategy to force extraction if indicators are present"""
    caption = content.get("caption", "")
    if any(keyword in caption.lower() for keyword in ["ingredients", "instructions", "prep", "cook"]):
        return recipe_agent.extract_recipe_from_text(caption, force=force)
    return None

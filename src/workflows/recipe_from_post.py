import os
import time
import logging

from classify_cuisine import classify_cuisine_and_format
from archive.instagram_monitor import InstagramMonitor
from archive.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator
from src.utils.pdf_utils import generate_pdf_and_return_path
from src.utils.recipe_utils import sanitize_recipe_data, extra_sanitize_recipe_data
from src.utils.pdf_cache import load_pdf_cache, save_pdf_cache

logger = logging.getLogger(__name__)


def extract_from_caption(content, recipe_agent):
    """Extracts recipe from caption if available."""
    caption = content.get("caption", "")
    return recipe_agent.extract_recipe_from_text(caption)


def extract_with_force_if_indicated(content, recipe_agent, force=True):
    """Forces extraction if keywords indicate recipe-like structure."""
    caption = content.get("caption", "")
    if any(keyword in caption.lower() for keyword in ["ingredients", "instructions", "prep", "cook"]):
        return recipe_agent.extract_recipe_from_text(caption, force=force)
    return None


def extract_from_urls(content, recipe_agent):
    """Stub for future implementation: extract recipe from linked URLs."""
    return None


def process_post_url(post_url: str) -> bool:
    """
    Processes a single Instagram post URL to extract recipe content and generate a PDF.
    Returns True if successful, False otherwise.
    """
    pdf_cache = load_pdf_cache()
    if post_url in pdf_cache:
        logger.info(f"Using cached PDF for: {post_url}")
        logger.info(f"PDF path: {pdf_cache[post_url]}")
        return True

    logger.info(f"Processing post: {post_url}")
    monitor = InstagramMonitor()
    recipe_agent = RecipeExtractor()
    pdf_agent = PDFGenerator()

    monitor.login()
    content = monitor.extract_post_content(post_url)
    if not content:
        logger.warning("Failed to extract content.")
        return False

    logger.info("Trying to extract recipe from caption text...")
    recipe_data = None
    extraction_methods = [
        lambda: extract_from_caption(content, recipe_agent),
        lambda: extract_with_force_if_indicated(content, recipe_agent, force=True),
        lambda: extract_from_urls(content, recipe_agent)
    ]

    for attempt in extraction_methods:
        try:
            recipe_data = attempt()
            if recipe_data:
                break
        except Exception as e:
            logger.warning(f"Recipe extraction method failed: {e}")

    if not recipe_data:
        logger.error("Recipe could not be extracted from content.")
        return False

    logger.info(f"Recipe extracted: {recipe_data.get('title', 'Untitled')}")

    sanitized = sanitize_recipe_data(recipe_data)
    classification = classify_cuisine_and_format(recipe_data.get("title", "") + "\n" + recipe_data.get("instructions", ""))
    sanitized["cuisine"] = classification["cuisine"]
    sanitized["meal_format"] = classification["meal_format"]
    pdf_path = generate_pdf_and_return_path(sanitized)

    if not pdf_path:
        logger.warning("Trying again with extra sanitization...")
        sanitized = extra_sanitize_recipe_data(recipe_data)
        pdf_path = generate_pdf_and_return_path(sanitized)

    if not pdf_path:
        logger.error("Failed to generate recipe PDF.")
        return False

    logger.info(f"Recipe PDF created at: {pdf_path}")
    pdf_cache[post_url] = pdf_path
    save_pdf_cache(pdf_cache)
    return True

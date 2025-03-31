import logging
from src.utils.claude_vision_assistant import ClaudeVisionAssistant
from src.agents.recipe_extractor import RecipeExtractor
from src.utils.pdf_utils import generate_pdf_and_return_path
from src.utils.email_simulator import mock_send_email
from src.workflows.recipe_from_post import process_post_url

logger = logging.getLogger(__name__)

def handle_incoming_dm(dm_data: dict) -> bool:
    """
    Routes parsed DM input to the correct processing path.
    """
    try:
        claude = ClaudeVisionAssistant()
        result = claude.analyze_instagram_content(
            image_path=dm_data.get("screenshot_path", None)
        )
        logger.info(f"Claude Vision result: {result}")

        if result.get("post_url"):
            success = process_post_url(result["post_url"])
            return success

        if result.get("caption_text"):
            extractor = RecipeExtractor()
            recipe = extractor.extract_recipe(result["caption_text"], force=True)
            if recipe:
                pdf_path = generate_pdf_and_return_path(recipe)
                if pdf_path:
                    logger.info(f"✅ End-to-end success: PDF generated from caption and ready at: {pdf_path}")
                    return True

        return False

    except Exception as e:
        logger.error(f"Error in DM router: {e}")
        return False
import logging
from test_workflow import process_post
from src.utils.claude_vision_assistant import ClaudeVisionAssistant
from src.agents.recipe_extractor import RecipeExtractor
from src.services.pdf_helper import generate_pdf_and_return_path
from src.utils.mock_email_delivery import mock_send_email

logger = logging.getLogger(__name__)

def handle_incoming_dm(dm_data: dict) -> bool:
    """
    Routes parsed DM input to the correct processing path.
    """
    try:
        claude = ClaudeVisionAssistant()
        result = claude.extract_structured_post_data(
            message_text=dm_data.get("message", ""),
            screenshot_path=dm_data.get("screenshot_path", None)
        )

        if result.get("post_url"):
            success = process_post(result["post_url"])
            return success

        if result.get("caption_text"):
            extractor = RecipeExtractor()
            recipe = extractor.extract_recipe(result["caption_text"], force=True)
            if recipe:
                pdf_path = generate_pdf_and_return_path(recipe)
                if pdf_path:
                    logger.info(f"PDF generated from caption: {pdf_path}")
                    return True

        return False

    except Exception as e:
        logger.error(f"Error in DM router: {e}")
        return False
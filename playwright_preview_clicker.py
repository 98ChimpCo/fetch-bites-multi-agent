import asyncio
from playwright.async_api import async_playwright
import logging
from src.utils.claude_vision_assistant import ClaudeVisionAssistant
from src.utils.user_state import UserStateManager, OnboardingManager
import os
PDF_OUTPUT_DIR = "pdfs"
from dotenv import load_dotenv
import time

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

from src.agents.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("playwright-preview-clicker")

# CONFIGURATION
INSTAGRAM_URL = "https://www.instagram.com/direct/inbox/"

async def expand_post_preview(playwright):
    load_dotenv()
    logger.info("🔥 Running AI-VISION-ONLY version of playwright_preview_clicker.py")
    browser = await playwright.chromium.launch(headless=False, slow_mo=50)
    context = await browser.new_context(storage_state="auth_storage.json")
    page = await context.new_page()

    logger.info("Navigating to Instagram DMs...")
    await page.goto(INSTAGRAM_URL, wait_until="domcontentloaded")
    await asyncio.sleep(5)

    screenshot_path = os.path.join(SCREENSHOT_DIR, f"screenshot_{int(time.time())}.png")
    await page.screenshot(path=screenshot_path)
    logger.info(f"✅ Screenshot saved to: {screenshot_path}")
    await asyncio.sleep(0.5)

    claude = ClaudeVisionAssistant(api_key=os.getenv("ANTHROPIC_API_KEY"))
    user_state_manager = UserStateManager()
    onboarding_manager = OnboardingManager(user_state_manager)

    click_targets = claude.get_all_unread_thread_targets(screenshot_path)

    if not click_targets:
        logger.warning("⚠️ No unread DM threads found.")
        await context.close()
        await browser.close()
        return

    viewport = page.viewport_size or {"width": 1280, "height": 720}

    for click_target in reversed(click_targets):
        if "x" not in click_target or "y" not in click_target:
            continue

        click_x = int(click_target["x"] * viewport["width"])
        click_y = int(click_target["y"] * viewport["height"])
        
        # Apply vertical correction to avoid mis-clicking below intended thread
        click_y = max(click_y - int(0.03 * viewport["height"]), 0)

        logger.info(f"📍 Claude recommends clicking unread thread at ({click_x}, {click_y})")
        await page.mouse.click(click_x, click_y)
        await asyncio.sleep(2)

        # After clicking, take new screenshot for analysis
        thread_screenshot = os.path.join(SCREENSHOT_DIR, f"thread_view_{int(time.time())}.png")
        await page.screenshot(path=thread_screenshot)
        analysis = claude.analyze_dm_thread(thread_screenshot)

        user_id = analysis.get("handle") or analysis.get("username") or analysis.get("display_name") or f"user_{click_y}"

        if onboarding_manager.should_onboard(user_id):
            for msg in onboarding_manager.get_onboarding_messages():
                await page.keyboard.type(msg)
                await page.keyboard.press("Enter")
                await asyncio.sleep(1.5)
            onboarding_manager.mark_onboarded(user_id)
            logger.info(f"👋 Onboarded new user: {user_id}")
            await context.close()
            await browser.close()
            return
        
        # If not onboarding, analyze thread for possible recipe content
        if not onboarding_manager.should_onboard(user_id):
            logger.info(f"📎 User already onboarded: {user_id}")
            if not analysis.get("is_shared_post") and not analysis.get("caption") and not analysis.get("post_url"):
                logger.info(f"❌ No recipe content found for user {user_id}")
                await page.keyboard.type("Hmm, I didn’t see a recipe post or link in your last message. If you send me a recipe from Instagram, I’ll convert it into a beautiful PDF!")
                await page.keyboard.press("Enter")
                await asyncio.sleep(1.5)
                await context.close()
                await browser.close()
                return

    await asyncio.sleep(5)
    await context.close()
    await browser.close()

async def process_post_url(post_url, browser=None, context=None, page=None):
    """
    Process an Instagram post URL, extracting the content using an already initialized browser.
    """
    logger.info(f"Processing post: {post_url}")
    
    if browser and context and page:
        logger.info("Using existing browser instance.")
    else:
        logger.error("❌ Browser instance not passed. Cannot extract post content.")
        return None

    logger.info("🔍 Extracting content using existing Playwright page...")

    # Placeholder logic — implement real scraping based on DOM structure
    try:
        await page.wait_for_selector("article", timeout=5000)
        caption_text = await page.evaluate("() => document.querySelector('article')?.innerText || '⚠️ No caption found in DOM'")
        content = {
            "caption": caption_text.strip(),
            "hashtags": [],
            "urls": [],
            "recipe_indicators": True,
            "page": page  # include page reference for downstream use
        }
        logger.info(f"Extracted content: {content}")
    except Exception as e:
        logger.error(f"❌ Failed to extract post content: {e}")
        content = None

    return content

def extract_from_urls(content, recipe_agent):
    if not content.get('urls'):
        return None
    for url in content['urls']:
        if any(social in url for social in ['instagram.com', 'facebook.com']):
            continue
        try:
            return recipe_agent.extract_recipe_from_url(url)
        except:
            continue
    return None

def extract_from_caption(content, recipe_agent, force=False):
    if not content.get('caption'):
        return None
    extracted = recipe_agent.extract_recipe(content['caption'], force=force)
    return sanitize_recipe_data(extracted) if extracted else None

def extract_with_force_if_indicated(content, recipe_agent):
    if not content.get('recipe_indicators') or not content.get('caption'):
        return None
    extracted = recipe_agent.extract_recipe(content['caption'], force=True)
    return sanitize_recipe_data(extracted) if extracted else None

def sanitize_recipe_data(recipe_data):
    import copy
    def sanitize_str(s):
        if not s or not isinstance(s, str): return s
        cleaned = (s.replace('\u2022', '*')
                     .replace('\u2019', "'")
                     .replace('\u2018', "'")
                     .replace('\u201c', '"')
                     .replace('\u201d', '"')
                     .replace('\u2013', '-')
                     .replace('\u2014', '--')
                     .replace('\u2026', '...'))
        return cleaned.encode('utf-8', errors='ignore').decode('utf-8')
    sanitized = copy.deepcopy(recipe_data)
    sanitized['title'] = sanitize_str(sanitized.get('title', ''))
    sanitized['description'] = sanitize_str(sanitized.get('description', ''))
    if 'ingredients' in sanitized:
        sanitized['ingredients'] = [sanitize_str(i) if isinstance(i, str) else i for i in sanitized['ingredients']]
    if 'instructions' in sanitized:
        sanitized['instructions'] = [sanitize_str(i) for i in sanitized['instructions']]
    return sanitized

def extra_sanitize_recipe_data(recipe_data):
    import copy
    def strict_sanitize(s): return ''.join(c for c in s if ord(c) < 128)
    sanitized = copy.deepcopy(recipe_data)
    sanitized['title'] = strict_sanitize(sanitized.get('title', ''))
    sanitized['description'] = strict_sanitize(sanitized.get('description', ''))
    if 'ingredients' in sanitized:
        sanitized['ingredients'] = [strict_sanitize(i) if isinstance(i, str) else i for i in sanitized['ingredients']]
    if 'instructions' in sanitized:
        sanitized['instructions'] = [strict_sanitize(i) for i in sanitized['instructions']]
    return sanitized

async def extract_recipe_and_generate_pdf(content):
    logger.info("🧪 Attempting to extract recipe from extracted post content...")
    recipe_agent = RecipeExtractor()
    recipe_data = None

    extraction_methods = [
        lambda: extract_from_urls(content, recipe_agent),
        lambda: extract_from_caption(content, recipe_agent, force=False),
        lambda: extract_with_force_if_indicated(content, recipe_agent)
    ]

    for method in extraction_methods:
        try:
            recipe_data = method()
            if recipe_data:
                break
        except Exception as ex:
            logger.warning(f"Recipe extraction method failed: {str(ex)}")

    if not recipe_data:
        logger.error("❌ Failed to extract recipe from content")
        return None

    logger.info(f"✅ Recipe extracted: {recipe_data['title']}")
    sanitized = sanitize_recipe_data(recipe_data)

    pdf_agent = PDFGenerator(output_dir=PDF_OUTPUT_DIR)
    pdf_path = None

    for attempt in range(2):
        try:
            logger.info(f"📝 Generating PDF (attempt {attempt+1}/2)...")
            pdf_path = pdf_agent.generate_pdf(sanitized)
            if pdf_path:
                logger.info(f"✅ PDF generated at: {pdf_path}")
                break
        except Exception as ex:
            logger.warning(f"PDF generation failed: {str(ex)}")
            sanitized = extra_sanitize_recipe_data(sanitized)

    if pdf_path and content and "page" in content:
        # Close expanded post overlay by clicking the close ("X") button
        close_button = await content["page"].query_selector('svg[aria-label="Close"]')
        if close_button:
            await close_button.click()
            
            # Re-analyze the DM thread screenshot for message input + send button
            chat_view_path = os.path.join(SCREENSHOT_DIR, f"chat_reply_view_{int(time.time())}.png")
            await content["page"].screenshot(path=chat_view_path)

            claude = ClaudeVisionAssistant(api_key=os.getenv("ANTHROPIC_API_KEY"))
            reply_targets = claude.analyze_instagram_content(chat_view_path)

            if reply_targets and "message_box" in reply_targets and "send_button" in reply_targets:
                viewport = content["page"].viewport_size or {"width": 1280, "height": 720}
                mb = reply_targets["message_box"]
                sb = reply_targets["send_button"]

                await content["page"].mouse.click(int(mb["x"] * viewport["width"]), int(mb["y"] * viewport["height"]))
                await content["page"].keyboard.type("Here’s your recipe PDF! 📄")

                file_input = await content["page"].query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(pdf_path)
                    logger.info(f"📎 Attached file: {pdf_path}")
                    await asyncio.sleep(2)

                await content["page"].mouse.click(int(sb["x"] * viewport["width"]), int(sb["y"] * viewport["height"]))
                await asyncio.sleep(1)
                await content["page"].keyboard.press("Enter")  # Fallback in case click didn’t send
                logger.info("✅ Attempted to send PDF reply using click + Enter fallback.")
            else:
                logger.warning("⚠️ Could not extract message_box and send_button coordinates from Claude.")
        else:
            logger.warning("⚠️ Could not find close button to dismiss post overlay.")

    return pdf_path

async def main():
    async with async_playwright() as playwright:
        await expand_post_preview(playwright)

if __name__ == "__main__":
    asyncio.run(main())
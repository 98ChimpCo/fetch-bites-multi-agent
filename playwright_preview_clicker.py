import asyncio
from playwright.async_api import async_playwright
import logging
from src.utils.claude_vision_assistant import ClaudeVisionAssistant
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
TARGET_USERNAME = "Elham Sadoughi-Yazdi"  # Username whose DM contains the preview

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

    claude = ClaudeVisionAssistant(api_key=os.getenv("ANTHROPIC_API_KEY"))
    click_target = claude.get_click_target_from_screenshot(screenshot_path, target_name=TARGET_USERNAME)

    if click_target and "x" in click_target and "y" in click_target:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        click_x = int(click_target["x"] * viewport["width"])
        click_y = int(click_target["y"] * viewport["height"])

        logger.info(f"📍 Claude recommends clicking at ({click_x}, {click_y})")
        await page.mouse.click(click_x, click_y)
        await asyncio.sleep(3)  # Allow for some delay after click for post expansion

        await asyncio.sleep(3)
        chat_screenshot_path = os.path.join(SCREENSHOT_DIR, f"chat_expanded_{int(time.time())}.png")
        await page.screenshot(path=chat_screenshot_path)
        logger.info("📸 Captured screenshot of opened DM view.")

        # 🔍 Step 2: Use Claude to find and click on the post preview in the DM thread
        preview_search_path = os.path.join(SCREENSHOT_DIR, f"post_preview_search_{int(time.time())}.png")
        await page.screenshot(path=preview_search_path)
        logger.info("📸 Captured screenshot for post preview search...")

        coords = ClaudeVisionAssistant().find_shared_post_coordinates(preview_search_path)
        if coords:
            width = page.viewport_size['width']
            height = page.viewport_size['height']
            x = int(coords["x"] * width)
            y = int(coords["y"] * height)
            logger.info(f"📍 Claude recommends clicking post preview at ({x}, {y})")
            await page.mouse.click(x, y)
            await asyncio.sleep(3)  # Allow for some delay after click for post expansion
            logger.info("✅ Clicked on shared post preview (expansion triggered)")
            post_url = page.url
            logger.info(f"📎 Post URL: {post_url}")

            content = await process_post_url(post_url, browser=browser, context=context, page=page)
            await extract_recipe_and_generate_pdf(content)
            
            await asyncio.sleep(4)
        else:
            logger.warning("⚠️ Claude could not find a post preview to click. Skipping...")
            return

        analysis = claude.analyze_instagram_content(chat_screenshot_path)
        if analysis:
            logger.info(f"Claude analysis: {analysis}")

            # Always click post preview if available
            if "click_target" in analysis and "x" in analysis["click_target"] and "y" in analysis["click_target"]:
                viewport = page.viewport_size or {"width": 1280, "height": 720}
                click_x = int(analysis["click_target"]["x"] * viewport["width"])
                click_y = int(analysis["click_target"]["y"] * viewport["height"])
                logger.info(f"🖱️ Clicking shared post preview at ({click_x}, {click_y})...")
                await page.mouse.click(click_x, click_y)
                await asyncio.sleep(3)

                post_expanded_path = os.path.join(SCREENSHOT_DIR, f"post_expanded_final_{int(time.time())}.png")
                await page.screenshot(path=post_expanded_path)
                logger.info("📸 Captured expanded post view.")

                analysis = claude.analyze_instagram_content(post_expanded_path)
                if analysis:
                    logger.info(f"📊 Final Claude analysis: {analysis}")
                else:
                    logger.warning("❌ Claude did not return a result for the final screenshot.")
                    return

            # After expansion or no click_target
            if analysis.get("is_shared_post"):
                logger.info(f"🎯 Shared post detected with confidence: {analysis.get('confidence', 0)}")
                logger.info(f"📎 Post URL: {post_url}")  # Ensure we're logging the correct URL here
                
                # Explicitly pass the correct post_url to Claude's analysis logic
                analysis["post_url"] = post_url

            else:
                logger.warning("⚠️ No valid shared post detected.")
        else:
            logger.warning("❌ Claude did not return usable analysis for DM screenshot.")

    else:
        logger.warning("⚠️ Claude Vision could not locate click target from screenshot.")
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

async def send_pdf_back_as_dm(page, pdf_path):
    logger.info("📤 Attempting to send PDF as DM reply...")
    try:
        # Step 1: Click the message textarea
        await page.click('textarea[placeholder="Message..."]')
        await page.fill('textarea[placeholder="Message..."]', "Here’s your recipe PDF! 📄")

        # Step 2: Attach the PDF via the hidden file input
        file_input = await page.query_selector('input[type="file"]')
        if file_input:
            await file_input.set_input_files(pdf_path)
            logger.info(f"📎 Attached file: {pdf_path}")
            await asyncio.sleep(2)  # Allow time for file to attach
        else:
            logger.warning("⚠️ File input not found for attaching PDF.")

        # Try pressing Enter to send
        await page.keyboard.press("Enter")
        await asyncio.sleep(2)

        # Optional fallback: click the Send button explicitly if Enter doesn't work
        send_button = await page.query_selector('svg[aria-label="Send"]')
        if send_button:
            await send_button.click()
            logger.info("✅ Clicked 'Send' button manually.")
    except Exception as e:
        logger.error(f"❌ Failed to send PDF via DM: {e}")

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
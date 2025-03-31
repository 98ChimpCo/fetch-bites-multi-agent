import asyncio
from playwright.async_api import async_playwright
import logging
from src.utils.claude_vision_assistant import ClaudeVisionAssistant
import os
from dotenv import load_dotenv
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("playwright-preview-clicker")

# CONFIGURATION
INSTAGRAM_URL = "https://www.instagram.com/direct/inbox/"
TARGET_USERNAME = "Shahin Zangenehpour"  # Username whose DM contains the preview

async def expand_post_preview(playwright):
    load_dotenv()
    logger.info("🔥 Running AI-VISION-ONLY version of playwright_preview_clicker.py")
    browser = await playwright.chromium.launch(headless=False, slow_mo=50)
    context = await browser.new_context(storage_state="auth_storage.json")
    page = await context.new_page()

    logger.info("Navigating to Instagram DMs...")
    await page.goto(INSTAGRAM_URL, wait_until="domcontentloaded")
    await asyncio.sleep(5)

    screenshot_path = f"screenshot_{int(time.time())}.png"
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
        chat_screenshot_path = f"chat_expanded_{int(time.time())}.png"
        await page.screenshot(path=chat_screenshot_path)
        logger.info("📸 Captured screenshot of opened DM view.")

        # 🔍 Step 2: Use Claude to find and click on the post preview in the DM thread
        preview_search_path = f"post_preview_search_{int(time.time())}.png"
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

                post_expanded_path = f"post_expanded_final_{int(time.time())}.png"
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
                logger.info(f"📎 Post URL: {analysis.get('post_url')}")
                
                post_url = analysis.get("post_url")
                if post_url:
                    try:
                        from src.services.pdf_helper import generate_pdf_and_return_path as process_post_and_generate_pdf
                        logger.info("🧪 Kicking off recipe extraction + PDF generation...")
                        try:
                            pdf_path = process_post_and_generate_pdf({"url": post_url})
                            if pdf_path:
                                logger.info(f"✅ PDF generated at: {pdf_path}")
                                logger.info("📤 (Mock) Sending PDF to user...")
                            else:
                                logger.warning("⚠️ No PDF generated from extracted content.")
                        except Exception as e:
                            logger.error(f"❌ Error during recipe processing: {e}")
                    except Exception as e:
                        logger.error(f"❌ Error during recipe processing: {e}")
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

async def main():
    async with async_playwright() as playwright:
        await expand_post_preview(playwright)

if __name__ == "__main__":
    asyncio.run(main())
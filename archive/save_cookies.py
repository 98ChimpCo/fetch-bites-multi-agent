# save_cookies.py
import asyncio
from playwright.async_api import async_playwright

async def save_login_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.instagram.com/accounts/login/")
        print("🔐 Please log in manually in the browser window...")

        await page.wait_for_timeout(30000)  # wait 30s for login
        await context.storage_state(path="auth_storage.json")
        print("✅ Login saved to auth_storage.json")

        await browser.close()

asyncio.run(save_login_state())
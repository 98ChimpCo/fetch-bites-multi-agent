# src/agents/instagram_monitor.py
import os
import time
import logging
import json
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Union
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class InstagramMonitorAgent:
    """Agent for monitoring Instagram accounts and identifying recipe posts"""
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.accounts: Dict[str, Dict] = {}
        self.processed_posts: Dict[str, datetime] = {}
        self.account_count = 0
        self._setup_browser()
        self._load_saved_state()
        
    def _setup_browser(self):
        """Set up headless browser for Instagram scraping"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        # Initialize the Chrome WebDriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        logger.info("Browser setup complete")
    
    def _load_saved_state(self):
        """Load previously monitored accounts and processed posts"""
        try:
            if os.path.exists("data/processed/monitor_state.json"):
                with open("data/processed/monitor_state.json", "r") as f:
                    state = json.load(f)
                    self.accounts = state.get("accounts", {})
                    self.processed_posts = {
                        k: datetime.fromisoformat(v) 
                        for k, v in state.get("processed_posts", {}).items()
                    }
                    self.account_count = len(self.accounts)
                    logger.info(f"Loaded state with {self.account_count} accounts and {len(self.processed_posts)} processed posts")
        except Exception as e:
            logger.error(f"Error loading saved state: {str(e)}")
            self.accounts = {}
            self.processed_posts = {}
            self.account_count = 0
    
    def _save_state(self):
        """Save current monitoring state"""
        try:
            os.makedirs("data/processed", exist_ok=True)
            with open("data/processed/monitor_state.json", "w") as f:
                state = {
                    "accounts": self.accounts,
                    "processed_posts": {
                        k: v.isoformat() 
                        for k, v in self.processed_posts.items()
                    }
                }
                json.dump(state, f)
            logger.info("Saved monitoring state")
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    async def login_to_instagram(self):
        """Log in to Instagram using credentials from environment variables"""
        try:
            self.driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(2)  # Wait for page to load
            
            # Accept cookies if the dialog appears
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
                )
                cookie_button.click()
                time.sleep(1)
            except:
                logger.info("No cookie consent dialog found")
            
            # Enter username
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_input.send_keys(os.getenv("INSTAGRAM_USERNAME"))
            
            # Enter password
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.send_keys(os.getenv("INSTAGRAM_PASSWORD"))
            
            # Click login button
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login was successful
            if "login" in self.driver.current_url:
                logger.error("Login to Instagram failed")
                return False
            
            logger.info("Successfully logged in to Instagram")
            return True
        except Exception as e:
            logger.error(f"Error during Instagram login: {str(e)}")
            return False
    
    async def add_account_to_monitor(self, username: str) -> bool:
        """Add an Instagram account to the monitoring list"""
        try:
            if username in self.accounts:
                logger.info(f"Account {username} is already being monitored")
                return True
            
            # Visit the account page to validate it exists
            self.driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(3)
            
            # Check if account exists
            if "Page Not Found" in self.driver.title:
                logger.error(f"Account {username} not found")
                return False
            
            # Add account to monitoring list
            self.accounts[username] = {
                "added": datetime.now().isoformat(),
                "last_checked": None,
                "recipe_posts_found": 0
            }
            self.account_count += 1
            
            # Save updated state
            self._save_state()
            
            logger.info(f"Added account {username} to monitoring list")
            return True
        except Exception as e:
            logger.error(f"Error adding account {username}: {str(e)}")
            return False
    
    async def check_for_new_posts(self, username: str, limit: int = 5) -> List[str]:
        """Check an account for new posts and return URLs of potential recipe posts"""
        try:
            logger.info(f"Checking for new posts from {username}")
            
            # Visit account page
            self.driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(3)
            
            # Find all post links
            post_links = []
            elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            for element in elements[:limit]:
                href = element.get_attribute("href")
                if href and href not in self.processed_posts:
                    post_links.append(href)
            
            # Update last checked time
            if username in self.accounts:
                self.accounts[username]["last_checked"] = datetime.now().isoformat()
                self._save_state()
            
            logger.info(f"Found {len(post_links)} new posts from {username}")
            return post_links
        except Exception as e:
            logger.error(f"Error checking posts for {username}: {str(e)}")
            return []
    
    async def is_recipe_post(self, post_url: str) -> bool:
        """Determine if a post is a recipe using Claude API"""
        try:
            # Extract post content
            content = await self.extract_post_content(post_url)
            if not content:
                return False
            
            # Combine caption and other metadata for analysis
            text_to_analyze = f"""
            Post Caption: {content.get('caption', '')}
            Hashtags: {', '.join(content.get('hashtags', []))}
            """
            
            # Use Claude to classify if this is a recipe post
            response = self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0,
                system="You are a specialist in identifying recipe posts. Respond with 'YES' if the Instagram post contains a recipe (ingredients and/or cooking instructions), or 'NO' if it does not. Only respond with YES or NO.",
                messages=[
                    {"role": "user", "content": text_to_analyze}
                ]
            )
            
            result = response.content[0].text.strip().upper()
            is_recipe = result == "YES"
            
            # Update processed posts
            self.processed_posts[post_url] = datetime.now()
            self._save_state()
            
            logger.info(f"Post {post_url} classified as recipe: {is_recipe}")
            return is_recipe
        except Exception as e:
            logger.error(f"Error classifying post {post_url}: {str(e)}")
            return False
    
    async def extract_post_content(self, post_url: str) -> Dict:
        """Extract content from an Instagram post"""
        try:
            logger.info(f"Extracting content from {post_url}")
            
            # Visit the post page
            self.driver.get(post_url)
            time.sleep(3)
            
            # Extract caption
            caption_element = None
            try:
                caption_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div._a9zs"))
                )
            except:
                logger.warning(f"No caption found for {post_url}")
            
            caption = caption_element.text if caption_element else ""
            
            # Extract hashtags from caption
            hashtags = re.findall(r'#\w+', caption)
            
            # Extract image URL or video thumbnail
            media_url = None
            try:
                # Try to find image
                img_element = self.driver.find_element(By.XPATH, "//div[@role='button']/img")
                media_url = img_element.get_attribute("src")
            except:
                try:
                    # Try to find video thumbnail
                    video_element = self.driver.find_element(By.TAG_NAME, "video")
                    media_url = video_element.get_attribute("poster")
                except:
                    logger.warning(f"No media found for {post_url}")
            
            # Extract post date
            post_date = None
            try:
                time_element = self.driver.find_element(By.TAG_NAME, "time")
                post_date = time_element.get_attribute("datetime")
            except:
                logger.warning(f"No date found for {post_url}")
            
            # Collect all data
            content = {
                "url": post_url,
                "caption": caption,
                "hashtags": hashtags,
                "media_url": media_url,
                "post_date": post_date,
                "extracted_at": datetime.now().isoformat()
            }
            
            # Save raw data
            os.makedirs("data/raw", exist_ok=True)
            post_id = post_url.split("/")[-2]
            with open(f"data/raw/{post_id}.json", "w") as f:
                json.dump(content, f)
            
            logger.info(f"Successfully extracted content from {post_url}")
            return content
        except Exception as e:
            logger.error(f"Error extracting content from {post_url}: {str(e)}")
            return {}
    
    async def start_monitoring(self, interval: int = 3600):
        """Start monitoring accounts for new recipe posts"""
        logger.info("Starting Instagram monitoring process")
        while True:
            try:
                # Log in to Instagram if needed
                if "instagram.com/accounts/login" in self.driver.current_url:
                    await self.login_to_instagram()
                
                # Check each account for new posts
                for username in self.accounts:
                    new_post_urls = await self.check_for_new_posts(username)
                    
                    # Check if each post is a recipe
                    for post_url in new_post_urls:
                        if await self.is_recipe_post(post_url):
                            self.accounts[username]["recipe_posts_found"] += 1
                            
                            # Here you would trigger the recipe extraction pipeline
                            # This will be implemented in the recipe_extractor.py file
                            logger.info(f"Recipe post found: {post_url}")
                            
                # Save updated state
                self._save_state()
                
                # Wait for the next check
                logger.info(f"Monitoring cycle complete. Waiting {interval} seconds for next cycle.")
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {str(e)}")
                await asyncio.sleep(60)  # Wait a bit before retrying
    
    def get_account_count(self) -> int:
        """Get the number of accounts being monitored"""
        return self.account_count
    
    def __del__(self):
        """Clean up resources"""
        try:
            self.driver.quit()
        except:
            pass

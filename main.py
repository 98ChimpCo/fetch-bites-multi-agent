"""
Main application for the Instagram Recipe Agent.
Ties together all components and provides the entry point.
"""

import logging
import os
import time
from typing import Optional
from dotenv import load_dotenv

from archive.instagram_monitor import InstagramMonitor
from archive.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator
from src.agents.delivery_agent import DeliveryAgent
from src.utils.user_state import UserStateManager
from src.utils.conversation_handler import ConversationHandler
from archive.instagram_message_adapter_vision_fixed_v2 import InstagramMessageAdapter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fetch_bites.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class FetchBitesApp:
    """Main application class for the Instagram Recipe Agent."""
    
    def __init__(self):
        """Initialize the application."""
        # Load environment variables
        load_dotenv()
        
        # Create data directories
        os.makedirs("data/users", exist_ok=True)
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("data/processed", exist_ok=True)
        os.makedirs("data/pdf", exist_ok=True)
        
        # Initialize components
        self._init_components()
        
    def _init_components(self):
        """Initialize all application components."""
        try:
            # Initialize user state manager
            self.user_state_manager = UserStateManager("data/users")
            
            # Initialize Instagram monitor
            self.instagram_monitor = InstagramMonitor()
            
            # Initialize recipe extractor
            self.recipe_extractor = RecipeExtractor()
            
            # Initialize PDF generator
            self.pdf_generator = PDFGenerator(
                output_dir="data/pdf"
            )
            
            # Initialize delivery agent
            self.delivery_agent = DeliveryAgent(
                smtp_server=os.getenv("SMTP_SERVER"),
                smtp_port=int(os.getenv("SMTP_PORT", "587")),
                smtp_username=os.getenv("SMTP_USERNAME"),
                smtp_password=os.getenv("SMTP_PASSWORD"),
                sender_email=os.getenv("EMAIL_SENDER")
            )
            
            # Initialize conversation handler
            self.conversation_handler = ConversationHandler(
                user_state_manager=self.user_state_manager,
                instagram_monitor=self.instagram_monitor,
                recipe_extractor=self.recipe_extractor,
                pdf_generator=self.pdf_generator,
                delivery_agent=self.delivery_agent
            )
            
            # Initialize Instagram message adapter
            self.instagram_message_adapter = InstagramMessageAdapter(
                username=os.getenv("INSTAGRAM_USERNAME"),
                password=os.getenv("INSTAGRAM_PASSWORD"),
                headless=True,
                check_interval=30
            )
            
            # Register message handler
            self.instagram_message_adapter.register_message_handler(
                self.conversation_handler.handle_message
            )
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise
            
    def start(self):
        """Start the application."""
        try:
            logger.info("Starting Fetch Bites application...")
            
            # Start monitoring Instagram messages
            self.instagram_message_adapter.start_message_monitoring()
            
        except KeyboardInterrupt:
            logger.info("Application stopped by user")
            self.stop()
        except Exception as e:
            logger.error(f"Error starting application: {str(e)}")
            self.stop()
            
    def stop(self):
        """Stop the application."""
        logger.info("Stopping Fetch Bites application...")
        
        # Stop Instagram message monitoring
        if hasattr(self, "instagram_message_adapter"):
            self.instagram_message_adapter.stop_message_monitoring()
            self.instagram_message_adapter.cleanup()
            
        logger.info("Application stopped")


def main():
    """Main entry point."""
    app = FetchBitesApp()
    app.start()


if __name__ == "__main__":
    main()

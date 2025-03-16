"""
Main application for the Instagram Recipe Agent with Claude Vision capabilities.
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import components
from src.agents.instagram_monitor import InstagramMonitor
from src.agents.recipe_extractor import RecipeExtractor
from src.agents.pdf_generator import PDFGenerator
from src.agents.delivery_agent import DeliveryAgent
from src.utils.instagram_message_adapter_vision import InstagramMessageAdapterVision
from src.utils.user_state_enhanced import UserStateManager
from src.utils.conversation_handler_enhanced import ConversationHandlerEnhanced
from src.utils.message_tracker import MessageTracker

class FetchBitesApp:
    """Main application for Fetch Bites Instagram Recipe Agent."""
    
    def __init__(self):
        """Initialize the Fetch Bites application."""
        try:
            # Create necessary directories
            os.makedirs("data/raw", exist_ok=True)
            os.makedirs("data/processed", exist_ok=True)
            os.makedirs("data/pdf", exist_ok=True)
            os.makedirs("data/users", exist_ok=True)
            os.makedirs("screenshots", exist_ok=True)
            
            # Initialize components
            self.message_tracker = MessageTracker()
            self.instagram_monitor = InstagramMonitor()
            self.recipe_extractor = RecipeExtractor()
            self.pdf_generator = PDFGenerator()
            self.user_state_manager = UserStateManager()
            
            # Initialize delivery agent
            self.delivery_agent = DeliveryAgent(
                smtp_server=os.getenv("SMTP_SERVER"),
                smtp_port=int(os.getenv("SMTP_PORT", "587")),
                smtp_username=os.getenv("SMTP_USERNAME"),
                smtp_password=os.getenv("SMTP_PASSWORD"),
                sender_email=os.getenv("EMAIL_SENDER")
            )

            # Initialize Instagram Message Adapter with Claude Vision
            self.instagram_message_adapter = InstagramMessageAdapterVision(
                username=os.getenv('INSTAGRAM_USERNAME'),
                password=os.getenv('INSTAGRAM_PASSWORD'),
                headless=False,
                check_interval=int(os.getenv('MONITORING_INTERVAL', '60')),
                message_tracker=self.message_tracker,
                claude_api_key=os.getenv('ANTHROPIC_API_KEY')
            )
            
            # Initialize Conversation Handler
            self.conversation_handler = ConversationHandlerEnhanced(
                user_state_manager=self.user_state_manager,
                instagram_monitor=self.instagram_monitor,
                recipe_extractor=self.recipe_extractor,
                pdf_generator=self.pdf_generator,
                delivery_agent=self.delivery_agent
            )
            
            # Register conversation handler with message adapter
            self.instagram_message_adapter.register_message_handler(
                self.conversation_handler.handle_message
            )
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Fetch Bites application: {str(e)}")
            raise
    
    def start(self):
        """Start the Fetch Bites application."""
        try:
            logger.info("Starting Fetch Bites application...")
            
            # Start Instagram message monitoring
            self.instagram_message_adapter.start_message_monitoring()
            
        except KeyboardInterrupt:
            logger.info("Application stopped by user")
        except Exception as e:
            logger.error(f"Error running Fetch Bites application: {str(e)}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources when shutting down."""
        try:
            # Stop Instagram message monitoring
            if hasattr(self, 'instagram_message_adapter') and self.instagram_message_adapter:
                self.instagram_message_adapter.stop_message_monitoring()
                self.instagram_message_adapter.cleanup()
                
            logger.info("Fetch Bites application cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up Fetch Bites application: {str(e)}")

if __name__ == "__main__":
    app = FetchBitesApp()
    app.start()

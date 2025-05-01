import os
import time
import signal
import logging
import json
from dotenv import load_dotenv

# Import the fixed version of the adapter
from archive.instagram_message_adapter_vision_fixed_v2 import InstagramMessageAdapterVision
from src.utils.user_state_enhanced import UserStateManager
from src.utils.conversation_handler_enhanced import ConversationHandler
from src.utils.claude_vision_assistant import ClaudeVisionAssistant

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class FetchBitesApp:
    """Main application for Fetch Bites Instagram Recipe Agent with improved error handling."""
    
    def __init__(self):
        """Initialize the Fetch Bites application."""
        # Load environment variables
        load_dotenv()
        
        # Get credentials from environment
        self.instagram_username = os.getenv("INSTAGRAM_USERNAME")
        self.instagram_password = os.getenv("INSTAGRAM_PASSWORD")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Validate required credentials
        if not self.instagram_username or not self.instagram_password:
            logger.error("Instagram credentials not found in environment variables")
            raise ValueError("Instagram credentials are required")
            
        if not self.anthropic_api_key:
            logger.warning("Anthropic API key not found. Visual analysis will be limited.")
        
        # Initialize components
        self.user_state_manager = UserStateManager()
        self.conversation_handler = ConversationHandler(
            self.user_state_manager, 
            self.send_message
        )
        
        # Initialize Claude Vision Assistant directly
        self.claude_assistant = ClaudeVisionAssistant(self.anthropic_api_key)
        
        # Initialize Instagram adapter with the improved version
        self.instagram_adapter = InstagramMessageAdapterVision(
            username=self.instagram_username,
            password=self.instagram_password,
            message_callback=self.handle_message,
            anthropic_api_key=self.anthropic_api_key,
            headless=False  # Set to True for production
        )
    
    def handle_message(self, sender: str, content: str):
        """
        Handle incoming messages from Instagram.
        
        Args:
            sender (str): Message sender
            content (str): Message content
        """
        try:
            logger.info(f"Received message from {sender}: '{content}'")
            
            # Process the message using conversation handler
            response = self.conversation_handler.process_message(sender, content)
            
            # Send response if available
            if response:
                # For debugging
                logger.info(f"Sending response to {sender}: '{response}'")
                
                success = self.send_message(sender, response)
                if not success:
                    logger.error(f"Failed to send response to {sender}")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    def send_message(self, recipient: str, message: str) -> bool:
        """
        Send a message to a recipient.
        
        Args:
            recipient (str): Message recipient
            message (str): Message content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use the improved _send_message_direct method
            return self.instagram_adapter._send_message_direct(message)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
    
    def start(self):
        """Start the Fetch Bites application."""
        logger.info("Starting Fetch Bites application...")
        
        # Start Instagram message monitoring
        self.instagram_adapter.start_monitoring(interval_seconds=10)
        
        # Handle termination signals
        def signal_handler(sig, frame):
            logger.info("Received termination signal, shutting down...")
            self.cleanup()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def cleanup(self):
        """Clean up resources."""
        # Stop monitoring
        self.instagram_adapter.stop_monitoring()
        
        # Clean up Instagram adapter
        self.instagram_adapter.cleanup()
        
        logger.info("Fetch Bites application cleaned up")

# Main entry point
if __name__ == "__main__":
    try:
        # Create and start application
        app = FetchBitesApp()
        
        # Log successful initialization
        logger.info("All components initialized successfully")
        
        # Start application
        app.start()
        
        # Keep application running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        # Handle manual termination
        logger.info("Application terminated by user")
        if 'app' in locals():
            app.cleanup()
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        # Attempt cleanup if possible
        if 'app' in locals():
            try:
                app.cleanup()
            except:
                pass
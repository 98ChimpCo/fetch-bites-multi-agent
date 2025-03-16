import os
import sys
import time
import signal
import logging
import json
import threading
import atexit
from dotenv import load_dotenv

# Import the fixed version of the adapter
try:
    # Try standard import path first
    from src.utils.instagram_message_adapter_vision_fixed_v2 import InstagramMessageAdapterVision
    from src.utils.user_state_enhanced import UserStateManager
    from src.utils.conversation_handler_enhanced import ConversationHandler
    from src.utils.claude_vision_assistant import ClaudeVisionAssistant
except ModuleNotFoundError:
    try:
        # If that fails, try to import from the current directory
        from instagram_message_adapter_vision_fixed_v2 import InstagramMessageAdapterVision
        from user_state_enhanced import UserStateManager
        from conversation_handler_enhanced import ConversationHandler
        from claude_vision_assistant import ClaudeVisionAssistant
    except ModuleNotFoundError:
        # As a last resort, try to import from a utils folder in the current directory
        from utils.instagram_message_adapter_vision_fixed_v2 import InstagramMessageAdapterVision
        from utils.user_state_enhanced import UserStateManager
        from utils.conversation_handler_enhanced import ConversationHandler
        from utils.claude_vision_assistant import ClaudeVisionAssistant

# Create a stop file path
STOP_FILE = "stop_app.txt"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Track processed messages to avoid duplicates
processed_messages = set()

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
        
        # Flag to track if app is running
        self.running = False
        
        # Flag to track if cleanup has been done
        self.cleanup_done = False
        
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
        
        # Register cleanup handlers
        atexit.register(self.cleanup)
        
        # Set up signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {sig}, shutting down...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def _create_message_hash(self, sender: str, content: str) -> str:
        """Create a unique hash for a message to avoid duplicate processing."""
        # Normalize the message content
        normalized_content = content.strip().lower()
        # Create a hash
        return f"{sender.lower()}:{normalized_content}"
    
    def handle_message(self, sender: str, content: str):
        """
        Handle incoming messages from Instagram.
        
        Args:
            sender (str): Message sender
            content (str): Message content
        """
        try:
            # Check if we've already processed this message
            message_hash = self._create_message_hash(sender, content)
            
            # Skip if already processed at the app level
            if message_hash in processed_messages:
                logger.info(f"Skipping already processed message from {sender}")
                return
                
            # Mark as processed
            processed_messages.add(message_hash)
            
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
        
        # Set running flag
        self.running = True
        
        # Create a "PID" file for easier process management
        with open("fetch_bites.pid", "w") as f:
            f.write(str(os.getpid()))
        
        # Remove stop file if it exists
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
        
        # Start Instagram message monitoring
        self.instagram_adapter.start_monitoring(interval_seconds=10)
        
        print("\n" + "=" * 80)
        print("Fetch Bites application is running!")
        print("- To stop gracefully, press Ctrl+C")
        print("- Or create a file named 'stop_app.txt' in this directory")
        print("=" * 80 + "\n")
        
        # Main loop with multiple stop conditions
        try:
            while self.running:
                # Check for stop file
                if os.path.exists(STOP_FILE):
                    logger.info("Stop file detected, shutting down...")
                    self.running = False
                    break
                
                # Sleep to avoid CPU usage
                time.sleep(1)
        except KeyboardInterrupt:
            # This should not be needed due to signal handler, but just in case
            logger.info("KeyboardInterrupt received, shutting down...")
            self.running = False
        finally:
            # Ensure cleanup
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        # Only run cleanup once
        if self.cleanup_done:
            return
            
        logger.info("Cleaning up resources...")
        
        # Stop monitoring
        try:
            self.instagram_adapter.stop_monitoring()
        except:
            pass
        
        # Clean up Instagram adapter
        try:
            self.instagram_adapter.cleanup()
        except:
            pass
        
        # Remove PID file
        try:
            if os.path.exists("fetch_bites.pid"):
                os.remove("fetch_bites.pid")
        except:
            pass
        
        # Remove stop file if it exists
        try:
            if os.path.exists(STOP_FILE):
                os.remove(STOP_FILE)
        except:
            pass
        
        # Mark cleanup as done
        self.cleanup_done = True
        
        logger.info("Fetch Bites application cleaned up")
        
        # Force exit to ensure all threads are terminated
        try:
            os._exit(0)
        except:
            pass

# Main entry point
if __name__ == "__main__":
    try:
        # Create and start application
        app = FetchBitesApp()
        
        # Log successful initialization
        logger.info("All components initialized successfully")
        
        # Start application
        app.start()
            
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        # Attempt cleanup if possible
        if 'app' in locals():
            try:
                app.cleanup()
            except:
                pass
        
        # Force exit on error
        os._exit(1)
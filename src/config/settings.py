import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Create a simple Settings class without Pydantic
class Settings:
    def __init__(self):
        # Project info
        self.PROJECT_NAME = "Fetch Bites Multi-Agent System"
        self.VERSION = "0.1.0"
        
        # API
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        
        # Database
        self.DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/fetch_bites.db")
        
        # Instagram
        self.INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
        self.INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")
        self.INSTAGRAM_MONITORING_INTERVAL = int(os.getenv("INSTAGRAM_MONITORING_INTERVAL", "3600"))
        
        # Email
        self.EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
        
        # Gmail or SendGrid settings
        self.GMAIL_USERNAME = os.getenv("GMAIL_USERNAME", "")
        self.GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
        self.SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
        
        # Configure SMTP based on what's available
        if self.GMAIL_USERNAME:
            self.SMTP_SERVER = "smtp.gmail.com"
            self.SMTP_USERNAME = self.GMAIL_USERNAME
            self.SMTP_PASSWORD = self.GMAIL_APP_PASSWORD
        elif self.SENDGRID_API_KEY:
            self.SMTP_SERVER = "smtp.sendgrid.net"
            self.SMTP_USERNAME = "apikey"
            self.SMTP_PASSWORD = self.SENDGRID_API_KEY
        else:
            self.SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
            self.SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
            self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        
        # Set up paths
        self.DATA_DIR = BASE_DIR / "data"
        self.RAW_DATA_DIR = self.DATA_DIR / "raw"
        self.PROCESSED_DATA_DIR = self.DATA_DIR / "processed"
        self.PDF_OUTPUT_DIR = self.PROCESSED_DATA_DIR / "pdfs"
        self.PDF_TEMPLATE_DIR = BASE_DIR / "templates" / "pdf"
        self.LOG_DIR = BASE_DIR / "logs"
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        for directory in [
            self.DATA_DIR,
            self.RAW_DATA_DIR,
            self.PROCESSED_DATA_DIR,
            self.PDF_OUTPUT_DIR,
            self.PDF_TEMPLATE_DIR,
            self.LOG_DIR
        ]:
            directory.mkdir(parents=True, exist_ok=True)

# Create settings instance
settings = Settings()
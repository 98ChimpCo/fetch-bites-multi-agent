"""
Delivery agent for the Instagram Recipe Agent.
Handles email delivery of recipe PDFs to users.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional

logger = logging.getLogger(__name__)

class DeliveryAgent:
    """Handles the delivery of recipe PDFs to users via email."""
    
    def __init__(
        self, 
        smtp_server: str, 
        smtp_port: int, 
        smtp_username: str, 
        smtp_password: str,
        sender_email: str
    ):
        """Initialize the delivery agent.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            smtp_username: SMTP username
            smtp_password: SMTP password
            sender_email: Sender email address
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        
    def send_recipe_email(self, recipient_email: str, recipe_title: str, pdf_path: str) -> bool:
        """Send a recipe PDF to a user via email.
        
        Args:
            recipient_email: Recipient email address
            recipe_title: Title of the recipe
            pdf_path: Path to the recipe PDF file
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return False
            
        try:
            # Create message
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message["Subject"] = f"Your Recipe Card: {recipe_title}"
            
            # Add email body
            body = f"""
Hello from Fetch Bites!

Attached is your recipe card for "{recipe_title}". 

Enjoy cooking and feel free to send us more recipes anytime!

Happy cooking!
The Fetch Bites Team
            """
            message.attach(MIMEText(body, "plain"))
            
            # Attach PDF
            with open(pdf_path, "rb") as file:
                attachment = MIMEApplication(file.read(), _subtype="pdf")
                attachment.add_header(
                    "Content-Disposition", 
                    f"attachment; filename={os.path.basename(pdf_path)}"
                )
                message.attach(attachment)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Recipe email sent to {recipient_email}: {recipe_title}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending recipe email: {str(e)}")
            return False
            
    def send_welcome_email(self, recipient_email: str) -> bool:
        """Send a welcome email to a new user.
        
        Args:
            recipient_email: Recipient email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message["Subject"] = "Welcome to Fetch Bites!"
            
            # Add email body
            body = """
Hello and welcome to Fetch Bites!

Thank you for using our service to turn Instagram recipes into printable recipe cards.

Here's how to use Fetch Bites:
1. Send us an Instagram post URL with a recipe
2. We'll extract the recipe details and create a formatted recipe card
3. We'll email the recipe card to you at this address

That's it! Simple and easy.

If you have any questions, just reply to our message on Instagram.

Happy cooking!
The Fetch Bites Team
            """
            message.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Welcome email sent to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            return False

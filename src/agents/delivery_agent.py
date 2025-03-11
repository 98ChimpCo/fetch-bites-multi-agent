# src/agents/delivery_agent.py
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formatdate

logger = logging.getLogger(__name__)

class DeliveryAgent:
    """Agent for delivering recipe PDFs to users via email"""
    
    def __init__(self):
        self.sent_count = 0
        self.last_sent = None
        self._load_stats()
        
        # Load email config from environment
        self.sender_email = os.getenv("EMAIL_SENDER", "recipes@example.com")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.sendgrid.net")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "apikey")
        self.smtp_password = os.getenv("SENDGRID_API_KEY", "")
        
        # Create email templates directory
        os.makedirs("templates", exist_ok=True)
        
        # Ensure email templates exist
        self._ensure_templates()
    
    def _load_stats(self):
        """Load delivery statistics"""
        try:
            if os.path.exists("data/processed/delivery_stats.json"):
                with open("data/processed/delivery_stats.json", "r") as f:
                    stats = json.load(f)
                    self.sent_count = stats.get("sent_count", 0)
                    self.last_sent = stats.get("last_sent")
        except Exception as e:
            logger.error(f"Error loading delivery stats: {str(e)}")
    
    def _save_stats(self):
        """Save delivery statistics"""
        try:
            os.makedirs("data/processed", exist_ok=True)
            with open("data/processed/delivery_stats.json", "w") as f:
                stats = {
                    "sent_count": self.sent_count,
                    "last_sent": self.last_sent
                }
                json.dump(stats, f)
        except Exception as e:
            logger.error(f"Error saving delivery stats: {str(e)}")
    
    def _ensure_templates(self):
        """Ensure that email templates exist"""
        template_path = "templates/recipe_email.html"
        
        if not os.path.exists(template_path):
            # Create a basic template
            with open(template_path, "w") as f:
                f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Recipe Card</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .content {
            padding: 20px 0;
        }
        .recipe-title {
            color: #e67e22;
            font-size: 24px;
            margin-bottom: 10px;
        }
        .footer {
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #777;
        }
        .button {
            display: inline-block;
            background-color: #e67e22;
            color: white !important;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 5px;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Your Recipe Card is Ready!</h1>
    </div>
    
    <div class="content">
        <p>Hello,</p>
        
        <p>We've prepared a recipe card for you from Instagram:</p>
        
        <h2 class="recipe-title">{{recipe_title}}</h2>
        
        <p>The recipe card is attached to this email as a PDF that you can save, print, or view on any device.</p>
        
        <p>We hope you enjoy making this delicious recipe!</p>
        
        <p>Original post: <a href="{{recipe_source}}">View on Instagram</a></p>
    </div>
    
    <div class="footer">
        <p>This email was sent because you signed up for recipe notifications from our service.</p>
        <p>To unsubscribe, reply to this email with "UNSUBSCRIBE" in the subject line.</p>
    </div>
</body>
</html>""")
    
    async def send_email(self, recipient_email: str, pdf_path: str, recipe_title: str, recipe_source: Optional[str] = None) -> bool:
        """Send recipe PDF via email"""
        try:
            logger.info(f"Preparing to send email to {recipient_email} with recipe: {recipe_title}")
            
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = f"Your Recipe Card: {recipe_title}"
            
            # Load email template
            with open("templates/recipe_email.html", "r") as f:
                template = f.read()
            
            # Replace placeholders
            email_content = template.replace("{{recipe_title}}", recipe_title)
            if recipe_source:
                email_content = email_content.replace("{{recipe_source}}", recipe_source)
            else:
                email_content = email_content.replace("{{recipe_source}}", "#")
            
            # Attach HTML content
            msg.attach(MIMEText(email_content, 'html'))
            
            # Attach PDF
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                
                # Add headers
                pdf_filename = os.path.basename(pdf_path)
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f"{recipe_title}.pdf")
                msg.attach(pdf_attachment)
            else:
                logger.error(f"PDF file not found: {pdf_path}")
                return False
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            # Update stats
            self.sent_count += 1
            self.last_sent = datetime.now().isoformat()
            self._save_stats()
            
            logger.info(f"Successfully sent email to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def get_sent_count(self) -> int:
        """Get the number of emails sent"""
        return self.sent_count

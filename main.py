import os
import logging
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
from src.agents.instagram_monitor import InstagramMonitorAgent
from src.agents.recipe_extractor import RecipeExtractorAgent
from src.agents.pdf_generator import PDFGeneratorAgent
from src.agents.delivery_agent import DeliveryAgent
from src.utils.db import init_db, get_db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("DEBUG") == "true" else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Instagram Recipe Agent")

# Initialize database
init_db()

# Define data models
class UserSignup(BaseModel):
    email: str
    instagram_account: str = None
    preferences: dict = {}

class RecipeProcessRequest(BaseModel):
    post_url: str
    email: str = None

# Initialize agents
monitor_agent = InstagramMonitorAgent()
recipe_agent = RecipeExtractorAgent()
pdf_agent = PDFGeneratorAgent()
delivery_agent = DeliveryAgent()

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks when the app starts"""
    logger.info("Starting Instagram Recipe Agent")

@app.post("/signup")
async def signup(user: UserSignup):
    """Sign up a new user to monitor Instagram accounts"""
    db = get_db()
    # Add user to database
    user_id = db.add_user(user.email, user.instagram_account, user.preferences)
    return {"status": "success", "user_id": user_id}

@app.post("/process")
async def process_recipe(recipe: RecipeProcessRequest, background_tasks: BackgroundTasks):
    """Process a specific Instagram post URL"""
    logger.info(f"Manual recipe processing request for {recipe.post_url}")
    
    # Add background task to process the recipe
    background_tasks.add_task(process_recipe_task, recipe.post_url, recipe.email)
    
    return {"status": "processing", "post_url": recipe.post_url}

@app.get("/status")
async def status():
    """Check the system status"""
    return {
        "status": "online",
        "monitored_accounts": monitor_agent.get_account_count(),
        "recipes_processed": recipe_agent.get_processed_count(),
        "pdfs_generated": pdf_agent.get_generated_count(),
        "emails_sent": delivery_agent.get_sent_count(),
    }

async def process_recipe_task(post_url: str, email: str = None):
    """Background task to process a recipe post"""
    try:
        # Extract content from Instagram post
        content = await monitor_agent.extract_post_content(post_url)
        
        # Extract recipe data
        recipe_data = await recipe_agent.extract_recipe(content)
        
        # Generate PDF
        pdf_path = await pdf_agent.generate_pdf(recipe_data)
        
        # If email is provided, deliver the PDF
        if email:
            await delivery_agent.send_email(email, pdf_path, recipe_data["title"])
            
        logger.info(f"Successfully processed recipe: {recipe_data['title']}")
        return True
    except Exception as e:
        logger.error(f"Error processing recipe: {str(e)}")
        return False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

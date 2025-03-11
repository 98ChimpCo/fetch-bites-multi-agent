# Instagram Recipe Agent - Getting Started Guide

This guide will help you set up and run your Instagram Recipe Agent locally before deploying it to a cloud environment.

## Prerequisites

Before you begin, make sure you have the following installed:
- Python 3.9 or higher
- Google Chrome (for web scraping with Selenium)
- Git (for version control)

## Step 1: Clone and Setup the Project

1. **Create a project directory**

```bash
mkdir instagram-recipe-agent
cd instagram-recipe-agent
```

2. **Create a virtual environment**

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Create the project structure**

```bash
mkdir -p src/{agents,utils,models,services,config}
mkdir -p data/{raw,processed,processed/pdfs}
mkdir -p src/utils/fonts
mkdir templates
```

4. **Create configuration files**

Create a `.env` file in the root directory with the following content:

```
# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
SENDGRID_API_KEY=your_sendgrid_api_key

# Instagram monitoring config
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# Email config
EMAIL_SENDER=your_sender_email@example.com
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey

# Application settings
DEBUG=true
MONITORING_INTERVAL=3600
```

5. **Create necessary files**

Create the following files using the code provided in previous steps:
- `main.py`
- `src/agents/instagram_monitor.py`
- `src/agents/recipe_extractor.py`
- `src/agents/pdf_generator.py`
- `src/agents/delivery_agent.py`
- `src/utils/db.py`
- `requirements.txt`

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Run the Application Locally

```bash
python -m uvicorn main:app --reload
```

This will start the FastAPI server on http://localhost:8000.

## Step 4: Test the Application

1. **Check the status endpoint**

Open your browser and navigate to: http://localhost:8000/status

You should see something like:
```json
{
  "status": "online",
  "monitored_accounts": 0,
  "recipes_processed": 0,
  "pdfs_generated": 0,
  "emails_sent": 0
}
```

2. **Register a user and add an Instagram account to monitor**

Send a POST request to http://localhost:8000/signup with the following JSON body:

```json
{
  "email": "your_email@example.com",
  "instagram_account": "some_food_account",
  "preferences": {
    "frequency": "daily",
    "categories": ["dinner", "dessert"]
  }
}
```

You can use curl, Postman, or any API testing tool.

3. **Process a specific recipe post**

Send a POST request to http://localhost:8000/process with the following JSON body:

```json
{
  "post_url": "https://www.instagram.com/p/SOME_POST_ID/",
  "email": "your_email@example.com"
}
```

## Step 5: Start Automatic Monitoring

The application has two main modes:

1. **On-demand processing**: Using the `/process` endpoint
2. **Automatic monitoring**: Started when the application runs

To run the application with automatic monitoring, modify the `main.py` file to start the monitoring process on startup:

```python
@app.on_event("startup")
async def startup_event():
    """Initialize background tasks when the app starts"""
    logger.info("Starting Instagram Recipe Agent")
    
    # Start monitoring in the background
    background_tasks = BackgroundTasks()
    background_tasks.add_task(monitor_agent.start_monitoring)
```

## Common Issues and Troubleshooting

### Instagram Login Issues

Instagram has security measures that may detect automation. If you encounter login issues:
- Try logging in manually first on the same machine
- Avoid using the same account for multiple instances
- Consider using an Instagram developer account

### Chrome/Selenium Issues

If Chrome or Selenium fails to start:
- Make sure Chrome is installed and up to date
- Check that chromedriver matches your Chrome version
- Try different Chrome options (see the `_setup_browser` method in `instagram_monitor.py`)

### PDF Generation Issues

If PDF generation fails:
- Ensure all font files are correctly downloaded
- Check that the required directories exist
- Verify the temporary image paths are correct

## Next Steps

After testing locally, you can:

1. Deploy to Replit using the Replit deployment guide
2. Set up continuous monitoring for recipe posts
3. Improve the email templates for better user experience
4. Implement additional features such as:
   - Recipe categorization
   - Nutritional information extraction
   - User preferences for types of recipes
   - Shopping list generation

## Troubleshooting

If you run into issues, check the logs in the console or in the `logs` directory. Most errors will be logged with detailed information.

For more specific help, refer to the documentation of the libraries used in this project:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Selenium](https://selenium-python.readthedocs.io/)
- [Anthropic Claude API](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [FPDF](https://pyfpdf.readthedocs.io/en/latest/)

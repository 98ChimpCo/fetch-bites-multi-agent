# Instagram Recipe Agent - Project Bible

## Project Overview

The Instagram Recipe Agent is an AI-powered system that automates the process of converting Instagram recipe posts into structured, printable PDF recipe cards. Using a combination of web scraping, natural language processing, and document generation, the system monitors Instagram accounts, identifies recipe posts, extracts recipe data, generates formatted PDFs, and delivers them to users via email.

## System Architecture

### Core Components

<figure>
  <img src="architecture_diagram.png" alt="System Architecture Diagram">
  <figcaption>High-level architecture of the Instagram Recipe Agent system</figcaption>
</figure>

1. **Instagram Monitor Agent**
   - Monitors specified Instagram accounts for new posts
   - Identifies recipe posts using AI classification
   - Extracts post content (text, images) for processing

2. **Recipe Extractor Agent**
   - Uses Claude API to extract structured recipe data from post content
   - Parses ingredients, instructions, cooking times, etc.
   - Formats data for PDF generation

3. **PDF Generator Agent**
   - Creates professionally formatted PDF recipe cards
   - Includes original post images when available
   - Adds QR codes linking back to original posts

4. **Delivery Agent**
   - Sends recipe PDFs to users via email
   - Manages user preferences and subscription settings
   - Tracks delivery metrics

5. **Web API**
   - Provides endpoints for user registration and management
   - Allows manual processing of specific Instagram posts
   - Reports system status and metrics

### Database Schema

The system uses SQLite for storage with the following structure:

- **users**: User registration and preferences
- **monitored_accounts**: Instagram accounts being tracked
- **user_account_subscriptions**: Links users to accounts they follow
- **processed_recipes**: Extracted and processed recipe data
- **delivered_recipes**: Records of recipe deliveries to users

## Technology Stack

### Current Dependencies (Updated)

```
# Core dependencies
fastapi>=0.104.0
uvicorn>=0.23.0
python-dotenv>=1.0.0
pydantic>=2.5.2,<3.0.0

# Database
sqlalchemy>=2.0.9

# Web scraping
requests>=2.28.2
beautifulsoup4>=4.12.2
selenium>=4.8.3
webdriver-manager>=3.8.5

# Processing
Pillow>=9.5.0
qrcode>=7.4.2
fpdf>=1.7.2
reportlab>=3.6.12

# AI services
anthropic>=0.49.0

# Email
aiosmtplib>=2.0.1
```

### Key APIs

1. **Anthropic Claude API**
   - Used for recipe identification and extraction
   - Requires API key and proper prompt engineering
   - Current implementation uses Claude 3 Sonnet

2. **SendGrid API**
   - Used for reliable email delivery
   - Requires API key and sender verification

## Implementation Guide

### Project Structure

```
instagram-recipe-agent/
├── main.py                  # FastAPI application entry point
├── .env                     # Environment variables
├── requirements.txt         # Dependencies
├── src/
│   ├── agents/
│   │   ├── instagram_monitor.py  # Instagram scraping and monitoring
│   │   ├── recipe_extractor.py   # Recipe data extraction with Claude
│   │   ├── pdf_generator.py      # PDF recipe card generation
│   │   └── delivery_agent.py     # Email delivery
│   ├── utils/
│   │   ├── db.py                 # Database operations
│   │   └── fonts/                # PDF font files
│   └── config/
│       └── settings.py           # Configuration settings
├── data/
│   ├── raw/                      # Raw scraped data
│   └── processed/                # Processed recipes and PDFs
├── templates/                    # Email templates
└── logs/                         # Application logs
```

### Instagram Monitoring Strategy

1. **Authentication**
   - Uses Selenium with a real Chrome browser instance
   - Requires Instagram credentials for login
   - Implements session management to avoid frequent logins

2. **Post Detection**
   - Periodically checks followed accounts for new posts
   - Uses Claude to classify posts as recipes or non-recipes
   - Maintains a database of processed posts to avoid duplicates

3. **Content Extraction**
   - Gets post captions, images, and metadata
   - Handles different post formats (single image, carousel, video)
   - Stores raw data for later reprocessing if needed

### Recipe Extraction Process

1. **Text Processing**
   - Sends post caption to Claude with specialized prompts
   - Extracts structured data for ingredients, instructions, metadata
   - Handles various recipe formats and styles

2. **Prompt Engineering**
   - Uses detailed system prompts to guide Claude's extraction
   - Includes examples of different recipe styles
   - Ensures consistent JSON output format

3. **Ingredient Parsing**
   - Separates quantities, units, and ingredient names
   - Standardizes measurements when possible
   - Handles special cases (e.g., "to taste", "a pinch of")

### PDF Generation

1. **Template System**
   - Uses FPDF library for PDF creation
   - Implements consistent design templates
   - Includes proper font handling for international characters

2. **Image Processing**
   - Incorporates post thumbnails in recipe cards
   - Resizes and optimizes images for PDF inclusion
   - Adds QR codes linking back to original posts

3. **Output Control**
   - Generates professional-looking recipe cards
   - Optimizes for both digital viewing and printing
   - Follows consistent styling across all recipes

### User Management

1. **Registration Process**
   - Captures email and Instagram accounts to follow
   - Stores user preferences (recipe types, delivery frequency)
   - Validates email addresses before sending

2. **Subscription Handling**
   - Allows users to follow multiple Instagram accounts
   - Manages frequency of updates and notifications
   - Provides unsubscribe mechanisms

## Deployment

### Local Development

1. **Environment Setup**
   - Python 3.9+ virtual environment
   - Dependencies installed via pip
   - Local SQLite database for testing

2. **Configuration**
   - Uses .env file for sensitive credentials
   - Configurable monitoring intervals and batch sizes
   - Debug mode for development

### Replit Deployment

1. **Platform Considerations**
   - Adapts Chrome/Selenium setup for Replit environment
   - Uses specific Replit configuration files (.replit, replit.nix)
   - Handles environment limitations (memory, CPU)

2. **Persistence**
   - Configures proper database storage
   - Manages file storage for PDFs and images
   - Implements backup strategies

## Future Enhancements

1. **Multilingual Support**
   - Extend recipe extraction to multiple languages
   - Implement language detection
   - Create language-specific PDF templates

2. **Content Enhancement**
   - Add nutritional information estimation
   - Include shopping list generation
   - Create meal planning suggestions

3. **User Experience**
   - Develop a web UI for account management
   - Add preference settings for recipe types
   - Implement recipe ratings and favorites

4. **Performance Optimization**
   - Add caching for frequently accessed data
   - Implement batch processing for Instagram monitoring
   - Add error recovery mechanisms

## API Documentation

### User API

#### POST /signup
Register a new user and subscribe to Instagram accounts.

**Request:**
```json
{
  "email": "user@example.com",
  "instagram_account": "food_blogger",
  "preferences": {
    "frequency": "daily",
    "categories": ["dinner", "dessert"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "user_id": 1
}
```

#### POST /process
Process a specific Instagram post URL.

**Request:**
```json
{
  "post_url": "https://www.instagram.com/p/ABCDEF/",
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "status": "processing",
  "post_url": "https://www.instagram.com/p/ABCDEF/"
}
```

#### GET /status
Check the system status.

**Response:**
```json
{
  "status": "online",
  "monitored_accounts": 10,
  "recipes_processed": 150,
  "pdfs_generated": 145,
  "emails_sent": 132
}
```

## Anthropic Claude Integration

### Recipe Extraction Prompt

```
Extract a complete recipe from this Instagram post caption.

CAPTION:
{caption}

HASHTAGS:
{hashtags}

Extract the following information in JSON format:
1. Recipe title
2. Recipe description (brief summary if available)
3. Ingredients list (with quantities and units when available)
4. Step-by-step instructions
5. Cooking time (prep time, cook time, total time)
6. Servings/yield
7. Any dietary information (vegan, gluten-free, etc.)
8. Difficulty level (easy, medium, hard)

Format the response as a valid JSON object with the following structure:
{
    "title": "Recipe Title",
    "description": "Brief description",
    "ingredients": [
        {
            "quantity": "1",
            "unit": "cup",
            "name": "flour"
        },
        ...
    ],
    "instructions": [
        "Step 1 instructions",
        "Step 2 instructions",
        ...
    ],
    "prep_time": "15 minutes",
    "cook_time": "30 minutes",
    "total_time": "45 minutes",
    "servings": "4",
    "dietary_info": ["vegan", "gluten-free"],
    "difficulty": "medium"
}
```

### Recipe Classification Prompt

```
You are a specialist in identifying recipe posts. Respond with 'YES' if the Instagram post contains a recipe (ingredients and/or cooking instructions), or 'NO' if it does not. Only respond with YES or NO.

Post Caption: {caption}
Hashtags: {hashtags}
```

## Maintenance Guidelines

1. **Instagram Changes**
   - Monitor for Instagram UI or API changes
   - Update selectors and navigation logic as needed
   - Implement exponential backoff for rate limiting

2. **Error Handling**
   - Log all errors with context information
   - Implement retry strategies for transient failures
   - Set up monitoring and alerts for critical issues

3. **Performance Monitoring**
   - Track processing times for each agent
   - Monitor resource usage (memory, CPU)
   - Optimize bottlenecks as identified

## Troubleshooting

### Common Issues

1. **Instagram Login Problems**
   - Check credentials in .env file
   - Verify IP is not blocked or restricted
   - Try using a different user agent

2. **Recipe Extraction Failures**
   - Review Claude prompt structure
   - Check for caption formatting edge cases
   - Ensure proper error handling

3. **PDF Generation Issues**
   - Verify font files are available
   - Check image processing code
   - Ensure temp directories are writable

4. **Email Delivery Issues**
   - Verify SMTP credentials
   - Check for email formatting problems
   - Monitor SendGrid quota and limits

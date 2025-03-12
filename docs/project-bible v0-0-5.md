# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** Iteration & Stabilization  
**Last Updated:** March 12, 2025

## Quick Reference
**Current Status:** Core scraping component stabilized, recipe extraction and PDF generation implemented  
**Next Milestone:** End-to-end workflow test with email delivery  
**Current Blockers:** None - Instagram content extraction fixed

## Project Goals
1. Primary Goal: Create an agentic AI system that converts Instagram recipe posts into structured PDF recipe cards
2. Secondary Goals: Automate monitoring, extraction, and delivery process with minimal human intervention
3. Success Criteria: Successfully extract recipe data from Instagram posts and generate PDF cards with >90% accuracy

## Progress Update

### Key Developments Since Last Update
1. **Fixed Instagram Content Extraction**
   - Resolved timeout issues when loading Instagram posts
   - Implemented multiple extraction strategies (JavaScript and selector-based)
   - Added comprehensive retry logic with progressive backoff
   - Implemented better error handling and debugging with screenshots

2. **Recipe Extraction Agent**
   - Implemented RecipeExtractor class with Claude API integration
   - Added fallback regex-based extraction for when API is unavailable
   - Enhanced parsing of ingredients, instructions, and metadata
   - Added structured output format for consistent processing

3. **PDF Generation**
   - Created PDFGenerator class for professional recipe cards
   - Implemented formatting for recipe details, ingredients, and instructions
   - Added image handling and inclusion in PDFs
   - Created consistent styling and layout

4. **Development Environment**
   - Created fresh virtual environment with proper dependencies
   - Implemented detailed logging for better debugging
   - Added screenshot capture at key points for visual debugging
   - Structured project for better modularization

## Technical Architecture
**Core Technologies:**
- Backend: Python, FastAPI (planned)
- Agents: 
  - InstagramMonitor: Selenium/ChromeDriver for Instagram interactions
  - RecipeExtractor: Claude API, regex fallback
  - PDFGenerator: FPDF, Pillow
  - DeliveryAgent: SendGrid (planned)
- Storage: SQLite (planned)
- Deployment: Docker, Replit (planned)

**Agent Architecture:**
- Instagram Monitor Agent: Identifies and extracts recipe posts
- Recipe Extractor Agent: Converts unstructured text to structured recipe data
- PDF Generator Agent: Creates formatted recipe PDFs
- Delivery Agent: Handles email distribution (in progress)

## Current Implementation Status

### Completed Components
1. **Instagram Monitor Agent**:
   - Status: ✅ Complete
   - Key Features: Post extraction, account monitoring, content analysis
   - Notes: Stable extraction with multiple fallback strategies

2. **Recipe Extractor Agent**:
   - Status: ✅ Complete
   - Key Features: Claude API integration, regex fallback, structured output
   - Notes: Works with both API and non-API approaches

3. **PDF Generator Agent**:
   - Status: ✅ Complete
   - Key Features: Professional recipe cards, image inclusion, consistent formatting
   - Notes: Creates attractive, printable recipe PDFs

4. **Test Workflow**:
   - Status: ✅ Complete
   - Key Features: Command-line testing, debugging support
   - Notes: Enables testing of extraction, recipe processing, and PDF generation

### In Progress
1. **Delivery Agent**:
   - Status: 🔄 Design phase
   - Current Focus: Email structure and delivery mechanism
   - Pending Items: SendGrid integration and email template design
   - Blockers: None

2. **End-to-end Workflow**:
   - Status: 🔄 Testing
   - Current Focus: Reliability of the entire pipeline
   - Pending Items: Edge case handling and error recovery
   - Blockers: None

### Planned/Todo
1. **Web API**:
   - Priority: Medium
   - Dependencies: Core agent functionality
   - Notes: FastAPI implementation for user interactions

2. **User Management**:
   - Priority: Medium
   - Dependencies: Web API
   - Notes: User subscriptions and preferences

3. **Deployment Configuration**:
   - Priority: Low
   - Dependencies: Complete workflow
   - Notes: Docker and Replit setup

## Implementation Details

### Instagram Monitor Agent
The Instagram Monitor Agent uses Selenium with ChromeDriver to interact with Instagram:

1. **Authentication**: 
   - Cookie-based for faster repeated access
   - Handles various login dialogs automatically
   - Implements anti-detection measures

2. **Content Extraction**:
   - Multiple extraction strategies for reliability
   - JavaScript execution for dynamic content
   - Selector-based fallbacks for different page structures

3. **Debugging**:
   - Screenshot capture at key points
   - Detailed logging of operations
   - Visual inspection of extraction stages

### Recipe Extractor Agent
The Recipe Extractor uses Claude AI for intelligent extraction:

1. **Claude Integration**:
   - Structured prompting for recipe identification
   - JSON output format for consistent parsing
   - Context-aware extraction of recipe components

2. **Fallback Mechanism**:
   - Regex-based extraction when API unavailable
   - Pattern matching for ingredients and instructions
   - Heuristic scoring for recipe identification

### PDF Generator Agent
The PDF Generator creates professional recipe cards:

1. **Layout**:
   - Clean design with consistent formatting
   - Proper spacing and section organization
   - Visual hierarchy for readability

2. **Content**:
   - Recipe title and description
   - Ingredient list with quantities
   - Numbered instructions
   - Additional metadata (prep time, cook time, etc.)

3. **Media**:
   - Post image inclusion
   - Image resizing and optimization
   - Source attribution and generation date

## Test Workflow

The test workflow provides an end-to-end testing mechanism:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Instagram Post  │ ──▶ │ Recipe Data     │ ──▶ │ PDF Recipe Card │
│ Extraction      │     │ Extraction      │     │ Generation      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Installation & Usage

### Environment Setup
```bash
# Create fresh virtual environment
python -m venv fresh_venv
source fresh_venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install selenium webdriver-manager requests pillow python-dotenv anthropic fpdf
```

### Required Environment Variables
```
# Instagram credentials
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# Anthropic API Key (optional - for better recipe extraction)
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Basic Usage
```bash
# Extract from a specific Instagram post
python test_workflow.py --url https://www.instagram.com/p/example123/

# Extract recipes from an account
python test_workflow.py --account foodblogger --limit 3

# Test with examples
python test_workflow.py
```

## Lessons Learned

1. **Instagram Automation Challenges**:
   - Instagram's anti-bot measures require sophisticated approaches
   - Multiple extraction strategies are essential for reliability
   - Visual debugging with screenshots is invaluable

2. **AI Recipe Extraction**:
   - Claude API provides superior extraction quality
   - Fallback mechanisms are important for robustness
   - Structured prompting is key to consistent results

3. **Architecture Decisions**:
   - Modular agent design enables independent development
   - Clear interfaces between components simplify testing
   - Proper error handling is critical for stability

## Next Steps

1. **Delivery Agent Implementation**:
   - Implement email delivery with SendGrid
   - Create HTML email templates
   - Add scheduling and rate limiting

2. **Web API Development**:
   - Create FastAPI endpoints for user interaction
   - Implement authentication and authorization
   - Add monitoring dashboard

3. **User Management**:
   - Develop subscription mechanism
   - Add preference management
   - Implement user storage

4. **Deployment**:
   - Create Docker configuration
   - Set up Replit deployment
   - Implement monitoring and logging

## Reference Materials

### Code Implementation

**RecipeExtractor Example**:
```python
def extract_recipe(self, text: str) -> Optional[Dict]:
    """
    Extract structured recipe data from text
    
    Args:
        text (str): Text to extract recipe from
        
    Returns:
        dict: Structured recipe data or None if extraction fails
    """
    try:
        logger.info("Extracting recipe from text...")
        
        # Check if text is too short to be a recipe
        if len(text.split()) < 20:
            logger.warning("Text too short to extract recipe")
            return None
            
        # Use Claude API if available, otherwise use regex-based extraction
        if self.client:
            return self._extract_with_claude(text)
        else:
            logger.warning("Claude API not available, using fallback extraction")
            return self._extract_with_regex(text)
            
    except Exception as e:
        logger.error(f"Failed to extract recipe: {str(e)}")
        return None
```

**Instagram Content Extraction**:
```python
def extract_post_content(self, post_url, max_retries=3):
    """Extract content from an Instagram post"""
    driver = None
    try:
        # Set up WebDriver if not already done
        if not self.driver:
            driver = self._setup_webdriver()
            self.login(driver)
        else:
            driver = self.driver
            
        logger.info(f"Extracting content from {post_url}...")
        
        # Implement retry logic
        for attempt in range(max_retries):
            try:
                # Navigate to the post
                driver.get(post_url)
                
                # Wait for content to load
                # Multiple extraction strategies
                # ...
                
                # If we have content, break out of the retry loop
                if content and content.get('caption'):
                    return content
                
                # Wait before retry
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error on attempt {attempt+1}: {str(e)}")
                continue
        
        # All retries failed
        return None
        
    except Exception as e:
        logger.error(f"Failed to extract post content: {str(e)}")
        return None
    finally:
        # Clean up resources
        if driver and driver != self.driver:
            driver.quit()
```

### Claude Extraction Prompt

```
Extract a complete recipe from this Instagram post caption.

CAPTION:
{caption}

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

---
[End of Project Bible - Last Updated: March 12, 2025]

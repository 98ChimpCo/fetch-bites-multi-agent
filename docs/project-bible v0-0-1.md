# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** Design & Implementation  
**Last Updated:** March 10, 2025

## Quick Reference
**Current Status:** Architecture and core code components designed, ready for implementation  
**Next Milestone:** Local MVP development with basic Instagram scraping and recipe extraction  
**Current Blockers:** None - development environment setup pending

## Project Goals
1. Primary Goal: Create an agentic AI system that converts Instagram recipe posts into structured PDF recipe cards
2. Secondary Goals: Automate monitoring, extraction, and delivery process with minimal human intervention
3. Success Criteria: Successfully extract recipe data from Instagram posts and generate PDF cards with >90% accuracy

## Key Decisions Log
| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|------------------------|
| 2025-03-10 | Use multi-agent architecture | Modular design for independent component development | Monolithic application |
| 2025-03-10 | Use Claude API for extraction | Superior contextual understanding for recipe text | Custom NLP models, OpenAI API |
| 2025-03-10 | Use Selenium for Instagram scraping | More reliable than API for caption extraction | Graph API, third-party services |
| 2025-03-10 | Use FastAPI for backend | Lightweight, async-compatible framework | Flask, Django |
| 2025-03-10 | Use SQLite for local storage | Simple setup for MVP phase | PostgreSQL, MongoDB |
| 2025-03-10 | Focus on caption-based extraction | Simplifies MVP, most recipes include details in caption | Video frame analysis |

## Technical Architecture
**Core Technologies:**
- Backend: Python, FastAPI
- Agents: Claude API, Selenium
- Storage: SQLite
- PDF Generation: fpdf
- Email: SendGrid
- Deployment: Docker, Replit

**Agent Architecture:**
- Instagram Monitor Agent: Identifies and extracts recipe posts
- Recipe Extractor Agent: Converts unstructured text to structured recipe data
- PDF Generator Agent: Creates formatted recipe PDFs
- Delivery Agent: Handles email distribution

## Current Implementation Status

### Completed Components
- Architecture Design:
  - Status: Complete
  - Key Features: Multi-agent system with defined responsibilities
  - Notes: Modular design allows for independent development of components

### In Progress
- Core Agent Implementation:
  - Status: Initial code designed
  - Current Focus: Instagram Monitor Agent and Recipe Extractor
  - Pending Items: Actual implementation and testing
  - Blockers: None

### Planned/Todo
- Development Environment Setup:
  - Priority: Immediate
  - Dependencies: None
  - Notes: Set up virtual environment, dependency installation, and API keys

- User Management System:
  - Priority: Medium
  - Dependencies: Core agent functionality
  - Notes: Create subscription and preference management

- Deployment Configuration:
  - Priority: Medium
  - Dependencies: Working local implementation
  - Notes: Docker and Replit deployment configurations

## API/Data Structures
```python
# Core recipe data structure
recipe_data = {
    "title": "Recipe Title",
    "description": "Brief description",
    "ingredients": [
        {
            "quantity": "1",
            "unit": "cup",
            "name": "flour"
        },
        # More ingredients
    ],
    "instructions": [
        "Step 1 instructions",
        "Step 2 instructions",
        # More steps
    ],
    "prep_time": "15 minutes",
    "cook_time": "30 minutes",
    "total_time": "45 minutes",
    "servings": "4",
    "dietary_info": ["vegan", "gluten-free"],
    "difficulty": "medium",
    "source": {
        "platform": "Instagram",
        "url": "https://instagram.com/p/xyz123",
        "extraction_date": "2025-03-10T12:34:56"
    }
}
```

## Outstanding Questions/Issues
1. Instagram Access Limitations
   - Status: To be evaluated during implementation
   - Impact: Could affect reliability of monitoring
   - Next Steps: Implement rate limiting and rotation strategies

2. Recipe Extraction Accuracy
   - Status: To be evaluated
   - Impact: Critical for system value
   - Next Steps: Fine-tune Claude prompts, implement feedback mechanisms

## Reference Materials
### Code Repositories
- Main Repository: `fetch-bites-multi-agent`
- Structure:
  - `src/agents/`: Agent implementation files
  - `src/utils/`: Utility functions and helpers
  - `data/`: Data storage directory
  - `templates/`: Email and PDF templates

### Code Snippets
```python
# Example Claude recipe extraction prompt
prompt = f"""
Extract a complete recipe from this Instagram post caption.

CAPTION:
{caption}

HASHTAGS:
{hashtags_text}

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
{{
    "title": "Recipe Title",
    "description": "Brief description",
    "ingredients": [
        {{
            "quantity": "1",
            "unit": "cup",
            "name": "flour"
        }},
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
}}

If any information is not available, use null or an empty array as appropriate.
If you cannot extract a complete recipe, return as much information as possible.
"""
```

### Configuration
- Environment variables needed:
  ```
  ANTHROPIC_API_KEY=your_anthropic_api_key
  SENDGRID_API_KEY=your_sendgrid_api_key
  EMAIL_SENDER=your_email@example.com
  SMTP_SERVER=smtp.sendgrid.net
  SMTP_PORT=587
  SMTP_USERNAME=apikey
  INSTAGRAM_USERNAME=your_instagram_username
  INSTAGRAM_PASSWORD=your_instagram_password
  ```

## Implementation Plan
| Phase | Timeline | Deliverables |
|-------|----------|--------------|
| MVP Setup | Week 1 | Development environment, core agent skeletons |
| MVP Implementation | Week 2 | Basic version of all agents working locally |
| Testing & Refinement | Week 3 | Improved extraction accuracy, error handling |
| Deployment | Week 4 | Working system on Replit or cloud provider |

## Notes for Next Steps
- Start by implementing the Instagram Monitor Agent and testing basic scraping
- Focus on reliable caption extraction before enhancing recipe extraction
- Implement recipe extraction with Claude and test with variety of recipe formats
- Develop PDF generator with simple template before adding more advanced designs
- Set up basic email delivery system
- Integrate all components and test end-to-end flow
- Deploy to Replit for initial testing
- Enhance with additional features based on performance

---
[End of Project Bible - Last Updated: March 10, 2025]

# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** Implementation & Testing  
**Last Updated:** March 11, 2025

## Quick Reference
**Current Status:** Core components implemented, environment set up, initial testing in progress  
**Next Milestone:** Fixing Instagram recipe extraction and improving integration testing  
**Current Blockers:** Instagram post content extraction reliability

## Implementation Progress

### Completed
1. ✅ Project architecture and component design
2. ✅ Development environment setup with fresh Python virtual environment
3. ✅ Requirements installation
4. ✅ Core agent code implementation:
   - Instagram Monitor Agent
   - Recipe Extractor Agent
   - PDF Generator Agent
   - Delivery Agent
5. ✅ Settings module with environment variable support
6. ✅ Directory structure for data storage

### In Progress
1. 🔄 Integration testing with test_workflow.py
2. 🔄 Debugging Instagram content extraction issues
3. 🔄 Improving recipe extraction reliability

### Pending
1. ⏳ FastAPI backend implementation
2. ⏳ User management system
3. ⏳ Email delivery testing
4. ⏳ Deployment configuration

## Key Decisions & Changes

| Date | Decision/Change | Rationale |
|------|----------|-----------|
| 2025-03-11 | Updated settings module to use plain Python class instead of Pydantic | Resolved validation issues with Pydantic v2 |
| 2025-03-11 | Implemented file naming convention with underscores | Python module compatibility |
| 2025-03-11 | Created fresh virtual environment | Resolved dependency conflicts |

## Development Environment

### Setup Instructions
1. Create and activate virtual environment:
   ```bash
   python -m venv fresh_venv
   source fresh_venv/bin/activate  # On macOS/Linux
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables in .env file:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   GMAIL_USERNAME=your.email@gmail.com
   GMAIL_APP_PASSWORD=your_app_password
   EMAIL_SENDER=your.email@gmail.com
   ```

### Testing Workflow
1. Run the test script to verify Instagram content extraction and recipe parsing:
   ```bash
   python test_workflow.py
   ```

2. Check logs and output in data/test directory

## Current Challenges & Next Steps

### Instagram Content Extraction
- **Issue:** Difficulty extracting captions from some Instagram posts
- **Symptoms:** "No caption found" errors, empty captions
- **Next Steps:**
  - Improve Selenium selectors for post content extraction
  - Add retry logic and wait times for page loading
  - Test with different post URLs and formats

### Recipe Extraction
- **Issue:** Insufficient content for recipe extraction
- **Symptoms:** "Caption too short to extract recipe" errors
- **Next Steps:**
  - Refine caption length threshold
  - Improve handling of partial recipe data
  - Add fallback extraction methods

## Updated Architecture

```
fetch-bites-multi-agent/
├── main.py                       # FastAPI application entry point
├── test_workflow.py              # Integration test script
├── requirements.txt              # Dependencies
├── .env                          # Environment variables
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
│   ├── processed/                # Processed recipes and PDFs
│   └── test/                     # Test output data
└── templates/                    # Email and PDF templates
```

## Next Milestone Plan
1. Fix Instagram content extraction issues
   - Update selectors in instagram_monitor.py
   - Add explicit waits for dynamic content
   - Test with different post types

2. Enhance recipe extraction robustness
   - Adjust minimum content requirements
   - Improve Claude prompting
   - Add post classification logic

3. Complete integration testing
   - End-to-end workflow test
   - PDF generation verification
   - Email delivery testing

4. Begin FastAPI backend implementation
   - Simple endpoints for testing
   - Post processing API
   - Status monitoring

## Questions & Considerations

1. Should we implement a better rate-limiting strategy for Instagram to avoid IP blocks?
2. Is the current Claude prompt optimal for recipe extraction?
3. Should we add image analysis for recipes that are primarily in image format?
4. Do we need to implement error recovery for partial extraction failures?

---
[End of Updated Project Bible - Last Updated: March 11, 2025]

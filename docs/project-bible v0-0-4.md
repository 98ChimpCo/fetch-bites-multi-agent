# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** Implementation & Testing  
**Last Updated:** March 11, 2025

## Quick Reference
**Current Status:** Instagram scraping component partially implemented, recipe extraction ready  
**Next Milestone:** Reliable Instagram post content extraction for recipe identification  
**Current Blockers:** Instagram automation challenges, handling diverse post formats

## Project Goals
1. Primary Goal: Create an agentic AI system that converts Instagram recipe posts into structured PDF recipe cards
2. Secondary Goals: Automate monitoring, extraction, and delivery process with minimal human intervention
3. Success Criteria: Successfully extract recipe data from Instagram posts and generate PDF cards with >90% accuracy

## Progress Update
Since the original project bible, we have made significant progress:

1. **Architecture Implementation**
   - Created modular architecture with separate agents for different tasks
   - Developed Instagram monitor agent with anti-detection measures
   - Implemented recipe extractor agent with Claude API integration

2. **Instagram Authentication**
   - Successfully implemented login process with cookie persistence
   - Added robust handling of various login dialogs
   - Implemented human-like interaction patterns to avoid detection

3. **Recipe Extraction Capabilities**
   - Developed capability to extract recipes from external websites
   - Implemented JSON-LD structured data parsing
   - Added fallback HTML parsing for non-structured recipe sites

## Technical Architecture
**Core Technologies:**
- Backend: Python, FastAPI
- Agents: Claude API, Selenium/Puppeteer
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
- Instagram Login Process:
  - Status: Working
  - Key Features: Cookie persistence, robust dialog handling, anti-detection measures
  - Notes: Successfully authenticates to Instagram

- Web Recipe Extraction:
  - Status: Working
  - Key Features: Extracts recipes from linked websites via JSON-LD or HTML parsing
  - Notes: Provides structured recipe data when available on external sites

- Recipe Extraction via Claude:
  - Status: Ready for integration
  - Key Features: Extracts structured recipe data from text captions
  - Notes: Works well with detailed recipe captions

### In Progress
- Instagram Post Content Extraction:
  - Status: Partial implementation
  - Current Focus: Reliable extraction of post captions and embedded links
  - Challenges: Instagram's anti-scraping measures, varying post formats
  - Approach: JavaScript-based DOM manipulation for more flexible extraction

- PDF Generation:
  - Status: Design phase
  - Dependencies: Structured recipe data
  - Notes: Will implement once recipe extraction is stable

### Planned/Todo
- Deployment Configuration:
  - Priority: Medium
  - Dependencies: Working local implementation
  - Notes: Docker and Replit deployment configurations

- User Management System:
  - Priority: Low
  - Dependencies: Core agent functionality
  - Notes: Create subscription and preference management

## Key Challenges & Solutions

### Instagram Automation Challenges

#### Challenge: Instagram Anti-Bot Detection
Instagram actively employs measures to detect and block automated browsers, making scraping difficult.

**Solutions Implemented:**
1. Browser fingerprinting prevention via:
   - WebDriver property masking
   - User-agent randomization
   - Chrome plugin simulation
   - JavaScript execution for DOM manipulation

2. Human-like interaction patterns:
   - Variable typing speed
   - Random delays between actions
   - Natural navigation patterns

3. Session persistence:
   - Cookie storage and reuse
   - Session recovery mechanisms

#### Challenge: Dynamic UI Changes
Instagram frequently updates their UI, breaking selectors and making automation fragile.

**Solutions Implemented:**
1. Multiple selector strategies:
   - Trying several selectors for each element
   - Using JavaScript for flexible element targeting
   - Implementing fallback mechanisms

2. Comprehensive logging:
   - Screenshot capture at key points
   - Detailed error tracking
   - Step-by-step operation logging

### Recipe Extraction Challenges

#### Challenge: Varied Recipe Formats
Recipes appear in different formats across Instagram captions and linked websites.

**Solutions Implemented:**
1. Multi-source extraction:
   - Direct caption extraction with Claude
   - Website scraping for linked recipes
   - JSON-LD structured data parsing
   - Fallback HTML parsing

2. Prompt engineering:
   - Specialized Claude prompts for recipe identification
   - Structured JSON response formatting
   - Consistent recipe schema

## Alternative Approaches Considered

### Approach 1: Instagram Graph API
Using Instagram's official API rather than browser automation.

**Pros:**
- More reliable and stable
- Official, permitted method
- Less prone to breakage

**Cons:**
- Requires Facebook Developer account
- Limited access to public content
- Approval process needed
- More setup required

**Status:** Alternative option if browser automation continues to be challenging

### Approach 2: Proxy Services
Using specialized third-party services for Instagram data retrieval.

**Pros:**
- Handles anti-detection measures
- More reliable access
- Simpler implementation

**Cons:**
- Cost associated with API calls
- Dependency on external service
- Potential rate limiting

**Status:** Fallback option for production use

## Next Steps

### Immediate Priorities
1. Fix the post content extraction timeout issue
   - Increase wait times for content loading
   - Implement more robust content detection strategies
   - Add additional error recovery mechanisms

2. Implement sequential post processing
   - Ensure proper driver reuse between posts
   - Handle post-specific errors without stopping entire process
   - Implement better retry logic

3. Test with diverse Instagram post types
   - Single-image recipe posts
   - Multi-image carousel posts
   - Posts with recipe links in bio
   - Posts with direct website links

### Medium-term Goals
1. Complete the end-to-end workflow
   - Integrate recipe extraction with Claude
   - Implement PDF generation
   - Create email delivery system

2. Add robustness features
   - Comprehensive error handling
   - Automated retries with exponential backoff
   - System state persistence

3. Prepare for deployment
   - Package dependencies
   - Configure environment variables
   - Create deployment documentation

## Notes on Instagram Scraping Approach

Based on our testing and development, we've refined our approach to Instagram scraping:

1. **Cookie-Based Authentication**
   - Login manually or through automation once
   - Save and reuse cookies for future sessions
   - Only perform full login when cookies expire

2. **JavaScript-Based Extraction**
   - Use JavaScript execution within Selenium for more flexible DOM manipulation
   - Define element finding strategies that don't rely on specific CSS classes
   - Implement content extraction based on element relationships rather than fixed selectors

3. **Multiple Fallback Strategies**
   - Implement chain of extraction methods for each data point
   - Use progressive enhancement approach (try best method, fall back to alternatives)
   - Incorporate manual extraction option for critical cases

## Lessons Learned

### 1. Instagram Automation Complexity
Modern social media platforms employ sophisticated measures to prevent automation. Simple selector-based approaches are too brittle, requiring more advanced techniques.

### 2. Multi-Strategy Approach
Having multiple fallback strategies for key operations is essential. When one approach fails, alternatives can often succeed.

### 3. Importance of Monitoring
Detailed logging and screenshot capture is critical for debugging automation issues that may not be apparent from code inspection alone.

### 4. Recipe Data Structure Variability
Recipe data appears in many formats across different sources, requiring flexible extraction approaches that can adapt to varied structures.

## Next Development Phase Focus

The next phase of development will focus on:

1. Refining Instagram post content extraction
2. Implementing comprehensive recipe extraction with Claude API
3. Creating visual PDF recipe card generation
4. Building a simple email delivery system
5. Testing the end-to-end workflow with various recipe post types

---

[End of Project Bible - Last Updated: March 11, 2025]

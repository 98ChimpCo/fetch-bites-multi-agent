# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** MVP Testing & Debugging  
**Last Updated:** March 15, 2025

## Quick Reference
**Current Status:** Core functionality working, fixing DM interaction bugs  
**Next Milestone:** Complete functioning Instagram conversation workflow  
**Current Blockers:** None - identified and fixed email validation bug

## Project Goals
1. Primary Goal: Create an agentic AI system that converts Instagram recipe posts into structured PDF recipe cards
2. Secondary Goals: Automate monitoring, extraction, and delivery process with minimal human intervention
3. Success Criteria: Successfully extract recipe data from Instagram posts and generate PDF cards with >90% accuracy

## Progress Update
As of March 15, 2025, we have made significant progress on the Instagram Recipe Agent:

1. **Instagram Message Monitoring**
   - Successfully implemented Instagram login and session management
   - Created reliable message detection in Instagram DMs
   - Implemented error handling and recovery for automation challenges
   - Added unread message focus to avoid duplicate processing

2. **Conversation Flow Implementation**
   - Built complete conversation state management system
   - Added user preference and data persistence
   - Implemented email validation and collection
   - Fixed bugs in email validation logic

3. **Database Implementation**
   - Created SQLite database with proper schema
   - Implemented recipe storage and retrieval
   - Added user preference management
   - Built monitoring system for processed recipes

4. **Recipe Extraction**
   - Successfully implemented extraction agent with Claude API integration
   - Added JSON formatting for consistent recipe structure
   - Implemented fallback extraction approaches
   - Created validation for extracted recipes

## Technical Architecture
**Core Technologies:**
- Backend: Python, FastAPI (planned)
- Agents: 
  - InstagramMessageAdapter: Selenium/ChromeDriver for Instagram DM monitoring
  - InstagramMonitor: Selenium/ChromeDriver for Instagram post extraction
  - RecipeExtractor: Claude API, regex fallback
  - PDFGenerator: ReportLab
  - DeliveryAgent: SendGrid (planned)
- Storage: SQLite
- Deployment: Docker, Replit (planned)

**Agent Architecture:**
- Instagram Message Adapter: Monitors Instagram DMs for recipe shares and user interactions
- Instagram Monitor Agent: Identifies and extracts recipe posts
- Recipe Extractor Agent: Converts unstructured text to structured recipe data
- PDF Generator Agent: Creates formatted recipe PDFs
- Delivery Agent: Handles email distribution

## Current Implementation Status

### Completed Components
1. **Instagram Login & Session Management**:
   - Status: ✅ Complete
   - Key Features: Cookie persistence, robust dialog handling, anti-detection measures
   - Notes: Successfully authenticates and navigates Instagram

2. **Message Monitoring System**:
   - Status: ✅ Complete
   - Key Features: Conversation detection, unread message focus, recovery mechanisms
   - Notes: Reliably detects and processes conversations

3. **User State Management**:
   - Status: ✅ Complete
   - Key Features: Conversation state tracking, file-based persistence, preferences storage
   - Notes: Maintains user context across interactions

4. **Database System**:
   - Status: ✅ Complete
   - Key Features: User management, recipe storage, subscription handling
   - Notes: Provides reliable data persistence

### In Progress
1. **Conversation Flow**:
   - Status: 🔄 Bug fixing
   - Current Focus: Resolving email validation and message response issues
   - Pending Items: Testing with diverse user interactions
   - Blockers: None - identified and fixed email validation bug

2. **Recipe Extraction Integration**:
   - Status: 🔄 Testing
   - Current Focus: Connecting extraction with conversation flow
   - Pending Items: Error handling for extraction failures
   - Blockers: None

### Planned/Todo
1. **Email Delivery System**:
   - Priority: High
   - Dependencies: Functioning conversation flow
   - Notes: Integrate with SendGrid for reliable delivery

2. **User Management Web UI**:
   - Priority: Medium
   - Dependencies: FastAPI implementation
   - Notes: Create simple dashboard for recipe management

3. **Deployment Configuration**:
   - Priority: Medium
   - Dependencies: Complete workflow
   - Notes: Docker and Replit setup

## Recent Bug Fixes

### Email Validation Bug
We identified and fixed a critical bug in the email validation logic:

1. **Issue**: The `is_valid_email()` method in the `UserStateManager` class was missing the `self` parameter, causing errors when called from instance methods.

2. **Solution**: Updated the method signature to include `self` as the first parameter:
   ```python
   def is_valid_email(self, email: str) -> bool:
       """Check if the given string is a valid email address."""
       # Method implementation...
   ```

3. **Impact**: This fix resolves the errors occurring during user interactions when email validation is performed, enabling the conversation flow to work properly.

### Message Input Field Detection
We've identified issues with message input field detection and implemented multiple approaches:

1. **Multiple Selector Strategies**: Added varied selectors for input field detection using CSS selectors, XPath, and JavaScript techniques.

2. **JavaScript DOM Manipulation**: Implemented specialized JavaScript for more flexible field detection and interaction.

3. **Viewport Coordinate Fallback**: Added alternative approach using screen coordinates when selectors fail.

## Next Steps

1. **Complete DM Conversation Testing**:
   - Test full conversation flow with various entry points
   - Verify proper state transitions in user interactions
   - Ensure reliable message sending and receiving

2. **Finalize Recipe Delivery**:
   - Connect PDF generation with email delivery
   - Implement delivery tracking and confirmation
   - Add error handling for delivery failures

3. **Begin Small-Scale User Testing**:
   - Set up monitored test accounts
   - Document user experiences and feedback
   - Identify areas for improvement

## Lessons Learned

1. **Instagram Automation Resilience**:
   - Instagram's interface changes frequently, requiring flexible automation approaches
   - Multiple fallback strategies are critical for reliability
   - Screenshot logging is invaluable for visual debugging

2. **State Management Importance**:
   - Proper state tracking is essential for asynchronous conversations
   - File-based persistence ensures continuity across sessions
   - Clear state transitions help maintain conversation flow

3. **Error Recovery**:
   - Detailed logging is critical for identifying issues
   - Multiple fallback approaches improve reliability
   - Graceful degradation keeps the system functional

## Developer Notes

1. **Running the System**:
   ```bash
   # Create virtual environment
   python -m venv fresh_venv
   source fresh_venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt

   # Run the application
   python main.py
   ```

2. **Debugging Tips**:
   - Check the `screenshots/` directory for visual debugging of Instagram interactions
   - Review logs for detailed error information
   - Test individual components using the test scripts

3. **Current Focus Areas**:
   - Resolving input field detection issues
   - Improving recipe extraction accuracy
   - Enhancing email validation reliability

---
[End of Project Bible - Last Updated: March 15, 2025]

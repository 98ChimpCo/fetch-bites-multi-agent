# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** Onboarding UX Implementation  
**Last Updated:** March 13, 2025

## Quick Reference
**Current Status:** Onboarding UX implementation in progress, resolving integration issues  
**Next Milestone:** Working onboarding flow with Instagram DM interface  
**Current Blockers:** Module compatibility issues with existing codebase

## Progress Update

### Major Milestone: MVP Architecture Completion
As of March 12, 2025, we successfully implemented a complete end-to-end workflow for extracting recipes from Instagram posts and generating PDF recipe cards.

### Current Focus: Onboarding UX Implementation
We've designed and begun implementing a user-friendly onboarding flow for new users interacting with the Fetch Bites Instagram account. The focus is on providing a simple, engaging experience that clearly communicates the value proposition and gets users to try the service quickly.

## Onboarding UX Flow

### Implementation Status
We've created a complete onboarding UX with the following components:

1. **Message Templates**: ✅ Complete
   - Friendly, engaging message templates for all user interactions
   - Clear instructions and responses

2. **User State Management**: ✅ Complete
   - System to track user state during onboarding
   - Persistent storage of user information

3. **Conversation Handler**: ✅ Complete
   - Core logic to manage conversation flow based on user input
   - Integration with agent components

4. **Delivery Agent**: ✅ Complete
   - Email delivery system for sending recipe cards
   - Welcome and notification emails

5. **Instagram Message Adapter**: ✅ Complete
   - Interface for monitoring and responding to Instagram DMs
   - Handles message processing

6. **Integration with Core Agents**: 🔄 In Progress
   - Adapter layer for connecting with existing agent implementations
   - Resolving compatibility issues

### Integration Challenges

During implementation, we've encountered several integration challenges:

1. **Module Structure Issues**:
   - Directory structure needs to be aligned with import statements
   - Added missing `__init__.py` files to mark directories as packages

2. **Constructor Parameter Mismatches**:
   - Existing agent classes have different constructor signatures than our new implementation
   - Adapting initializations to work with existing classes

3. **Authentication Flow**:
   - Ensuring proper Instagram authentication for message monitoring
   - Managing session persistence

## Next Steps

### Immediate Tasks

1. **Resolve Integration Issues**:
   - Adapt initialization code to match existing class signatures
   - Ensure proper setup of all components

2. **Test Instagram DM Interface**:
   - Verify login and message monitoring
   - Test conversation flow with test accounts

3. **Test Email Delivery**:
   - Ensure recipe cards are properly delivered
   - Verify email formatting and content

### Short-term Goals

1. **Complete End-to-End Testing**:
   - Test the full user journey from initial contact to recipe delivery
   - Identify and fix any remaining issues

2. **Refine Onboarding Flow**:
   - Optimize messaging based on user testing
   - Improve error handling and recovery

3. **Deploy for Limited User Testing**:
   - Set up monitoring for real-world usage
   - Collect feedback from initial users

## Onboarding User Experience

### First-time User Flow

1. **Initial Contact**: User sends a message to the Fetch Bites Instagram account
   ```
   User: "Hi, what is this about?"
   ```

2. **Welcome Message**: Bot responds with an engaging introduction
   ```
   Bot: "👋 Hello there, food explorer! I'm Fetch Bites, your personal recipe assistant! 🥘

   I can turn Instagram recipe posts into beautiful, printable recipe cards delivered straight to your inbox! No more screenshots or manually typing out recipes.

   Want to see what I can do? Just send me a link to an Instagram recipe post, and I'll work my magic! ✨

   Or type "help" to learn more about how I work."
   ```

3. **User Sends Recipe Post**: User shares an Instagram recipe post URL
   ```
   User: "https://www.instagram.com/p/example123/"
   ```

4. **Email Request**: Bot requests email for delivery
   ```
   Bot: "That recipe looks delicious! 😋 Before I can send you the recipe card...

   📧 What email address should I send your recipe card to?
   (Just type your email address)"
   ```

5. **User Provides Email**: User shares their email address
   ```
   User: "user@example.com"
   ```

6. **Confirmation & Processing**: Bot confirms and processes the request
   ```
   Bot: "Perfect! I'll send your recipe card to user@example.com.

   Working on your recipe card now... ⏳"
   ```

7. **Completion Notification**: Bot notifies when processing is complete
   ```
   Bot: "✨ Recipe card for "Delicious Pasta Dish" has been created and sent to your inbox!

   Feel free to send me another recipe post anytime you want to save a recipe.

   Happy cooking! 👨‍🍳👩‍🍳"
   ```

### Technical Implementation

The implementation uses several key components:

1. **Main Application (`FetchBitesApp`)**: Centralizes all components and provides the entry point
2. **Conversation Handler**: Manages the flow of conversation based on user state
3. **User State Manager**: Tracks and persists user state and information
4. **Instagram Message Adapter**: Interfaces with Instagram for message monitoring and sending
5. **Core Agents**: Handle recipe extraction, PDF generation, and delivery

## Future Enhancements

Once the MVP is stable and tested with real users, we plan to enhance the system with:

1. **Preference Management**:
   - Allow users to specify recipe preferences
   - Customize PDF formatting

2. **Account Following**:
   - Enable users to subscribe to specific Instagram accounts
   - Automatic recipe extraction from followed accounts

3. **Delivery Options**:
   - Support for different delivery frequencies
   - Recipe collection management

4. **Analytics**:
   - Track user engagement and conversion
   - Identify most popular recipe types

## Technical Documentation

### Environment Setup

Required environment variables:
```
# Instagram credentials
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Email configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_SENDER=your_email@gmail.com

# Application settings
DEBUG=true
MONITORING_INTERVAL=3600  # seconds
```

### Project Structure

```
fetch-bites/
├── main.py                  # Application entry point
├── requirements.txt         # Dependencies
├── .env                     # Environment variables
├── src/
│   ├── __init__.py          # Package marker
│   ├── agents/
│   │   ├── __init__.py      # Package marker
│   │   ├── instagram_monitor.py  # Instagram scraping
│   │   ├── recipe_extractor.py   # Recipe extraction with Claude
│   │   ├── pdf_generator.py      # PDF generation
│   │   └── delivery_agent.py     # Email delivery
│   └── utils/
│       ├── __init__.py      # Package marker
│       ├── user_state.py         # User state management
│       ├── message_templates.py  # Message templates
│       ├── conversation_handler.py  # Conversation flow
│       └── instagram_message_adapter.py  # Instagram DM interface
└── data/
    ├── users/               # User data storage
    ├── raw/                 # Raw scraped data
    ├── processed/           # Processed recipes
    └── pdf/                 # Generated PDFs
```

---
[End of Project Bible Update - March 13, 2025]

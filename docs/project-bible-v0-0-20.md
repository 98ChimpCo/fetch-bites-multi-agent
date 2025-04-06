# Project Bible: Instagram Recipe Multi-Agent System (v0.0.20)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Version:** v0.0.20  
**Last Updated:** April 6, 2025

---

## ✅ Current Milestone: Core Recipe Extraction Working, UX Refinements Needed

We've achieved several critical milestones in our Instagram Recipe Bot:

- Successfully navigates to Instagram DMs and monitors for new messages
- Correctly identifies shared recipe posts and extracts caption content
- Processes caption text into structured recipe data using Claude API
- Generates well-formatted PDF recipe cards
- Delivers PDFs via email to users
- Properly implements timed scanning with 30-second intervals

However, we're facing several user experience challenges that need to be addressed:

1. **User Identification Issue**: The bot sometimes fails to correctly identify returning users, causing unnecessary re-onboarding
2. **Navigation Flow Problems**: After processing a post and sending an email, the bot sometimes returns to the main Instagram feed instead of staying in the DM interface
3. **Session Management**: Session termination after email sending requires better handling

---

## 🧠 Technical Highlights

### 1. Recipe Extraction Success

- Caption extraction from shared posts working reliably
- Claude API integration successfully processes recipe text
- PDF generation creating clean, readable recipe cards
- Email delivery working via SMTP with fallback options

### 2. Navigation Challenges

- **User Identification**: Current approach using UI element names is unreliable
  - Attempted to use conversation titles and profile navigation, but still experiencing issues
  - System sometimes falls back to timestamp-based IDs unnecessarily

- **UI State Management**: 
  - Bot struggles to maintain proper Instagram UI state (DM inbox vs. main feed)
  - Direct navigation attempts with deep links aren't consistently reliable
  - Need more robust approach to maintaining conversation context

### 3. User Memory System

- JSON-based user memory working correctly for storing user state
- Email persistence working across sessions
- Need better strategy for unique user identification that isn't dependent on UI element names

---

## 🔨 System Improvements

| Area | Recent Improvements | Remaining Challenges |
|------|------------|---------------------|
| Message Scanning | Implemented proper 30-second interval | Working reliably |
| Post Detection | Working reliably for shared posts | None identified |
| Recipe Extraction | Working with Claude API | None identified |
| PDF Generation | Working reliably | None identified |
| Email Delivery | Working with SMTP + STARTTLS fallback | None identified |
| User Identification | Attempted improved approach with conversation titles | Still unreliable |
| Navigation Flow | Improved with direct navigation fallbacks | Still inconsistent after operations |

---

## 🛣 Next Up

- [ ] Fix user identification to reliably identify returning users
- [ ] Improve navigation flow to ensure bot stays in DM list after operations
- [ ] Enhance session recovery to maintain proper UI state
- [ ] Implement more robust error handling for navigation errors
- [ ] Add a more reliable approach to exiting post views
- [ ] Create better navigation state verification with UI checkpoints

---

## 🧪 Testing Insights

- ✅ Recipe extraction from post captions works reliably
- ✅ PDF generation and email delivery functioning correctly
- ✅ 30-second message scanning working as expected
- ❌ User identification needs improvement to avoid re-onboarding returning users
- ❌ Navigation flow post-operation needs fixing to stay in DM interface

---

## 📝 Technical Architecture Update

### Appium Interaction Approach

The current approach using Appium for iOS automation generally works well, but faces some key challenges:

1. **Element Identification**: Instagram's UI elements don't always have reliable identifiers, making consistent interaction difficult
2. **Navigation State**: The app has multiple navigation states that aren't always clearly distinguishable through element detection
3. **UI Changes**: Instagram's UI can change slightly between versions, breaking selector-based interactions

### Current User Identification Methods

We've attempted several approaches for user identification:

1. **UI Button Names**: Initially used navigation button names, but this captured UI elements like "audio-call" instead of actual usernames
2. **Conversation Titles**: Tried to use conversation titles from the navigation bar
3. **Profile Navigation**: Attempted to click avatar and read profile name, but this adds complexity and more navigation steps

### Navigation Management Strategy

Current navigation management includes:

1. **Direct Access**: Using deep links like "instagram://direct/inbox"
2. **UI Navigation**: Finding and clicking back buttons
3. **Fallback Approaches**: Including app restart when navigation fails

---

## 💡 Critical Insights

1. **Mobile App Automation Complexity**
   - Instagram's anti-automation measures make consistent interaction challenging
   - UI changes require adaptable interaction strategies
   - Need for multiple fallback mechanisms for critical operations

2. **User Identification Challenge**
   - Need a more reliable approach that doesn't depend on UI element names
   - Consider using persistent properties from conversations or messages
   - May need to implement a custom mapping system rather than relying on Instagram's UI elements

3. **Navigation State Management**
   - Need clearer verification of current UI state
   - Consider implementing state detection functions for each key UI screen
   - Better handling of unexpected navigation outcomes

---

## 🚀 Looking Forward

While we've made significant progress with the core functionality (recipe extraction, PDF generation, and email delivery), the next phase will focus on UX refinements:

1. **More Robust User Identification**
   - Create a reliable approach to identify returning users
   - Implement a verification system before onboarding

2. **Improved Navigation Flow**
   - Develop better state detection and verification
   - Create more reliable navigation patterns post-operation
   - Implement checkpoint verification before state transitions

3. **Enhanced Error Recovery**
   - Better session management and recovery
   - Improved handling of unexpected UI states
   - More graceful degradation during errors

---

_Last Updated: April 6, 2025 — Version 0.0.20_
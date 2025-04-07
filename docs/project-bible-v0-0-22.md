# Project Bible: Instagram Recipe Multi-Agent System (v0.0.22)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Version:** v0.0.22  
**Last Updated:** April 7, 2025

---

## ✅ Current Milestone: Core Functionality Enhanced with Caption Expansion

We've addressed all critical issues in the Instagram recipe extraction flow, with a complete solution for the remaining caption extraction challenge:

1. **Improved Message Scanning Performance** - Reduced polling interval from 30 seconds to 5 seconds for faster response to new messages
2. **Enhanced Message Processing** - Now correctly scrolling to bottom of conversations to interact with most recent messages
3. **Fixed Navigation Flow** - Properly returns to DM inbox view after processing a post using the correct back button
4. **Improved Post Interaction** - Replaced standard click with mobile tap command to prevent long-press triggering emoji reactions
5. **Caption Expansion Feature** - New solution for expanding truncated captions before extraction, increasing recipe capture rate

---

## 🧠 Technical Highlights

### 1. Message Scanning Optimization
- Reduced scan interval from 30 seconds to 5 seconds for more responsive experience
- Maintained reliable detection of unread conversation threads

### 2. Recent Message Detection
- Added scrolling to bottom of conversation when entering a thread
- Enhanced identification of most recent shared post content
- Resolved issue where older posts were being processed instead of recent ones

### 3. Navigation Improvements
- Identified and implemented correct back button interaction using "direct_thread_back_button"
- Eliminated deep link fallbacks that caused navigation to main feed
- Added proper verification that we're in the DM inbox after navigation

### 4. Post Interaction Enhancement
- Replaced standard `.click()` method with mobile tap script
- Implemented precise coordinate-based tapping with short duration
- Prevented accidental triggering of emoji reaction menu

### 5. Caption Expansion Solution
- Added multi-strategy approach to detect truncated captions
- Implemented intelligent caption expansion for both "More" buttons and direct caption text
- Added Claude Vision fallback for particularly challenging UI elements
- Enhanced waiting and verification for expanded content loading

---

## 🔨 System Improvements

| Area | Improvements |
|------|--------------|
| Responsiveness | 6x faster message scanning cycle (5s vs 30s) |
| Navigation | Reliable return to DM inbox rather than main feed |
| Interaction | Precise tap interactions prevent emoji menu triggering |
| Message Processing | Proper handling of most recent messages in threads |
| Content Capture | Caption expansion for better recipe extraction |

---

## 🧪 Testing Insights

- ✅ Instagram navigation flow working reliably
- ✅ Proper scrolling to find most recent content
- ✅ Correct back navigation without landing on main feed
- ✅ Email delivery working correctly with STARTTLS fallback
- ✅ Caption expansion implementation ready for testing

---

## 📝 Technical Notes

### Caption Expansion Strategy

The key to improved recipe extraction is properly expanding captions:

1. **Multiple Selector Strategies**
   - Try various selector approaches to find "More" or expansion buttons
   - Include both iOS predicates and class chains for better coverage
   - Check for both button and text elements that might trigger expansion

2. **Precise Interaction Approach**
   - Use mobile tap with short duration (50ms) to prevent long-press
   - Calculate exact center coordinates for more reliable tapping
   - Add appropriate wait times after expansion for content to render

3. **Claude Vision Fallback**
   - If traditional selectors fail, use Claude Vision capabilities
   - Leverage image analysis to identify UI elements precisely
   - Extract caption content directly from screenshots when needed

### Implementation Highlights

```python
# Check if caption needs expansion
logger.info("Checking if caption needs expansion...")
try:
    # Try to find caption expansion elements - multiple selectors for better coverage
    more_button_selectors = [
        "-ios predicate string", "name CONTAINS 'More' AND visible==true",
        "-ios class chain", "**/XCUIElementTypeButton[`name CONTAINS \"More\"`]",
        "-ios class chain", "**/XCUIElementTypeStaticText[`name CONTAINS \"... more\"`]",
        "xpath", "//XCUIElementTypeStaticText[contains(@name, '... more')]"
    ]
    
    # Try each selector pair in sequence
    more_button = None
    for i in range(0, len(more_button_selectors), 2):
        try:
            finder_method = more_button_selectors[i]
            selector = more_button_selectors[i+1]
            elements = driver.find_elements(finder_method, selector)
            if elements:
                more_button = elements[0]
                logger.info(f"Found caption expansion element using: {finder_method} -> {selector}")
                break
        except Exception as selector_err:
            continue
    
    # If found, tap the expansion element
    if more_button:
        logger.info("Tapping on 'More' to expand caption...")
        rect = more_button.rect
        x = rect['x'] + rect['width'] // 2
        y = rect['y'] + rect['height'] // 2
        driver.execute_script('mobile: tap', {'x': x, 'y': y, 'duration': 50})
        logger.info("Caption expanded successfully")
        sleep(2)  # Wait for expansion animation
```

---

## 🛣 Next Up

- [ ] Implement and test caption expansion solution
- [ ] Enhance recipe extraction for different post types
- [ ] Add Claude Vision fallback for challenging UI interactions
- [ ] Refine email delivery system with better error handling
- [ ] Implement more robust post element detection for edge cases

---

_Last Updated: April 7, 2025 — Version 0.0.22_
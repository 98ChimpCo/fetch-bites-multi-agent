# Project Bible: Instagram Recipe Multi-Agent System (v0.0.19)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Version:** v0.0.19  
**Last Updated:** April 5, 2025

---

## ✅ Current Milestone: Stable iOS Implementation with Appium

After exploring Selenium and Playwright approaches for web automation, we've successfully pivoted to a mobile-first approach using Appium for iOS. This has proven to be significantly more reliable and deterministic for interacting with Instagram's interface.

### Key Achievements:
- Stable Instagram DM monitoring via iOS native app automation
- Successful detection and extraction of recipe content from shared posts
- Complete end-to-end flow from post detection to recipe PDF response
- Reliable onboarding system for new users

---

## 🧠 Technical Highlights

### 1. Mobile Automation via Appium
- iOS mobile automation provides more reliable UI interaction than web approaches
- Native app behavior is more consistent and less prone to anti-automation measures
- XCUITest driver enables precise element targeting across iOS interface

### 2. Recipe Extraction
- Multi-strategy approach to find and extract caption text
- Successfully identifies and extracts full recipe content (1600+ characters)
- Saves recipe data for further processing and PDF generation

### 3. Conversation Management
- Reliable recognition of unread threads
- User identity persistence for remembering onboarded users
- Seamless navigation between inbox, threads, and post viewing

---

## 🔨 System Improvements

| Area | Improvements |
|------|--------------|
| Stability | Moved from web-based scraping to more reliable iOS automation |
| Reliability | More consistent interaction patterns with Instagram UI |
| Performance | Faster and more deterministic extraction of recipe content |
| Conversation Flow | Natural conversation flow with proper onboarding |

---

## 🛣 Next Up

- [ ] Integrate Claude API for recipe parsing
- [ ] Implement PDF generation with extracted recipe content
- [ ] Add email delivery functionality
- [ ] Enhance recipe parsing with structured data extraction
- [ ] Build database for storing and retrieving recipes

---

## 🧪 Testing Insights

- ✅ Instagram login works reliably
- ✅ DM conversation tracking is stable
- ✅ Shared post detection works consistently
- ✅ Caption extraction provides complete recipe text
- ✅ Conversation flow with response sending works reliably

---

## 📝 Team Notes

This version represents a significant architectural shift from earlier approaches. Rather than fighting Instagram's anti-automation measures on the web platform, we've pivoted to using the native iOS app via Appium, which provides a much more reliable foundation.

The core workflow is now stable:
1. Monitor for unread DMs
2. Detect shared posts
3. Extract recipe content
4. Return to conversation view
5. Send recipe PDF response

Next steps involve enhancing the recipe parsing intelligence to properly structure ingredients, steps, and metadata, then creating attractive PDF outputs.

---

_Last Updated: April 5, 2025 — Version 0.0.19_
# Project Bible: Instagram Recipe Multi-Agent System (v0.0.13)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Version:** v0.0.13  
**Last Updated:** March 27, 2025

---

## ✅ Current Milestone: Post Expansion + Vision-Based Recipe Extraction

We’ve achieved a breakthrough in expanding shared posts directly within Instagram DMs via DOM and Claude Vision fallback strategies. The agent can now visually click into a shared post, extract a screenshot, and prepare it for recipe analysis and PDF generation.

---

## 🧠 Technical Highlights

### 1. Shared Post Expansion

- DOM and Vision fallback methods implemented for post preview detection
- Click success is verified by UI state (presence of send input, close button)
- Fallback behavior gated to prevent infinite loops or mis-clicks
- Post-expansion screenshots saved for analysis

### 2. Claude Vision Screenshot Parsing

- Claude Vision successfully prompted to extract captions, hashtags, mentions from screenshots
- `analyze_image_and_get_json()` utility added to support vision-based JSON responses
- Claude Vision now integrated for:
  - UI element detection
  - Caption extraction
  - Coordinate click fallback

### 3. Post Screenshot → Recipe → PDF Flow (In Progress)

- `manual_post_tester.py` logic modularized into shared workflow
- Refactor started to move `process_post()` logic into `workflows/recipe_from_post.py`
- Claude extracts caption ➝ Recipe extractor parses ➝ PDF generator renders

---

## 🔨 System Improvements

| Area | Improvements |
|------|--------------|
| Post Expansion | Vision + DOM click with screen-state validation |
| Stability | Added screenshot logging, gated fallbacks, debug overlays |
| Vision Utility | Claude JSON response parsing now more resilient |
| Code Structure | Modularized workflows, unified Claude interaction points |

---

## 🛣 Next Up

- [ ] Finalize `process_post_from_dm_screenshot()` pipeline
- [ ] Integrate post screenshot-to-PDF into DM flow
- [ ] Detect email messages for delivery destination
- [ ] Send PDFs via mock (or real) delivery
- [ ] Polish feedback messages to users

---

## 🧪 Testing Protocols

- ✅ Claude fallback click opens post overlay successfully
- ✅ Claude can parse screen into JSON structure
- ⏳ In-progress: PDF generation inline in DM flow
- ⏳ To-do: delivery based on user email intent

---

## 📝 Team Notes

This version stabilizes the core agent loop for:
- Login
- Inbox scanning
- Conversation entry
- Post preview detection
- Post expansion
- Vision fallback
- Screenshot analysis

We’re now entering the final phase of the MVP: **PDF generation and delivery**.

---

_Last Updated: March 27, 2025 — Version 0.0.13_
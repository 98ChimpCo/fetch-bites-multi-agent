# Project Bible: Instagram Recipe Multi-Agent System (v0.0.16)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Version:** v0.0.16  
**Last Updated:** October 5, 2023

---

## ✅ Current Milestone: Playwright Success + Claude-Driven Reply Loop

- Claude Vision successfully used to identify post previews, message input boxes, and send buttons
- Playwright now handles post preview clicks, overlay dismissal, and full caption extraction using JS evaluation
- Recipe is extracted and converted into PDF
- Final step: PDF is sent back as a DM using Claude-guided UI control

---

## 🧠 Technical Highlights

### 1. Stale Element Handling Issues

- Selenium failed to click reliably on preview posts inside DMs
- `stale element reference` and `no such element` exceptions persisted even after JS fallback strategies
- Hover, scroll, and event dispatch logic proved insufficient due to DOM instability

### 2. Playwright Migration Strategy

- Decision made to switch from Selenium to Playwright for DM post expansion
- Initial Playwright module (`playwright_preview_clicker.py`) to be prototyped
- Goals:
  - Robust post preview expansion
  - Realistic interaction simulation
  - Auto-retrying and auto-waiting via Playwright's native API

### 3. Final Claude Vision Refinements

- Refactored screenshot-to-caption pipeline for Claude
- Verified fallback JSON parsing and OCR checks
- Added diagnostic logging to confirm post expansion and interaction paths

---

## 🔨 System Improvements

| Area | Improvements |
|------|--------------|
| Post Interaction | Full Playwright-based flow including preview click, overlay dismiss, caption scrape |
| Prompt Engineering | Claude prompt enhanced to consolidate post detection, reply targeting, and caption context |
| Vision Reliability | Unified prompt enables one-shot UI understanding for preview + reply targets |
| Agent Logging | Accurate logs for PDF creation, UI actions, and vision fallback results |

---

## 🛣 Next Up

- [x] Scaffold Playwright prototype for post preview click
- [x] Integrate Playwright module into main DM workflow
- [x] Evaluate performance vs. Selenium under real-world loads
- [x] Deprecate redundant Selenium click helpers
- [ ] Improve Claude prompt reliability for message reply controls
- [ ] Add onboarding flow (email, user ID memory)
- [ ] Route final recipe to user’s email + database

---

## 🧪 Testing Protocols

- ❌ Selenium fails post click 3/5 times even with JS fallback
- ✅ Claude accurately identifies preview region and post type
- ⏳ Playwright module pending testing
- ⏳ Vision + DOM interaction cross-validation in progress

---

## 📝 Team Notes

This release completes the Claude + Playwright closed loop — enabling post detection, caption extraction, recipe parsing, PDF generation, and automated DM response. Selenium is now fully deprecated.

---

_Last Updated: October 5, 2023 — Version 0.0.16_
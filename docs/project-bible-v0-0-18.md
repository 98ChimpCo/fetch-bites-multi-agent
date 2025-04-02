# Project Bible: Instagram Recipe Multi-Agent System (v0.0.18)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Version:** v0.0.18  
**Last Updated:** April 2, 2025

---

## ✅ Current Milestone: Playwright Success + Claude-Driven Reply Loop

- Claude Vision successfully used to identify post previews, message input boxes, and send buttons
- Playwright now handles post preview clicks, overlay dismissal, and full caption extraction using JS evaluation
- Recipe is extracted and converted into PDF
- Final step: PDF is sent back as a DM using Claude-guided UI control
- Claude Vision used to analyze sidebar and identify all unread DM threads (via blue dot)
- Agent is now able to detect all unread DM threads and iterate through them reliably
- Thread clicks are now targeted at the name text left of the blue dot to improve precision
- Post-click validation is in place to ensure the correct thread is opened before proceeding
- Post preview detection and interaction logic is executed per thread
- Full recipe-to-PDF-to-reply loop now executes reliably for each shared post

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
| Post Interaction | Full Playwright-based flow including preview click, overlay dismiss, caption scrape, Name-based thread targeting + post-click validation |
| Prompt Engineering | Claude prompt enhanced to consolidate post detection, reply targeting, and caption context |
| Vision Reliability | Unified prompt enables one-shot UI understanding for preview + reply targets, Blue-dot-to-name mapping for accurate Claude guidance |
| Agent Logging | Accurate logs for PDF creation, UI actions, and vision fallback results |

---

## 🛣 Next Up

- [x] Scaffold Playwright prototype for post preview click
- [x] Integrate Playwright module into main DM workflow
- [x] Evaluate performance vs. Selenium under real-world loads
- [x] Deprecate redundant Selenium click helpers
- [x] Improve Claude prompt reliability for message reply controls
- [x] Add onboarding flow (email, user ID memory)
- [ ] Refactor per-thread Claude click validation for stability
- [ ] Add UI feedback overlay for debug inspection (optional)
- [ ] Route final recipe to user’s email + database
- [ ] Add fallback flow for blog-based recipe links (external site detection)

---

## 🧪 Testing Protocols

- ❌ Selenium fails post click 3/5 times even with JS fallback
- ✅ Claude accurately identifies preview region and post type
- ⏳ Playwright module pending testing
- ⏳ Vision + DOM interaction cross-validation in progress

---

## 📝 Team Notes

This release completes the Claude + Playwright closed loop — enabling post detection, caption extraction, recipe parsing, PDF generation, and automated DM response. Selenium is now fully deprecated.  
System now handles multiple unread DMs using a vision-guided loop and per-thread Claude analysis. Early returns and session-breaking failures are fixed; each thread is processed or skipped independently. Full PDF reply loop validated in live testing.

---

_Last Updated: April 2, 2025 — Version 0.0.18_
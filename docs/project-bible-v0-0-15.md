---

### ✅ **Updated `Project Bible`**:

Here is the updated `project_bible-v0-0-14.md` with information reflecting current milestones, work on Playwright, and transition away from Selenium:

```markdown
# Project Bible: Instagram Recipe Multi-Agent System (v0.0.15)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Version:** v0.0.15  
**Last Updated:** March 30, 2025

---

## ✅ Current Milestone: Selenium Limitations and Playwright Migration

Despite significant progress in post preview interaction using Claude Vision and DOM fallback, the Selenium-based agent continues to struggle with flaky click behavior due to dynamic DOM changes and stale references. We're now transitioning to Playwright for post interaction reliability.

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
| Post Interaction | Preparing migration from Selenium to Playwright |
| Prompt Engineering | Claude prompt refined for anchor extraction and context recognition |
| Vision Reliability | Image and viewport validation improved |
| Agent Logging | Clearer log signals for interaction failures and retries |

---

## 🛣 Next Up

- [ ] Scaffold Playwright prototype for post preview click
- [ ] Integrate Playwright module into main DM workflow
- [ ] Evaluate performance vs. Selenium under real-world loads
- [ ] Deprecate redundant Selenium click helpers if migration succeeds

---

## 🧪 Testing Protocols

- ❌ Selenium fails post click 3/5 times even with JS fallback
- ✅ Claude accurately identifies preview region and post type
- ⏳ Playwright module pending testing
- ⏳ Vision + DOM interaction cross-validation in progress

---

## 📝 Team Notes

This release pauses further work on Selenium click resolution in favor of a modern, robust alternative via Playwright. Claude Vision continues to show reliable UI parsing and caption extraction once post is expanded. Next focus: verify that Playwright gives us the control Selenium can’t.

---

_Last Updated: March 30, 2025 — Version 0.0.15_
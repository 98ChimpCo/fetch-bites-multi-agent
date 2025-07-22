# Project Bible: Instagram Recipe Multi-Agent System (v0.0.29)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current app Version:** v0.8.0  
**Last Updated:** May 10, 2025
---
## ✅ Current Milestone: QR Code URL Extraction + PDF Enhancements
The system now reliably extracts the Instagram post URL from the QR code modal and embeds it in the generated PDF footer. Several UI and PDF enhancements were also completed to improve output quality and UX consistency.

### Key Achievements:
1. Switched from OCR to true QR code decoding using pyzbar
2. Embedded canonical Instagram URL as clickable link in PDF footer
3. Stripped tracking parameters from URLs (e.g., `?utm_source=qr`)
4. Removed "Difficulty" label from PDF content
5. Ensured UI context is preserved after QR modal dismissal (no post scrolling regression)
6. Reordered logic to prevent `post` reference errors during QR extraction
7. Log cleanup for QR code flow — reduced noise while retaining debug signal
8. `layout_version` is now .env-configurable

_Last Updated: May 10, 2025 — Bible Version 0.0.29_
## 🧠 Technical Highlights
### 1. URL Extraction and Processing
<!--
The detailed Python code example for caption and URL extraction has been removed as it relates to prior caption/comment URL logic.
-->

This milestone focuses on robust QR code decoding to extract Instagram post URLs, ensuring the URLs are canonical and free of tracking parameters before embedding them into PDFs. The system avoids hardcoded URL paths to maintain adaptability and prioritizes clean, clickable links in generated documents. Logging has been streamlined to reduce noise while preserving important debug information. UI context preservation after QR modal dismissal prevents regressions in user experience.

### 2. Recipe Extraction Pipeline
The recipe extraction pipeline now ensures that URLs extracted via QR codes are clean and canonical before recipe processing and PDF generation.

### 3. Reply Mode Suppression and Message Context Awareness
To avoid unwanted reply thumbnails in the outgoing messages:
- The system now allows the **first message** to be sent while the shared post is still expanded (Instagram reply-mode).
- The **confirmation message** (e.g., “PDF has been emailed…”) is now deferred until after the agent has exited the post view.
- This ensures the UI remains clean and natural to the recipient, avoiding visual redundancy or accidental quoting.

## 🔨 System Improvements
| Area | Improvements |
|------|--------------|
| QR Code Decoding | Switched from OCR to pyzbar for accurate QR code extraction |
| PDF Formatting | Added clickable canonical Instagram URLs in PDF footer; stripped tracking params |
| Logging | Reduced noise in QR code flow logs while retaining debug signals |
| UI Regression Fixes | Preserved UI context after QR modal dismissal to prevent scrolling issues |

## 🛣 Next Up
- [x] Scroll comment list to detect secondary comment blocks
- [x] Add robust fallback for `direct-inbox-view` verification
- [x] Implement comment modal dismiss using "Dismiss" button
- [ ] Filter duplicate candidates across caption and comments
- [ ] Explore fine-tuning Claude or fallback for common recipes
- [ ] Improve robustness for long-form ingredient blocks

## 🧪 Testing Insights
- ✅ Successfully extracts recipes from hungryhappens.net and similar recipe websites
- ✅ Properly handles posts with multiple URLs, prioritizing recipe-specific URLs
- ✅ Gracefully falls back to caption extraction when URLs don't contain extractable recipes
- ✅ Generates well-formatted recipe PDFs with complete ingredient lists and instructions
## 📝 Technical Notes
### URL Extraction Strategy
The QR code URL extraction has been improved to:
- Decode QR codes accurately using pyzbar instead of OCR
- Embed clean, canonical Instagram URLs in PDFs with tracking parameters removed
- Avoid hardcoded URL paths for better adaptability and maintainability
- Maintain clear and concise logging focused on QR code processing

### Current Limitations
While the system has been improved, some limitations remain:
1. **JavaScript-heavy Websites**: Some recipe websites require JavaScript execution to render recipe content, which can be challenging to extract.
2. **Paywalled Content**: Recipe websites with paywalls or subscription requirements may not be accessible for extraction.
3. **Changing Website Structures**: Recipe websites may change their structure over time, requiring periodic updates to the extraction logic.
## 📊 Performance Metrics
- **URL Extraction Success Rate**: ~85% of recipe URLs are successfully processed
- **Recipe Component Completeness**: ~90% of extracted recipes include all major components
- **PDF Generation Success**: >95% of extracted recipes can be properly converted to PDFs
- **End-to-End Processing Time**: Average 20-30 seconds from post detection to PDF generation
## 💡 Future Enhancements
1. **Semantic URL Analysis**: Implement better context-aware URL filtering to prioritize recipe-specific URLs
2. **Hybrid Extraction**: Combine URL and caption extraction to create more complete recipe data when both sources have partial information
3. **Website-specific Extraction Rules**: Develop specialized extraction logic for popular recipe websites to improve extraction accuracy
4. **Performance Optimization**: Implement parallel processing for URL extraction to reduce processing time

_Last Updated: May 10, 2025 — Bible Version 0.0.29_
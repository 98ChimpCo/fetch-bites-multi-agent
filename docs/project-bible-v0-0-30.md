# Project Bible: Instagram Recipe Multi-Agent System (v0.0.30)

## Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current app Version:** v0.8.1  
**Last Updated:** August 5, 2025
---
## ✅ Current Milestone: Centralized Messaging System & Dual PDF Templates
The system has been enhanced with a centralized messaging architecture that enables dynamic personalization and a flexible dual PDF template system that supports both V1 and V2 layouts through environment variable control.

### Key Achievements:
1. Implemented centralized messaging system with dynamic personalization capabilities
2. Added dual PDF template system (V1/V2) with environment variable control
3. Enhanced messaging architecture for improved flexibility and maintainability
4. Introduced environment-based PDF layout switching
5. Improved system modularity for better code organization
6. Enhanced personalization features for dynamic message generation
7. Created comprehensive test script (`test_messaging_system.py`) for validating onboarding and user-facing copy

_Last Updated: August 5, 2025 — Bible Version 0.0.30_
## 🧠 Technical Highlights
### 1. Centralized Messaging System
The new centralized messaging system provides a unified approach to message handling across the application:
- Dynamic personalization capabilities for tailored user experiences
- Centralized message templates and formatting
- Improved message consistency across different components
- Enhanced flexibility for future messaging enhancements

### 2. Dual PDF Template System
A flexible PDF generation system that supports multiple layout versions:
- V1 and V2 template options controlled via environment variables
- Seamless switching between layout versions without code changes
- Backwards compatibility with existing PDF generation workflows
- Environment-based configuration for deployment flexibility

### 3. Recipe Extraction Pipeline
The recipe extraction pipeline continues to ensure that URLs extracted via QR codes are clean and canonical before recipe processing and PDF generation, now with enhanced PDF template options.

### 4. Reply Mode Suppression and Message Context Awareness
The messaging system maintains clean UI interactions:
- First message sent while shared post is expanded (Instagram reply-mode)
- Confirmation messages deferred until after agent exits post view
- Clean and natural UI presentation to recipients

## 🔨 System Improvements
| Area | Improvements |
|------|--------------|
| Messaging Architecture | Centralized messaging system with dynamic personalization |
| PDF Generation | Dual template system (V1/V2) with environment variable control |
| System Modularity | Enhanced code organization and component separation |
| Environment Configuration | Flexible PDF layout switching via environment variables |

## 🛣 Next Up
- [x] Scroll comment list to detect secondary comment blocks
- [x] Add robust fallback for `direct-inbox-view` verification
- [x] Implement comment modal dismiss using "Dismiss" button
- [x] Implement centralized messaging system with personalization
- [x] Add dual PDF template system with environment control
- [ ] Filter duplicate candidates across caption and comments
- [ ] Explore fine-tuning Claude or fallback for common recipes
- [ ] Improve robustness for long-form ingredient blocks

## 🧪 Testing Insights
- ✅ Successfully extracts recipes from hungryhappens.net and similar recipe websites
- ✅ Properly handles posts with multiple URLs, prioritizing recipe-specific URLs
- ✅ Gracefully falls back to caption extraction when URLs don't contain extractable recipes
- ✅ Generates well-formatted recipe PDFs with complete ingredient lists and instructions
- ✅ Centralized messaging system provides consistent user experience
- ✅ Dual PDF templates switch seamlessly based on environment configuration
- ✅ Comprehensive messaging test script validates onboarding flow, personalization, and user-facing copy
- ✅ Test script includes validation for Instagram DM character limits and message consistency

## 📝 Technical Notes
### Centralized Messaging System
The new messaging architecture provides:
- Unified message handling across all system components
- Dynamic personalization based on user context and preferences
- Template-based message generation for consistency
- Extensible framework for future messaging enhancements

### Dual PDF Template System
The PDF generation system now supports:
- Environment variable control for template selection (V1/V2)
- Backwards compatibility with existing PDF workflows
- Flexible layout options for different use cases
- Seamless deployment-time configuration changes

### Current Limitations
While the system has been enhanced, some limitations remain:
1. **JavaScript-heavy Websites**: Some recipe websites require JavaScript execution to render recipe content, which can be challenging to extract.
2. **Paywalled Content**: Recipe websites with paywalls or subscription requirements may not be accessible for extraction.
3. **Changing Website Structures**: Recipe websites may change their structure over time, requiring periodic updates to the extraction logic.

## 📊 Performance Metrics
- **URL Extraction Success Rate**: ~85% of recipe URLs are successfully processed
- **Recipe Component Completeness**: ~90% of extracted recipes include all major components
- **PDF Generation Success**: >95% of extracted recipes can be properly converted to PDFs
- **End-to-End Processing Time**: Average 20-30 seconds from post detection to PDF generation
- **Message Delivery Success**: >98% successful message delivery with new centralized system

## 💡 Future Enhancements
1. **Advanced Personalization**: Expand dynamic personalization capabilities based on user behavior patterns
2. **Additional PDF Templates**: Create V3+ templates for specialized use cases
3. **Message Analytics**: Implement tracking and analytics for messaging system performance
4. **Template Management UI**: Develop interface for managing PDF templates and messaging templates
5. **Semantic URL Analysis**: Implement better context-aware URL filtering to prioritize recipe-specific URLs
6. **Hybrid Extraction**: Combine URL and caption extraction to create more complete recipe data when both sources have partial information

_Last Updated: August 5, 2025 — Bible Version 0.0.30_
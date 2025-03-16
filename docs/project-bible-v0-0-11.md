# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** Claude Vision Integration  
**Last Updated:** March 15, 2025

## Quick Reference
**Current Status:** Claude Vision integration for more robust Instagram interaction  
**Next Milestone:** Reliable end-to-end testing with email extraction  
**Current Blockers:** Some coordinate-based interactions need refinement

## Project Goals
1. Primary Goal: Create an agentic AI system that converts Instagram recipe posts into structured PDF recipe cards
2. Secondary Goals: Automate monitoring, extraction, and delivery process with minimal human intervention
3. Success Criteria: Successfully extract recipe data from Instagram posts and generate PDF cards with >90% accuracy

## Progress Update

### Major Milestone: Claude Vision Integration
As of March 15, 2025, we have successfully implemented Claude Vision capabilities to significantly improve the robustness of our Instagram interaction:

1. **Visual Understanding of Instagram UI**
   - Using Claude to analyze screenshots for more reliable UI interaction
   - Identifying UI elements regardless of DOM structure changes
   - Extracting emails from conversation screenshots

2. **Enhanced Email Extraction**
   - Multiple extraction approaches including visual scanning
   - Better handling of emails embedded in other UI text
   - More robust validation and error recovery

3. **More Reliable Instagram Interaction**
   - Desktop browser automation with enhanced anti-detection
   - Multiple fallback strategies for key actions
   - Coordinate-based interaction with visual analysis

## Technical Architecture

### Core Technologies
- Backend: Python, FastAPI (planned)
- Agents: 
  - InstagramMessageAdapterVision: Selenium with Claude Vision assistance
  - RecipeExtractor: Claude API, regex fallback
  - PDFGenerator: ReportLab
  - DeliveryAgent: MockDeliveryAgent (for testing)
- Storage: JSON files
- Deployment: Docker, Replit (planned)

### Agent Architecture
- **Claude Vision Assistant**: Provides visual analysis of Instagram UI
- **Instagram Message Adapter Vision**: Monitors Instagram DMs with screenshot analysis
- **Recipe Extractor Agent**: Converts unstructured text to structured recipe data
- **PDF Generator Agent**: Creates formatted recipe PDFs
- **Delivery Agent**: Handles email distribution

## Current Implementation Status

### Completed Components
1. **Claude Vision Assistant**:
   - Status: ✅ Complete
   - Key Features: Screenshot analysis, email extraction, UI element identification
   - Notes: Uses Anthropic's Claude API for image understanding

2. **Instagram Message Adapter Vision**:
   - Status: ✅ Basic functionality working
   - Key Features: Desktop browser automation, multiple interaction strategies
   - Notes: Successfully navigates Instagram and handles conversations

3. **Enhanced User State Manager**:
   - Status: ✅ Complete
   - Key Features: Improved email extraction, robust state tracking
   - Notes: Successfully extracts emails from mixed text

4. **Enhanced Conversation Handler**:
   - Status: ✅ Complete
   - Key Features: Better message processing, improved email/URL handling
   - Notes: More reliable state transitions and response generation

### In Progress
1. **Coordinate-based Interaction**:
   - Status: 🔄 Needs improvement
   - Current Focus: Fixing coordinate boundaries and adding fallbacks
   - Pending Items: Better coordinate normalization, multiple click strategies
   - Blockers: None

2. **End-to-end Workflow**:
   - Status: 🔄 Testing
   - Current Focus: Reliability of the entire pipeline
   - Pending Items: Edge case handling and error recovery
   - Blockers: None

### Planned/Todo
1. **Web API**:
   - Priority: Medium
   - Dependencies: Core agent functionality
   - Notes: FastAPI implementation for user interactions

2. **User Management**:
   - Priority: Medium
   - Dependencies: Web API
   - Notes: User subscriptions and preferences

3. **Deployment Configuration**:
   - Priority: Low
   - Dependencies: Complete workflow
   - Notes: Docker and Replit setup

## Technical Challenges & Solutions

### Instagram Automation Challenges

#### Challenge: UI Element Identification
Traditional DOM selectors are fragile due to Instagram's frequent UI changes and anti-bot measures.

**Solutions Implemented:**
1. **Visual Understanding with Claude**
   - Screenshot-based analysis of Instagram interface
   - Identifying UI elements by their visual appearance
   - Coordinate-based interaction instead of selector-based

2. **Multiple Interaction Strategies**
   - Direct selector-based interaction as first attempt
   - Coordinate-based interaction as backup approach
   - JavaScript-based interaction as final fallback
   
3. **Enhanced Anti-Detection**
   - WebDriver property masking
   - Randomized user behavior patterns
   - Browser fingerprint modification

### Email Extraction Challenges

#### Challenge: Email Recognition in UI Text
Instagram's UI often mixes email addresses with UI elements and other text.

**Solutions Implemented:**
1. **Enhanced Email Extraction**
   - Multiple regex patterns for different email formats
   - Text cleaning to remove UI elements
   - Visual analysis of screenshots for email detection

2. **Robust Validation**
   - Multi-stage validation to confirm email structure
   - Character-by-character analysis for partial emails
   - Context-aware email detection

## Next Steps

### Immediate Priorities
1. **Fix coordinate-based interaction issues**
   - Implement better coordinate boundary handling
   - Add multiple click fallback strategies
   - Improve coordinate normalization

2. **Complete end-to-end testing**
   - Test email extraction in varied scenarios
   - Verify recipe PDF generation
   - Validate conversation flow

3. **Add more visual analysis capabilities**
   - Enhance screenshot analysis for better UI understanding
   - Improve error recovery with visual feedback
   - Implement UI change detection

### Medium-term Goals
1. **Implement FastAPI backend**
   - Create web API for user management
   - Add monitoring endpoints
   - Implement authentication

2. **Improve recipe extraction**
   - Enhance Claude prompts for better extraction
   - Add more ingredient parsing capabilities
   - Implement nutrition information extraction

3. **Prepare for deployment**
   - Create Docker configuration
   - Set up continuous integration
   - Implement monitoring and logging

## Key Implementation Insights

### 1. Visual Understanding Is More Robust
Traditional DOM-based automation is fragile. Visual understanding with Claude provides more human-like interaction with UIs and is more resistant to changes.

### 2. Defense in Depth Strategy
Multiple fallback mechanisms greatly improve reliability. Each interaction attempt should have at least 3 different approaches to maximize success.

### 3. Email Extraction Complexity
Email extraction from UI text is a complex challenge requiring multiple approaches including regex, text analysis, and visual identification.

### 4. Continuous Adaptation Required
Instagram's anti-automation measures continue to evolve. Our system needs continuous monitoring and adaptation to maintain reliability.

## Reference Materials

### Claude Vision Assistant Usage
```python
# Example usage of Claude Vision Assistant for UI analysis
screenshot_path = "screenshots/current_view.png"
ui_elements = claude_assistant.identify_ui_elements(screenshot_path)

# Extract identified elements
if "input_field" in ui_elements:
    x, y = ui_elements["input_field"]["x"], ui_elements["input_field"]["y"]
    # Click at these coordinates
    
# Extract emails from conversation
emails = claude_assistant.extract_emails(screenshot_path)
if emails:
    email = emails[0]  # Use the first extracted email
```

### Enhanced Email Extraction
```python
# Multi-stage email extraction
def extract_email_from_text(self, text: str) -> Optional[str]:
    """Extract email from text with multiple approaches."""
    # Try regex pattern first
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(email_pattern, text)
    if matches:
        return matches[0]
        
    # Try cleaning text and checking words
    cleaned_text = text.lower()
    for element in ui_elements:
        cleaned_text = cleaned_text.replace(element, ' ')
    
    words = cleaned_text.split()
    for word in words:
        if '@' in word and '.' in word:
            # Clean and validate the word
            cleaned_word = re.sub(r'[^a-zA-Z0-9.@_+-]', '', word)
            if re.match(email_pattern, cleaned_word):
                return cleaned_word
                
    return None
```

### Multiple Interaction Strategies
```python
def _click_at_normalized_coordinates(self, normalized_x: float, normalized_y: float) -> bool:
    """Click at coordinates with multiple strategies."""
    try:
        # Convert normalized to actual coordinates
        x = int(normalized_x * self.screen_width)
        y = int(normalized_y * self.screen_height)
        
        # Strategy 1: Direct ActionChains click
        try:
            actions = ActionChains(self.driver)
            actions.move_by_offset(x, y).click().perform()
            return True
        except Exception as e:
            logger.warning(f"Direct click failed: {str(e)}")
            
        # Strategy 2: JavaScript elementFromPoint
        try:
            self.driver.execute_script(f"""
                document.elementFromPoint({x}, {y}).click();
            """)
            return True
        except Exception as e:
            logger.warning(f"JavaScript click failed: {str(e)}")
            
        # Strategy 3: Find element and click
        element = self.driver.execute_script(f"return document.elementFromPoint({x}, {y});")
        if element:
            element.click()
            return True
            
        return False
    except Exception as e:
        logger.error(f"All click approaches failed: {str(e)}")
        return False
```

---
[End of Project Bible - Last Updated: March 15, 2025]

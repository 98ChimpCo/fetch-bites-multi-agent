# Project Bible: Instagram Recipe Multi-Agent System

## Project Overview
**Project Name:** Fetch Bites Multi-Agent System  
**Start Date:** March 10, 2025  
**Current Phase:** Basic Working MVP with Instagram Integration  
**Last Updated:** March 14, 2025

## Quick Reference
**Current Status:** Functional MVP with successful Instagram DM monitoring and recipe detection  
**Next Milestone:** Complete email delivery integration and enhanced recipe extraction refinement  
**Current Blockers:** None - core functionality working with expected limitations

## Project Goals
1. Primary Goal: Create an agentic AI system that converts Instagram recipe posts into structured PDF recipe cards
2. Secondary Goals: Automate monitoring, extraction, and delivery process with minimal human intervention
3. Success Criteria: Successfully extract recipe data from Instagram posts and generate PDF cards with >90% accuracy

## Progress Update
Since the previous update, we've made significant progress:

1. **Instagram DM Monitoring**
   - Successfully implemented Instagram login and session management
   - Created reliable conversation detection and prioritization system
   - Developed robust message detection for various Instagram UI patterns
   - Implemented multi-method approach for finding and responding to messages

2. **Recipe Content Detection**
   - Enhanced recipe identification for both URLs and direct shares
   - Added support for detecting recipe content shared within Instagram DMs
   - Improved keyword-based classification of recipe content
   - Implemented detection for multiple Instagram content sharing formats

3. **Message Processing Flow**
   - Created complete conversation flow from message reception to response
   - Successfully demonstrated "Hello" message detection and response
   - Added prioritization for human conversations with recipe content
   - Implemented robust error handling and recovery mechanisms

4. **PDF Generation**
   - Verified PDF generation functionality with proper formatting
   - Confirmed structured recipe data is correctly transformed into recipe cards
   - Successfully tested PDF output with real recipe content

## Technical Architecture
**Core Technologies:**
- Backend: Python, FastAPI (planned)
- Agents: 
  - InstagramMessageAdapter: Selenium/ChromeDriver for Instagram DM monitoring
  - InstagramMonitor: Selenium/ChromeDriver for Instagram post extraction
  - RecipeExtractor: Claude API, regex fallback
  - PDFGenerator: ReportLab
  - DeliveryAgent: SendGrid (planned)
- Storage: SQLite (planned)
- Deployment: Docker, Replit (planned)

**Agent Architecture:**
- Instagram Message Adapter: Monitors Instagram DMs for recipe shares
- Instagram Monitor Agent: Identifies and extracts recipe posts
- Recipe Extractor Agent: Converts unstructured text to structured recipe data
- PDF Generator Agent: Creates formatted recipe PDFs
- Delivery Agent: Handles email distribution

## Current Implementation Status

### Completed Components
1. **Instagram Message Adapter**:
   - Status: ✅ Complete
   - Key Features: Message monitoring, conversation detection, response handling
   - Notes: Successfully identifies and responds to messages

2. **Instagram Monitor Agent**:
   - Status: ✅ Complete
   - Key Features: Post content extraction, recipe identification
   - Notes: Works with both direct URLs and shared content

3. **Recipe Extractor Agent**:
   - Status: ✅ Complete
   - Key Features: Claude API integration, regex fallback, structured output
   - Notes: Extracts recipe components from various formats

4. **PDF Generator Agent**:
   - Status: ✅ Complete
   - Key Features: Professional recipe cards, consistent formatting
   - Notes: Creates attractive, printable recipe PDFs

### In Progress
1. **Delivery Agent**:
   - Status: 🔄 Implementation
   - Current Focus: Email delivery mechanism
   - Pending Items: SendGrid integration testing
   - Blockers: None

2. **End-to-end Workflow**:
   - Status: 🔄 Testing
   - Current Focus: Complete flow from message to delivery
   - Pending Items: Testing with real user scenarios
   - Blockers: None

### Planned/Todo
1. **User Management System**:
   - Priority: Medium
   - Dependencies: Core agent functionality
   - Notes: User preferences and subscription management

2. **Web API Implementation**:
   - Priority: Medium
   - Dependencies: Core agent functionality
   - Notes: FastAPI implementation for user interactions

3. **Deployment Configuration**:
   - Priority: Low
   - Dependencies: Complete workflow
   - Notes: Docker and Replit setup

## Technical Challenges & Solutions

### Instagram DM Monitoring Challenges

#### Challenge: Instagram Anti-Automation Measures
Instagram employs various techniques to detect and block automated browsers.

**Solutions Implemented:**
1. **Multiple Browser Fingerprinting Defenses**
   - WebDriver property masking
   - JavaScript execution for DOM manipulation
   - Cookie-based authentication for faster access

2. **Dynamic Element Finding**
   - Multiple selector strategies for each element
   - JavaScript-based element identification
   - Fallback approaches when primary methods fail

3. **Conversation Prioritization**
   - Focus on human conversations with relevant content
   - Multi-tier prioritization system
   - Filtering out system conversations

#### Challenge: Message Input Field Detection
Finding and interacting with message input fields is particularly challenging.

**Solutions Implemented:**
1. **Multi-method Input Detection**
   - Multiple selectors and approaches
   - JavaScript-based element focusing
   - Action chains for reliable interaction

2. **Contextual Processing**
   - Process messages in the context of their conversation
   - Direct response while in the active conversation
   - Fallback message sending strategies

### Recipe Extraction Challenges

#### Challenge: Varied Content Sharing Methods
Instagram content can be shared in multiple formats.

**Solutions Implemented:**
1. **Flexible Content Detection**
   - Support for direct URLs
   - Recognition of shared posts
   - Extraction from message content

2. **Keyword-based Classification**
   - Recipe-specific keyword detection
   - Structure pattern recognition
   - Measurement and ingredient identification

## Lessons Learned

1. **Instagram Automation Complexity**
   - Instagram's anti-automation measures require sophisticated approaches
   - Multiple fallback strategies are essential for reliability
   - Cookie-based authentication improves session management

2. **Dynamic Content Challenges**
   - Instagram's UI changes frequently, requiring flexible selectors
   - JavaScript-based DOM manipulation is more robust than fixed selectors
   - Screenshot logging is invaluable for visual debugging

3. **User Experience Focus**
   - Prioritizing human conversations improves resource allocation
   - Fast response time enhances user engagement
   - Simple, clear messaging is important for user understanding

## Next Steps

1. **Email Delivery Completion**
   - Complete SendGrid integration testing
   - Create professional email templates
   - Implement delivery tracking

2. **Recipe Extraction Refinement**
   - Test with wider variety of recipe formats
   - Gather extraction accuracy data
   - Refine detection algorithms

3. **User Management Development**
   - Implement user preference storage
   - Create subscription management
   - Build authentication system

4. **Deployment Preparation**
   - Prepare Docker configuration
   - Set up cloud hosting
   - Create monitoring systems

## Key Code Implementations

### Enhanced Instagram Message Monitoring

```python
def check_new_messages(self) -> List[Dict[str, Any]]:
    """Check for new messages in the Instagram inbox."""
    try:
        # Navigate to inbox fresh
        self.driver.get("https://www.instagram.com/direct/inbox/")
        time.sleep(3)
        
        # Find conversations using JavaScript to avoid stale element issues
        conversations_js = """
        let results = [];
        try {
            // Get all conversation elements
            const allConvos = Array.from(document.querySelectorAll('div[role="listitem"], div[role="button"]'));
            
            // Get only elements with text content
            results = allConvos
                .filter(el => {
                    const text = el.textContent && el.textContent.trim();
                    return text && text.length > 0 && 
                           !text.includes('Page Not Found') && 
                           !text.includes('Requests');
                })
                .map((el, index) => ({
                    index: index,
                    text: el.textContent.trim(),
                    hasUnread: el.textContent.includes('New message')
                }));
        } catch (e) {
            console.error('Error finding conversations:', e);
        }
        return results;
        """
        
        conversations = self.driver.execute_script(conversations_js)
        
        # Prioritize conversations with "Hello" or recipe content
        hello_conversations = [c for c in conversations if 'hello' in c.get('text', '').lower()]
        recipe_conversations = [c for c in conversations if any(term in c.get('text', '').lower() 
                                for term in ['recipe', 'food', 'cook', 'kauscooks'])]
        
        # Process conversations in priority order
        # [implementation details omitted for brevity]
        
        return new_messages
    except Exception as e:
        logger.error(f"Error checking new messages: {str(e)}")
        return []
```

### Recipe Content Extraction

```python
def extract_post_content(self, post_url_or_content, max_retries=3):
    """Extract content from an Instagram post URL or shared content."""
    # Check if input is a valid URL or direct content
    is_url = post_url_or_content.startswith('http')
    
    # Handle direct content (not a URL)
    if not is_url:
        logger.info("Processing direct content share rather than URL...")
        
        # Create a content object from the shared post
        content = {
            'caption': post_url_or_content,
            'username': self._extract_username_from_content(post_url_or_content),
            'hashtags': self._extract_hashtags_from_content(post_url_or_content),
            'recipe_indicators': self._check_recipe_indicators(post_url_or_content),
            'urls': self._extract_urls_from_content(post_url_or_content),
            'source': {
                'platform': 'Instagram',
                'url': 'Direct share',
                'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        return content
        
    # Handle URL-based extraction
    # [implementation details omitted for brevity]
```

## References

### Instagram DM Monitoring Documentation
- Cookie-based authentication for reliable sessions
- Multi-method approach for message detection
- Conversation prioritization strategies

### Recipe Classification Approach
- Keyword-based recipe identification
- Structure pattern recognition
- Measurement and instruction detection

---
[End of Project Bible - Last Updated: March 14, 2025]

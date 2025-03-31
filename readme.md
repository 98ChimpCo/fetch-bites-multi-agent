# Fetch Bites — AI-Powered Instagram Recipe Agent

**Fetch Bites** is an intelligent automation agent designed to monitor Instagram Direct Messages (DMs) for shared recipe posts. It automatically replies with beautifully generated, printable PDF recipe cards. The agent uses Claude Vision to visually interpret Instagram's UI, extract content from posts, and transform them into structured, easily shareable recipes.

---

## 🚀 Project Status

**Version:** v0.3.0 (Closed-Loop Vision Agent)  
**Status:** Actively under development

---

## 🔥 Features

- 💬 Monitors Instagram DMs via browser automation
- 🧠 Uses Claude Vision to detect shared post previews
- 🖼 Expands posts using both DOM-based interactions and AI-guided fallback clicking
- ✍️ Extracts captions and metadata using Claude Vision prompts
- 🧪 Automatically parses recipe steps, ingredients, and titles with Claude's reasoning
- 📄 Generates and saves printable PDF recipe cards
- 📤 Replies with the recipe PDF directly in Instagram DMs using Claude-guided UI interactions

---

## ⚙️ Setup Instructions

### Prerequisites

Before you begin, ensure that you have the following prerequisites:

- **Python 3.9+**
- **Google Chrome** browser (compatible with Selenium WebDriver or Playwright for automation)
- **Instagram account** (for logging in to Instagram and interacting with DMs)
- **Anthropic Claude API key** (for utilizing Claude Vision to analyze Instagram posts)
- **Python dependencies** listed in `requirements.txt`.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/fetch-bites.git
   cd fetch-bites
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file in the root directory with the following content:**
   ```env
   # Instagram credentials
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password

   # Claude API
   ANTHROPIC_API_KEY=your_anthropic_api_key

   # Optional: Email delivery configuration (for future use)
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=your_sendgrid_api_key
   EMAIL_SENDER=your_verified_sender@example.com

   # Monitoring interval (in seconds)
   MONITORING_INTERVAL=30
   ```

---

## 🧪 Running the Agent

To run the system as a whole, simply execute:
```bash
python playwright_preview_clicker.py
```

For testing a known Instagram post, you can run:
```bash
python manual_post_tester.py --url https://www.instagram.com/p/your_post_id/
```

---

## 👤 User Interaction Flow

### First-Time Users
1. User sends a message or post to the agent.
2. Agent identifies the shared post visually using Claude.
3. The post is expanded, and its caption is extracted.
4. Claude parses the recipe and generates a PDF.
5. Agent replies to the same DM thread with the generated PDF automatically.

### Returning Users
1. The agent can handle multiple incoming posts from the same user.
2. It extracts, parses, and replies to each with a recipe PDF in the same thread.

---

## 🗂 Project Structure

The project is organized as follows:

```
fetch-bites/
├── main_vision_fixed_v2.py          # Main entry point with Vision support
├── manual_post_tester.py            # Test tool for manually processing known Instagram post links
├── .env                             # Environment variables file for API keys and settings
├── requirements.txt                 # Python dependencies
├── screenshots/                     # Debugging directory for storing vision screenshots
├── pdfs/                            # Folder to store generated recipe PDFs
├── src/
│   ├── agents/                      # Core agents for handling Claude, PDF generation, and recipe extraction
│   ├── utils/                       # Instagram-specific adapters and conversation handlers
│   └── workflows/                   # Workflow logic for extracting and processing recipes
└── data/
    └── users/                       # User-specific data storage (e.g., email addresses, state)
```

---

## 📌 Upcoming Milestones

- [ ] Conversational onboarding flow with user memory
- [ ] Email collection and delivery support
- [ ] Database storage of user and recipe data
- [ ] Open-source LLM fallback for visual or caption parsing
- [ ] OCR fallback support for Reels or text-in-video posts
- [ ] Language-aware recipe processing and localization

---

## 📜 License

The code is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- [Anthropic Claude](https://www.anthropic.com/) — powering UI understanding and recipe parsing
- [Playwright](https://playwright.dev/) — for stable browser automation and file uploads
- [Jinja2 + wkhtmltopdf](https://wkhtmltopdf.org/) — for clean PDF rendering

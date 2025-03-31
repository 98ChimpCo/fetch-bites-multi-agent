# Fetch Bites — AI-Powered Instagram Recipe Agent

**Fetch Bites** is an intelligent automation agent designed to monitor Instagram Direct Messages (DMs) for shared recipe posts. It automatically replies with beautifully generated, printable PDF recipe cards. The agent uses Claude Vision to visually interpret Instagram's UI, extract content from posts, and transform them into structured, easily shareable recipes.

---

## 🚀 Project Status

**Version:** v0.2.0 (Interactive Agent Prototype)  
**Status:** Actively under development

---

## 🔥 Features

- 💬 Monitors Instagram DMs via browser automation
- 🧠 Uses Claude Vision to detect shared post previews
- 🖼 Expands posts using both DOM-based interactions and AI-guided fallback clicking
- ✍️ Extracts captions and metadata using Claude Vision prompts
- 🧪 Automatically parses recipe steps, ingredients, and titles with Claude's reasoning
- 📄 Generates and saves printable PDF recipe cards
- 📨 [Coming Soon] Sends recipe cards back via Instagram DM or email

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
python main_vision_fixed_v2.py
```

For testing a known Instagram post, you can run:
```bash
python manual_post_tester.py --url https://www.instagram.com/p/your_post_id/
```

---

## 👤 User Interaction Flow

### First-Time Users
1. User sends a message or post to the agent.
2. Agent replies with an introduction message and asks for a recipe link.
3. User sends a post or video containing a recipe.
4. The agent expands the post, extracts the recipe, and asks for the user's email.
5. The user sends their email address.
6. The agent generates the recipe as a PDF and "sends" it (mock or real).

### Returning Users
1. The agent remembers the user and skips the intro message.
2. It extracts the recipe and reuses the email address to deliver the result.
3. The agent can handle multiple posts and repeat the process with a feedback loop.

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

- [ ] **Email Detection from DMs** – Automating email collection from conversations.
- [ ] **PDF Delivery via Email or Instagram** – Integrating email APIs for real-world delivery.
- [ ] **OCR Fallback for Video-only Reels** – Adding support for processing recipe text in Instagram Reels.
- [ ] **Language Translation for International Recipes** – Enabling automatic translation of recipe content.

---

## 📜 License

The code is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- [Anthropic Claude](https://www.anthropic.com/) — for the Claude Vision model, which powers recipe extraction from images.
- [Selenium](https://www.selenium.dev/) — used for automating browser interactions (currently being transitioned to Playwright).
- [Jinja2 + wkhtmltopdf](https://wkhtmltopdf.org/) — for rendering the recipe into a PDF format.

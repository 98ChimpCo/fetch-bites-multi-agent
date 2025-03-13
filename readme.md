# Fetch Bites: Instagram Recipe Agent

Fetch Bites is an AI-powered Instagram agent that turns recipe posts into beautiful, printable recipe cards delivered straight to your inbox.

## Project Status

**Current Version:** v0.1.0 (MVP)  
**Status:** Ready for user testing

## Features

- 📱 Extract recipes from Instagram posts
- 🧙‍♂️ Intelligent recipe extraction using Claude AI
- 📑 Generate professional PDF recipe cards
- 📧 Deliver recipe cards via email
- 💬 Interactive Instagram DM interface

## Setup Instructions

### Prerequisites

- Python 3.9+
- Chrome browser (for Selenium)
- Instagram account for the agent
- Anthropic API key (for Claude)
- SMTP server access (for email delivery)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fetch-bites.git
   cd fetch-bites
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   # Instagram credentials
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password

   # Anthropic API Key
   ANTHROPIC_API_KEY=your_anthropic_api_key

   # Email configuration
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=your_sendgrid_api_key
   EMAIL_SENDER=your_verified_sender@example.com
   ```

### Running the Application

Start the application:
```bash
python main.py
```

The agent will:
1. Log in to Instagram
2. Monitor for direct messages
3. Respond to user messages according to the onboarding flow
4. Process recipe post URLs as they are received

## User Interaction Flow

### First-time User

1. User sends a message to the Instagram agent
2. Agent responds with welcome message explaining the service
3. User sends an Instagram recipe post URL
4. Agent asks for user's email address
5. User provides email address
6. Agent extracts recipe, creates PDF, and sends it to the user's email
7. Agent confirms delivery and encourages further use

### Returning User

1. User sends an Instagram recipe post URL
2. Agent recognizes user and confirms processing
3. Agent extracts recipe, creates PDF, and sends it to the user's saved email
4. Agent confirms delivery

## Development

### Project Structure

```
fetch-bites/
├── main.py                  # Application entry point
├── requirements.txt         # Dependencies
├── .env                     # Environment variables
├── src/
│   ├── agents/
│   │   ├── instagram_monitor.py  # Instagram scraping
│   │   ├── recipe_extractor.py   # Recipe extraction with Claude
│   │   ├── pdf_generator.py      # PDF generation
│   │   └── delivery_agent.py     # Email delivery
│   └── utils/
│       ├── user_state.py         # User state management
│       ├── message_templates.py  # Message templates
│       ├── conversation_handler.py  # Conversation flow
│       └── instagram_message_adapter.py  # Instagram DM interface
└── data/
    ├── users/               # User data storage
    ├── raw/                 # Raw scraped data
    ├── processed/           # Processed recipes
    └── pdf/                 # Generated PDFs
```

## License

[MIT License](LICENSE)

## Acknowledgements

- [Anthropic Claude](https://www.anthropic.com/claude) for recipe extraction
- [Selenium](https://www.selenium.dev/) for Instagram automation
- [ReportLab](https://www.reportlab.com/) for PDF generation

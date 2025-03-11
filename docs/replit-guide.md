# Deploying Your Instagram Recipe Agent on Replit

Replit is a great platform for hosting your Instagram recipe agent, especially for development and testing. This guide will walk you through deploying your project on Replit.

## Step 1: Create a New Repl

1. Go to [Replit](https://replit.com/) and sign in or create an account.
2. Click on "Create Repl" in the dashboard.
3. Select "Python" as the template.
4. Name your Repl something like "instagram-recipe-agent" and click "Create Repl".

## Step 2: Upload Your Code

You have two options:

### Option A: Upload Files
1. In the Replit interface, click on the three dots next to "Files" in the left sidebar
2. Select "Upload folder" and upload your project directory

### Option B: Connect to GitHub
1. Initialize a Git repository in your local project
2. Push to GitHub
3. In Replit, click on "Connect to GitHub" in the Version Control panel
4. Select your repository

## Step 3: Set Up Environment Variables

1. In the sidebar, click on the lock icon (Secrets/Environment Variables)
2. Add the following environment variables:
   ```
   ANTHROPIC_API_KEY=your_anthropic_api_key
   SENDGRID_API_KEY=your_sendgrid_api_key
   EMAIL_SENDER=your_email@example.com
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   ```

## Step 4: Configure Replit for Your Application

Create a `.replit` file with the following content:

```
language = "python3"
entrypoint = "main.py"
run = "uvicorn main:app --host 0.0.0.0 --port 8080"

[env]
PYTHONPATH = "/home/runner/${REPL_SLUG}"

[packager]
ignoredPackages = ["chrome-driver"]

[nix]
channel = "stable-22_11"

[deployment]
run = ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8080"]
deploymentTarget = "cloudrun"
```

## Step 5: Install Dependencies

Create a `replit.nix` file with the following content to install system dependencies:

```nix
{ pkgs }: {
  deps = [
    pkgs.python39
    pkgs.python39Packages.pip
    pkgs.chromium
    pkgs.chromedriver
  ];
  env = {
    PYTHONBIN = "${pkgs.python39}/bin/python3.9";
    PYTHONHOME = "${pkgs.python39}";
    CHROMEDRIVER_PATH = "${pkgs.chromedriver}/bin/chromedriver";
    CHROME_BIN = "${pkgs.chromium}/bin/chromium";
  };
}
```

Then install Python dependencies by running the following in the Replit Shell:

```bash
pip install -r requirements.txt
```

## Step 6: Modify Code for Replit

Update your Instagram monitor agent to use the Replit-specific Chrome paths:

```python
# In src/agents/instagram_monitor.py, modify _setup_browser method:

def _setup_browser(self):
    """Set up headless browser for Instagram scraping"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    
    # Initialize the Chrome WebDriver
    chrome_driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    if os.path.exists(chrome_driver_path):
        self.driver = webdriver.Chrome(
            service=Service(chrome_driver_path),
            options=chrome_options
        )
    else:
        # Fall back to webdriver_manager
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
    
    logger.info("Browser setup complete")
```

## Step 7: Run Your Repl

1. Click on the "Run" button at the top of the Replit interface
2. Replit will install dependencies and start your FastAPI application
3. You'll see a web view appear showing your application running

## Step 8: Set Up Replit Always On (Optional)

For Basic, Pro, or Teams users:

1. Click on the "Tools" button in the left sidebar
2. Select "Always On"
3. Toggle the switch to enable Always On
4. Your Repl will now continue running even when you're not actively using it

## Step 9: Connect a Custom Domain (Optional)

For Pro or Teams users:

1. Click on the "Tools" button in the left sidebar
2. Select "Custom Domain"
3. Follow the instructions to connect your domain

## Troubleshooting

### Chrome/Selenium Issues
If you encounter issues with Chrome or Selenium, try updating the browser options in the `_setup_browser` method:

```python
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-setuid-sandbox")
chrome_options.add_argument("--remote-debugging-port=9222")
```

### Database Persistence
By default, your SQLite database will be stored in the Replit file system and will persist between runs. However, it may be deleted if your Repl is inactive for an extended period. Consider using a cloud database service for long-term storage.

### Memory Limitations
Free Replit accounts have memory limitations. If you run into memory issues, consider:

1. Processing fewer Instagram accounts at once
2. Reducing the image quality in PDFs
3. Implementing batch processing for larger workloads

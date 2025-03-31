"""
Message templates for the Instagram Recipe Agent onboarding flow.
"""

# Initial welcome message for new users
WELCOME_MESSAGE = """
👋 Hello there, food explorer! I'm Fetch Bites, your personal recipe assistant! 🥘

I can turn Instagram recipe posts into beautiful, printable recipe cards delivered straight to your inbox! No more screenshots or manually typing out recipes.

To use me:
1. Send me an Instagram recipe post link (must start with https://www.instagram.com/...)
2. Or share a recipe post directly from the Instagram app
3. I'll extract the recipe and create a PDF recipe card for you!

Ready to try it out? Send me a recipe post!
"""

# Help message explaining the service
HELP_MESSAGE = """
🔍 Here's how I can help you:

📱 Send me an Instagram post URL with a recipe
🧙‍♂️ I'll extract all the tasty details
📑 Transform it into a professionally formatted recipe card
📧 And deliver it straight to your inbox!

It's that simple! Ready to try it out? Just send me a recipe post link!
"""

# Request for email address
EMAIL_REQUEST = """
That recipe looks delicious! 😋 Before I can send you the recipe card...

📧 What email address should I send your recipe card to?
(Just type your email address)
"""

# Confirmation after receiving email
EMAIL_CONFIRMATION = """
Perfect! I'll send your recipe card to {email}.

Working on your recipe card now... ⏳
"""

# Message after processing is complete
PROCESSING_COMPLETE = """
✨ Recipe card for "{recipe_title}" has been created and sent to your inbox!

Feel free to send me another recipe post anytime you want to save a recipe.

Happy cooking! 👨‍🍳👩‍🍳
"""

# Message for returning users
RETURNING_USER = """
I see another tasty recipe! 👀 I'll fetch that for you and send it to {email}.

Working on your recipe card now... ⏳
"""

# Error messages
INVALID_URL = """
Hmm, that doesn't look like an Instagram post link. Please send me a link that starts with "https://www.instagram.com/p/" or "https://instagram.com/p/"
"""

EXTRACTION_ERROR = """
I had some trouble extracting the recipe from that post. It might not contain a complete recipe, or Instagram might be acting up.

Could you try sending me a different recipe post?
"""

PROCESSING_ERROR = """
Oops! Something went wrong while creating your recipe card. Our team has been notified about this issue.

Could you try sending me a different recipe post? Or try this one again in a few minutes?
"""

INVALID_EMAIL = """
That doesn't look like a valid email address. Please send me a valid email so I can deliver your recipe card.
"""

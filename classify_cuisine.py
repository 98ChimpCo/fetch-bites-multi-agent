import os
import json
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

CACHE_PATH = "analytics/classification_cache.json"
os.makedirs("analytics", exist_ok=True)
if os.path.exists(CACHE_PATH):
    with open(CACHE_PATH) as f:
        classification_cache = json.load(f)
else:
    classification_cache = {}

def classify_cuisine_and_format(text):
    if text in classification_cache:
        return classification_cache[text]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You're a recipe assistant. Given a recipe or a caption, return the most likely cuisine and meal format."
                },
                {
                    "role": "user",
                    "content": f"Here is the recipe or caption:\n{text}"
                }
            ],
            functions=[
                {
                    "name": "set_classification",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cuisine": {
                                "type": "string",
                                "description": "Cuisine category like Italian, Persian, Indian, Thai, etc."
                            },
                            "meal_format": {
                                "type": "string",
                                "description": "Meal type like Breakfast, Lunch, Dinner, Snack, Brunch"
                            }
                        },
                        "required": ["cuisine", "meal_format"]
                    }
                }
            ],
            function_call={"name": "set_classification"}
        )
        args = response["choices"][0]["message"]["function_call"]["arguments"]
        parsed = json.loads(args)
        cuisine = parsed.get("cuisine", "unknown")
        meal_format = parsed.get("meal_format", "unknown")
        classification_cache[text] = {
            "cuisine": cuisine,
            "meal_format": meal_format
        }
        with open(CACHE_PATH, "w") as f:
            json.dump(classification_cache, f, indent=2)
        return classification_cache[text]
    except Exception as e:
        print(f"Classification failed: {e}")
        return {"cuisine": "unknown", "meal_format": "unknown"}
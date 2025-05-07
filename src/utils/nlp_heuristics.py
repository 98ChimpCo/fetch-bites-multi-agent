import re

def looks_like_recipe_caption(caption: str) -> bool:
    """
    Basic heuristic to determine if a caption is likely to contain a recipe.
    Returns True if it appears to be a recipe, False otherwise.
    """
    if not caption:
        return False

    caption = caption.lower()

    keywords = [
        "ingredients", "instructions", "prep", "preheat", "oven",
        "minutes", "tsp", "tbsp", "cup", "grams", "serve", "mix", "bake", "chop"
    ]
    if any(keyword in caption for keyword in keywords):
        return True

    if re.search(r"\d+\.", caption) or re.search(r"•\s", caption):
        return True

    return False

# --- Additional heuristics for recipe comment blocks ---

def is_long_enough(text: str, min_words: int = 50) -> bool:
    return len(text.split()) >= min_words

def contains_recipe_signals(text: str) -> bool:
    ingredient_keywords = [
        "cup", "cups", "tbsp", "tsp", "tablespoon", "teaspoon",
        "grams", "g", "ml", "mix", "combine", "bake", "preheat",
        "oven", "flour", "sugar", "salt", "pepper", "butter", "oil"
    ]
    text = text.lower()
    return any(word in text for word in ingredient_keywords)

def looks_like_recipe_comment_block(text: str, min_words: int = 50) -> bool:
    """
    Heuristic for detecting recipe-like comment blocks, typically from the first comment.

    This function is intended to evaluate only the top (first) comment for now.
    If both conditions are met—minimum word count and recipe-related signals—it returns True.
    """
    if not text or not is_long_enough(text, min_words=min_words):
        return False
    return contains_recipe_signals(text)
import re

def sanitize_recipe_data(recipe_data):
    """Basic cleanup of recipe fields for PDF generation."""
    sanitized = recipe_data.copy()
    for key in ['title', 'ingredients', 'instructions']:
        value = sanitized.get(key)
        if isinstance(value, str):
            sanitized[key] = value.strip()
        elif isinstance(value, list):
            sanitized[key] = [item.strip() for item in value if isinstance(item, str)]
    return sanitized

def extra_sanitize_recipe_data(recipe_data):
    """Strips out any invalid characters and collapses whitespace."""
    import re
    sanitized = sanitize_recipe_data(recipe_data)
    for key in ['title', 'ingredients', 'instructions']:
        value = sanitized.get(key)
        if isinstance(value, str):
            sanitized[key] = re.sub(r'\s+', ' ', value)
        elif isinstance(value, list):
            sanitized[key] = [re.sub(r'\s+', ' ', item) for item in value]
    return sanitized
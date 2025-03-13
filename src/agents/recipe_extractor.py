# src/agents/recipe_extractor.py
import os
import json
import re
import logging
import requests
from typing import Dict, List, Optional
import anthropic

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handler if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class RecipeExtractor:
    """
    Recipe Extractor Agent for extracting structured recipe data from text
    """
    
    def __init__(self):
        """
        Initialize Recipe Extractor Agent
        """
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment variables")
        
        # Initialize Anthropic client if API key is available
        self.client = None
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def extract_recipe(self, text: str, force: bool = False) -> Optional[Dict]:
        """
        Extract structured recipe data from text
        
        Args:
            text (str): Text to extract recipe from
            force (bool, optional): Force extraction even if content is minimal
            
        Returns:
            dict: Structured recipe data or None if extraction fails
        """
        try:
            logger.info("Extracting recipe from text...")
            
            # Check if text is too short to be a recipe, unless force=True
            if len(text.split()) < 20 and not force:
                logger.warning("Text too short to extract recipe")
                return None
                    
            # Use Claude API if available, otherwise use regex-based extraction
            if self.client:
                return self._extract_with_claude(text)
            else:
                logger.warning("Claude API not available, using fallback extraction")
                return self._extract_with_regex(text)
                
        except Exception as e:
            logger.error(f"Failed to extract recipe: {str(e)}")
            return None
    
    def _extract_with_claude(self, text: str) -> Optional[Dict]:
        """
        Extract recipe data using Claude API
        
        Args:
            text (str): Text to extract recipe from
            
        Returns:
            dict: Structured recipe data or None if extraction fails
        """
        try:
            # Create prompt for Claude
            prompt = f"""
Extract a complete recipe from this Instagram post caption.

CAPTION:
{text}

Extract the following information in JSON format:
1. Recipe title
2. Recipe description (brief summary if available)
3. Ingredients list (with quantities and units when available)
4. Step-by-step instructions
5. Cooking time (prep time, cook time, total time)
6. Servings/yield
7. Any dietary information (vegan, gluten-free, etc.)
8. Difficulty level (easy, medium, hard)

Format the response as a valid JSON object with the following structure:
{{
    "title": "Recipe Title",
    "description": "Brief description",
    "ingredients": [
        {{
            "quantity": "1",
            "unit": "cup",
            "name": "flour"
        }},
        ...
    ],
    "instructions": [
        "Step 1 instructions",
        "Step 2 instructions",
        ...
    ],
    "prep_time": "15 minutes",
    "cook_time": "30 minutes",
    "total_time": "45 minutes",
    "servings": "4",
    "dietary_info": ["vegan", "gluten-free"],
    "difficulty": "medium"
}}

If any information is not available, use null or an empty array as appropriate.
If you cannot extract a complete recipe, return as much information as possible.
"""

            # Call Claude API
            message = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",  # Updated model name
                max_tokens=4000,
                temperature=0,
                system="You are a helpful assistant that extracts recipe data from text and returns it in JSON format.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from Claude's response
            response_text = message.content[0].text
            
            # Extract JSON from the response
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code block
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response_text
            
            # Parse JSON response
            recipe_data = json.loads(json_str)
            
            # Validate if it's a recipe (must have at least title and some ingredients or instructions)
            if recipe_data.get('title') and (recipe_data.get('ingredients') or recipe_data.get('instructions')):
                logger.info(f"Successfully extracted recipe: {recipe_data['title']}")
                return recipe_data
            else:
                logger.warning("Claude response doesn't contain a valid recipe")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract recipe with Claude: {str(e)}")
            return None
    
    def _extract_with_regex(self, text: str) -> Optional[Dict]:
        """
        Extract recipe data using regex patterns (fallback method)
        
        Args:
            text (str): Text to extract recipe from
            
        Returns:
            dict: Structured recipe data or None if extraction fails
        """
        try:
            # Extract title (look for capitalized phrases or lines ending with "Recipe")
            title_match = re.search(r'([A-Z][A-Za-z\s]+)(?:[\s\n]Recipe|\n|:)', text)
            title = title_match.group(1).strip() if title_match else "Untitled Recipe"
            
            # Extract ingredients section
            ingredients_section = ""
            ingredients_match = re.search(r'(?:INGREDIENTS|Ingredients|ingredients)(?::|[\s\n])+([^#]+?)(?:INSTRUCTIONS|Instructions|instructions|DIRECTIONS|Directions|directions|STEPS|Steps|steps|$)', text, re.DOTALL)
            if ingredients_match:
                ingredients_section = ingredients_match.group(1).strip()
            
            # Parse ingredients
            ingredients = []
            if ingredients_section:
                ingredient_items = re.findall(r'[-•*]?\s*([^•*\n]+)', ingredients_section)
                for item in ingredient_items:
                    item = item.strip()
                    if not item:
                        continue
                        
                    # Try to split quantity, unit, and name
                    match = re.match(r'([\d./]+)?\s*([a-zA-Z]+)?\s*(.*)', item)
                    if match:
                        quantity, unit, name = match.groups()
                        ingredients.append({
                            "quantity": quantity if quantity else "",
                            "unit": unit if unit else "",
                            "name": name.strip()
                        })
                    else:
                        ingredients.append({
                            "quantity": "",
                            "unit": "",
                            "name": item
                        })
            
            # Extract instructions section
            instructions_section = ""
            instructions_match = re.search(r'(?:INSTRUCTIONS|Instructions|instructions|DIRECTIONS|Directions|directions|STEPS|Steps|steps)(?::|[\s\n])+([^#]+?)(?:NOTES|Notes|notes|$)', text, re.DOTALL)
            if instructions_match:
                instructions_section = instructions_match.group(1).strip()
            
            # Parse instructions
            instructions = []
            if instructions_section:
                # Try numbered steps first
                numbered_steps = re.findall(r'(?:\d+\.\s*)([^.0-9]+)(?=\d+\.|$)', instructions_section)
                if numbered_steps:
                    instructions = [step.strip() for step in numbered_steps if step.strip()]
                else:
                    # Try bullet points or new lines
                    instruction_steps = re.findall(r'[-•*]?\s*([^•*\n]+)', instructions_section)
                    instructions = [step.strip() for step in instruction_steps if step.strip()]
            
            # Check if we have minimum required recipe components
            if ingredients or instructions:
                # Create recipe data structure
                recipe_data = {
                    "title": title,
                    "description": "",
                    "ingredients": ingredients,
                    "instructions": instructions,
                    "prep_time": "",
                    "cook_time": "",
                    "total_time": "",
                    "servings": "",
                    "dietary_info": [],
                    "difficulty": self._estimate_difficulty(ingredients, instructions)
                }
                
                # Try to extract prep time
                prep_time_match = re.search(r'(?:Prep Time|PREP TIME|prep time)[:\s]+([\d\s]+(?:min|minute|hour|hr)[s]?)', text)
                if prep_time_match:
                    recipe_data["prep_time"] = prep_time_match.group(1).strip()
                
                # Try to extract cook time
                cook_time_match = re.search(r'(?:Cook Time|COOK TIME|cook time)[:\s]+([\d\s]+(?:min|minute|hour|hr)[s]?)', text)
                if cook_time_match:
                    recipe_data["cook_time"] = cook_time_match.group(1).strip()
                
                # Try to extract total time
                total_time_match = re.search(r'(?:Total Time|TOTAL TIME|total time)[:\s]+([\d\s]+(?:min|minute|hour|hr)[s]?)', text)
                if total_time_match:
                    recipe_data["total_time"] = total_time_match.group(1).strip()
                
                # Try to extract servings
                servings_match = re.search(r'(?:Servings|SERVINGS|servings|Serves|serves)[:\s]+([\d\-\s]+)', text)
                if servings_match:
                    recipe_data["servings"] = servings_match.group(1).strip()
                
                # Try to identify dietary info
                dietary_terms = ['vegan', 'vegetarian', 'gluten-free', 'dairy-free', 
                                'low-carb', 'keto', 'paleo', 'nut-free', 'sugar-free']
                recipe_data["dietary_info"] = [term for term in dietary_terms if re.search(rf'\b{term}\b', text, re.IGNORECASE)]
                
                logger.info(f"Successfully extracted recipe using regex: {title}")
                return recipe_data
            else:
                logger.warning("Couldn't extract enough recipe components with regex")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract recipe with regex: {str(e)}")
            return None
    
    def _estimate_difficulty(self, ingredients, instructions) -> str:
        """
        Estimate recipe difficulty based on number of ingredients and steps
        
        Args:
            ingredients: List of ingredients
            instructions: List of instruction steps
            
        Returns:
            str: Difficulty level ('easy', 'medium', or 'hard')
        """
        num_ingredients = len(ingredients)
        num_steps = len(instructions)
        
        # Simple heuristic
        if num_ingredients <= 5 and num_steps <= 5:
            return "easy"
        elif num_ingredients > 12 or num_steps > 12:
            return "hard"
        else:
            return "medium"
        
    def extract_recipe_from_url(self, url):
        """
        Extract recipe from a website URL
        
        Args:
            url (str): URL of the recipe website
            
        Returns:
            dict: Structured recipe data or None if extraction fails
        """
        try:
            logger.info(f"Extracting recipe from URL: {url}")
            
            # Use requests to get the page content
            import requests
            from bs4 import BeautifulSoup
            
            # Random user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for structured recipe data (JSON-LD)
            recipe_data = None
            for script in soup.find_all('script', {'type': 'application/ld+json'}):
                try:
                    json_data = json.loads(script.string)
                    
                    # Check if it's a recipe
                    if isinstance(json_data, dict) and '@type' in json_data:
                        if json_data['@type'] == 'Recipe':
                            recipe_data = json_data
                            break
                    
                    # Check for graph structure
                    if isinstance(json_data, dict) and '@graph' in json_data:
                        for item in json_data['@graph']:
                            if isinstance(item, dict) and '@type' in item and item['@type'] == 'Recipe':
                                recipe_data = item
                                break
                except:
                    continue
            
            # If we found structured recipe data
            if recipe_data:
                # Extract recipe components
                title = recipe_data.get('name', 'Untitled Recipe')
                description = recipe_data.get('description', '')
                
                # Extract ingredients
                ingredients = []
                raw_ingredients = recipe_data.get('recipeIngredient', [])
                if isinstance(raw_ingredients, list):
                    for ingredient in raw_ingredients:
                        # Try to parse the ingredient
                        parts = self._parse_ingredient(ingredient)
                        ingredients.append(parts)
                
                # Extract instructions
                instructions = []
                raw_instructions = recipe_data.get('recipeInstructions', [])
                if isinstance(raw_instructions, list):
                    for instruction in raw_instructions:
                        if isinstance(instruction, dict) and 'text' in instruction:
                            instructions.append(instruction['text'])
                        elif isinstance(instruction, str):
                            instructions.append(instruction)
                
                # Extract times
                prep_time = self._extract_time(recipe_data.get('prepTime', ''))
                cook_time = self._extract_time(recipe_data.get('cookTime', ''))
                total_time = self._extract_time(recipe_data.get('totalTime', ''))
                
                # Extract yield/servings
                servings = ''
                recipe_yield = recipe_data.get('recipeYield', '')
                if isinstance(recipe_yield, list) and len(recipe_yield) > 0:
                    servings = recipe_yield[0]
                elif isinstance(recipe_yield, str):
                    servings = recipe_yield
                
                # Construct recipe data
                structured_recipe = {
                    'title': title,
                    'description': description,
                    'ingredients': ingredients,
                    'instructions': instructions,
                    'prep_time': prep_time,
                    'cook_time': cook_time,
                    'total_time': total_time,
                    'servings': servings,
                    'dietary_info': [],
                    'difficulty': self._estimate_difficulty(ingredients, instructions),
                    'source': {
                        'platform': 'Website',
                        'url': url
                    }
                }
                
                logger.info(f"Successfully extracted recipe from URL: {title}")
                return structured_recipe
            
            # If no structured data, try to extract recipe from HTML
            return self._extract_recipe_from_html(soup, url)
            
        except Exception as e:
            logger.error(f"Failed to extract recipe from URL: {str(e)}")
            return None

    def _parse_ingredient(self, ingredient_text):
        """
        Parse an ingredient string into components
        
        Args:
            ingredient_text (str): Raw ingredient text
            
        Returns:
            dict: Parsed ingredient with quantity, unit, and name
        """
        # Simple regex parsing
        import re
        
        # Try to match quantity, unit, and name
        match = re.match(r'([\d\s./]+)?\s*([a-zA-Z]+)?\s*(.*)', ingredient_text.strip())
        
        if match:
            quantity, unit, name = match.groups()
            return {
                'quantity': quantity.strip() if quantity else '',
                'unit': unit.strip() if unit else '',
                'name': name.strip()
            }
        else:
            # If no match, just return the text as the name
            return {
                'quantity': '',
                'unit': '',
                'name': ingredient_text.strip()
            }

    def _extract_time(self, time_string):
        """
        Extract time from ISO duration format
        
        Args:
            time_string (str): ISO duration string
            
        Returns:
            str: Formatted time string
        """
        if not time_string:
            return ''
        
        # Handle ISO duration format like PT1H30M
        if time_string.startswith('PT'):
            import re
            
            hours = re.search(r'(\d+)H', time_string)
            minutes = re.search(r'(\d+)M', time_string)
            
            if hours and minutes:
                return f"{hours.group(1)} hr {minutes.group(1)} min"
            elif hours:
                return f"{hours.group(1)} hr"
            elif minutes:
                return f"{minutes.group(1)} min"
        
        return time_string

    def _extract_recipe_from_html(self, soup, url):
        """
        Extract recipe from HTML when no structured data is available
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            url (str): Source URL
            
        Returns:
            dict: Structured recipe data or None if extraction fails
        """
        # Extract title (common patterns)
        title_candidates = [
            soup.find('h1'),
            soup.find('h2', class_=lambda c: c and ('recipe' in c.lower() if c else False)),
            soup.find('div', class_=lambda c: c and ('recipe-title' in c.lower() if c else False))
        ]
        
        title = ''
        for candidate in title_candidates:
            if candidate and candidate.text.strip():
                title = candidate.text.strip()
                break
        
        if not title:
            title = 'Recipe from ' + url.split('/')[2]  # Use domain as fallback
        
        # Find ingredient lists
        ingredients = []
        ingredient_containers = [
            soup.find('ul', class_=lambda c: c and ('ingredient' in c.lower() if c else False)),
            soup.find('div', class_=lambda c: c and ('ingredient' in c.lower() if c else False))
        ]
        
        for container in ingredient_containers:
            if container:
                ingredient_items = container.find_all('li')
                if not ingredient_items:
                    ingredient_items = container.find_all(['p', 'div'])
                
                for item in ingredient_items:
                    text = item.text.strip()
                    if text and len(text) > 2:  # Skip empty or very short items
                        ingredients.append(self._parse_ingredient(text))
        
        # Find instructions
        instructions = []
        instruction_containers = [
            soup.find('ol', class_=lambda c: c and ('instruction' in c.lower() if c else False)),
            soup.find('div', class_=lambda c: c and ('instruction' in c.lower() if c else False))
        ]
        
        for container in instruction_containers:
            if container:
                instruction_items = container.find_all('li')
                if not instruction_items:
                    instruction_items = container.find_all(['p', 'div'])
                
                for item in instruction_items:
                    text = item.text.strip()
                    if text and len(text) > 10:  # Skip very short instructions
                        instructions.append(text)
        
        # If we couldn't find proper ingredients or instructions
        if not ingredients and not instructions:
            logger.warning(f"Couldn't extract recipe components from HTML: {url}")
            return None
        
        # Construct recipe data
        recipe = {
            'title': title,
            'description': '',
            'ingredients': ingredients,
            'instructions': instructions,
            'prep_time': '',
            'cook_time': '',
            'total_time': '',
            'servings': '',
            'dietary_info': [],
            'difficulty': self._estimate_difficulty(ingredients, instructions),
            'source': {
                'platform': 'Website',
                'url': url
            }
        }
        
        logger.info(f"Extracted recipe from HTML: {title}")
        return recipe

    def _estimate_difficulty(self, ingredients, instructions):
        """
        Estimate recipe difficulty based on ingredients and instructions
        
        Args:
            ingredients (list): Recipe ingredients
            instructions (list): Recipe instructions
            
        Returns:
            str: Difficulty level (easy, medium, hard)
        """
        ingredient_count = len(ingredients)
        instruction_count = len(instructions)
        
        instruction_length = sum(len(instruction) for instruction in instructions) if instructions else 0
        avg_instruction_length = instruction_length / instruction_count if instruction_count > 0 else 0
        
        if ingredient_count <= 5 and instruction_count <= 3:
            return "easy"
        elif ingredient_count >= 12 or instruction_count >= 10 or avg_instruction_length > 200:
            return "hard"
        else:
            return "medium"
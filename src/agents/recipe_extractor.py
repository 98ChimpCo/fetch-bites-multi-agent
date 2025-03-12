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
    
    def extract_recipe(self, text: str) -> Optional[Dict]:
        """
        Extract structured recipe data from text
        
        Args:
            text (str): Text to extract recipe from
            
        Returns:
            dict: Structured recipe data or None if extraction fails
        """
        try:
            logger.info("Extracting recipe from text...")
            
            # Check if text is too short to be a recipe
            if len(text.split()) < 20:
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
                model="claude-3-sonnet-20240229",
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
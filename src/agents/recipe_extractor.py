# src/agents/recipe_extractor.py
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class RecipeExtractorAgent:
    """Agent for extracting structured recipe data from Instagram post content"""
    
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.processed_count = 0
        self.last_processed = None
        self._load_stats()
    
    def _load_stats(self):
        """Load processing statistics"""
        try:
            if os.path.exists("data/processed/extractor_stats.json"):
                with open("data/processed/extractor_stats.json", "r") as f:
                    stats = json.load(f)
                    self.processed_count = stats.get("processed_count", 0)
                    self.last_processed = stats.get("last_processed")
        except Exception as e:
            logger.error(f"Error loading extractor stats: {str(e)}")
    
    def _save_stats(self):
        """Save processing statistics"""
        try:
            os.makedirs("data/processed", exist_ok=True)
            with open("data/processed/extractor_stats.json", "w") as f:
                stats = {
                    "processed_count": self.processed_count,
                    "last_processed": self.last_processed
                }
                json.dump(stats, f)
        except Exception as e:
            logger.error(f"Error saving extractor stats: {str(e)}")
    
    async def extract_recipe(self, post_content: Dict) -> Dict:
        """Extract structured recipe data from Instagram post content"""
        try:
            caption = post_content.get("caption", "")
            hashtags = post_content.get("hashtags", [])
            post_url = post_content.get("url", "")
            
            # Skip if caption is too short
            if len(caption) < 50:
                logger.warning(f"Caption too short to extract recipe from {post_url}")
                return {}
            
            # Prepare prompt for Claude
            prompt = self._create_extraction_prompt(caption, hashtags)
            
            # Extract recipe data using Claude
            response = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0,
                system="""You are a recipe extraction specialist. Extract structured recipe data from Instagram captions.
                For ingredients, always include quantity, unit, and name as separate fields when possible.
                For instructions, break them into clear, numbered steps.
                Format the response as a valid JSON object.""",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            recipe_json_text = response.content[0].text
            
            # Extract JSON from the response
            recipe_json_text = self._extract_json_from_text(recipe_json_text)
            
            # Parse the extracted JSON
            recipe_data = json.loads(recipe_json_text)
            
            # Add metadata
            recipe_data["source"] = {
                "platform": "Instagram",
                "url": post_url,
                "extraction_date": datetime.now().isoformat()
            }
            
            # Add thumbnail if available
            if "media_url" in post_content and post_content["media_url"]:
                recipe_data["thumbnail_url"] = post_content["media_url"]
            
            # Save processed recipe data
            self._save_recipe_data(post_url, recipe_data)
            
            # Update stats
            self.processed_count += 1
            self.last_processed = datetime.now().isoformat()
            self._save_stats()
            
            logger.info(f"Successfully extracted recipe from {post_url}")
            return recipe_data
        except Exception as e:
            logger.error(f"Error extracting recipe: {str(e)}")
            return {}
    
    def _create_extraction_prompt(self, caption: str, hashtags: List[str]) -> str:
        """Create a prompt for recipe extraction"""
        hashtags_text = ", ".join(hashtags) if hashtags else "None"
        
        prompt = f"""
        Extract a complete recipe from this Instagram post caption.
        
        CAPTION:
        {caption}
        
        HASHTAGS:
        {hashtags_text}
        
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
        
        return prompt
    
    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON object from text response"""
        # Look for JSON between curly braces
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        
        if start_idx >= 0 and end_idx >= 0:
            return text[start_idx:end_idx+1]
        
        # If no JSON found, return empty object
        return "{}"
    
    def _save_recipe_data(self, post_url: str, recipe_data: Dict):
        """Save processed recipe data to disk"""
        try:
            os.makedirs("data/processed/recipes", exist_ok=True)
            
            # Create a filename from the post URL
            post_id = post_url.split("/")[-2]
            filename = f"data/processed/recipes/{post_id}.json"
            
            with open(filename, "w") as f:
                json.dump(recipe_data, f, indent=2)
                
            logger.info(f"Saved recipe data to {filename}")
        except Exception as e:
            logger.error(f"Error saving recipe data: {str(e)}")
    
    def get_processed_count(self) -> int:
        """Get the number of recipes processed"""
        return self.processed_count

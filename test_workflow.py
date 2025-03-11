# test_workflow.py
import asyncio
import os
import json
from src.config.settings import settings
from src.agents.instagram_monitor import InstagramMonitorAgent
from src.agents.recipe_extractor import RecipeExtractorAgent

async def test_single_post():
    # Initialize agents
    monitor = InstagramMonitorAgent()
    extractor = RecipeExtractorAgent()
    
    # Test URL - replace with a known recipe post
    test_url = "https://www.instagram.com/p/DGYqcZ4vspg/"  # Replace with a real post ID
    
    # Login to Instagram
    print("Logging in to Instagram...")
    login_success = await monitor.login_to_instagram()
    if not login_success:
        print("Failed to log in to Instagram")
        return
    
    # Extract content from Instagram
    print(f"Extracting content from {test_url}...")
    post_content = await monitor.extract_post_content(test_url)
    
    if not post_content:
        print("Failed to extract post content")
        return
    
    print("Post content extracted successfully")
    print(f"Caption: {post_content.get('caption', '')[:100]}...")
    
    # Extract recipe from content
    print("Extracting recipe data...")
    recipe_data = await extractor.extract_recipe(post_content)
    
    if not recipe_data:
        print("Failed to extract recipe data")
        return
    
    print("Recipe extracted successfully:")
    print(f"Title: {recipe_data.get('title', 'No title')}")
    print(f"Ingredients: {len(recipe_data.get('ingredients', []))} items")
    print(f"Instructions: {len(recipe_data.get('instructions', []))} steps")
    
    # Save the results for inspection
    print("Saving results to test_output.json...")
    os.makedirs("data/test", exist_ok=True)
    with open("data/test/test_output.json", "w") as f:
        json.dump(recipe_data, f, indent=2)
    
    print("Test completed successfully")

if __name__ == "__main__":
    asyncio.run(test_single_post())
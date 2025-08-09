#!/usr/bin/env python3
"""
Test script to generate V2 PDF from cached recipe data
"""

import os
import sys
from src.agents.pdf_generator import PDFGenerator

# Sample recipe data based on the Beef Ho Fun recipe we processed
recipe_data = {
    'title': 'Truffle Risotto with Wild Mushrooms',
    'description': 'A luxurious and creamy risotto elevated with truffle oil and seasonal wild mushrooms. Perfect for special occasions.',
    'prep_time': '15 min',
    'cook_time': '25 min', 
    'servings': '4',
    'views': '2.4K',
    'ingredients': [
        {'quantity': '1½', 'unit': 'cups', 'name': 'Arborio rice'},
        {'quantity': '4', 'unit': 'cups', 'name': 'warm chicken or vegetable stock'},
        {'quantity': '½', 'unit': 'cup', 'name': 'dry white wine'},
        {'quantity': '1', 'unit': 'large', 'name': 'shallot, finely diced'},
        {'quantity': '3', 'unit': 'cloves', 'name': 'garlic, minced'},
        {'quantity': '8', 'unit': 'oz', 'name': 'mixed wild mushrooms (porcini, shiitake, oyster)'},
        {'quantity': '3', 'unit': 'tbsp', 'name': 'truffle oil'},
        {'quantity': '½', 'unit': 'cup', 'name': 'grated Parmigiano-Reggiano'},
        {'quantity': '3', 'unit': 'tbsp', 'name': 'unsalted butter'},
        {'quantity': '2', 'unit': 'tbsp', 'name': 'olive oil'},
        {'quantity': '', 'unit': '', 'name': 'Salt and white pepper to taste'},
        {'quantity': '', 'unit': '', 'name': 'Fresh chives for garnish'}
    ],
    'instructions': [
        'Heat olive oil in a heavy-bottomed pan over medium heat. Sauté shallots until translucent, about 3 minutes.',
        'Add garlic and cook for another minute until fragrant.',
        'Add Arborio rice, stirring constantly for 2 minutes until lightly toasted.',
        'Pour in white wine and stir until absorbed.',
        'Add warm stock one ladle at a time, stirring continuously until each addition is absorbed before adding the next.',
        'In a separate pan, sauté wild mushrooms with butter until golden and tender.',
        'Continue adding stock and stirring for 18-20 minutes until rice is creamy and al dente.',
        'Fold in sautéed mushrooms, truffle oil, and Parmigiano-Reggiano.',
        'Season with salt and white pepper. Garnish with fresh chives and serve immediately.'
    ],
    'notes': 'For best results, use high-quality truffle oil and freshly grated cheese. The key to perfect risotto is patience and constant stirring.',
    'source': {
        'platform': 'Instagram',
        'url': 'https://instagram.com/p/DIyViWet1IQ/',
        'creator': 'Marco Antonelli',
        'instagram_handle': 'chef_marco'
    }
}

def test_v2_pdf():
    """Test the V2 PDF generation with sample data"""
    print("Testing V2 PDF generation...")
    
    # Set environment variable to use V2 template
    os.environ['LAYOUT_VERSION'] = 'v2'
    
    # Initialize PDF generator
    pdf_gen = PDFGenerator()
    
    # Use the template image as sample (you can replace with actual extracted image)
    sample_image_path = "recipe-card-v2-template.png"  # The template image you showed me
    
    # Generate PDF
    pdf_path, is_cached = pdf_gen.generate_pdf(
        recipe_data, 
        image_path=sample_image_path if os.path.exists(sample_image_path) else None,
        post_url="https://instagram.com/p/DIyViWet1IQ/"
    )
    
    if pdf_path:
        print(f"✅ V2 PDF generated successfully: {pdf_path}")
        print(f"📁 Check the file: {os.path.abspath(pdf_path)}")
        return True
    else:
        print("❌ Failed to generate V2 PDF")
        return False

if __name__ == "__main__":
    success = test_v2_pdf()
    sys.exit(0 if success else 1)
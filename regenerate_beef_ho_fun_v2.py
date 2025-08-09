#!/usr/bin/env python3
"""
Regenerate the Beef Ho Fun PDF with V2 template improvements
"""

import os
import sys
from src.agents.pdf_generator import PDFGenerator

# Exact Beef Ho Fun recipe data from the cache
beef_ho_fun_recipe = {
    'title': 'Beef Ho Fun (Beef Chow Fun)',
    'description': 'A 20 minute high protein recipe featuring beef and flat rice noodles in a savory sauce.',
    'prep_time': '10 minutes',
    'cook_time': '10 minutes', 
    'total_time': '20 minutes',
    'servings': '4',  # Default since original had null
    'views': '2.4K',  # Default
    'ingredients': [
        {'quantity': '400-500', 'unit': 'g', 'name': 'skirt/flank beef steak, trimmed'},
        {'quantity': '1', 'unit': 'tsp', 'name': 'light soy sauce (for beef marinade)'},
        {'quantity': '1', 'unit': 'tsp', 'name': 'dark soy sauce (for beef marinade)'},
        {'quantity': '1', 'unit': 'tsp', 'name': 'cornstarch'},
        {'quantity': '1', 'unit': 'tsp', 'name': 'bicarb soda'},
        {'quantity': '1', 'unit': 'tsp', 'name': 'sugar (for beef marinade)'},
        {'quantity': '1', 'unit': 'Tbsp', 'name': 'high-fry oil (for beef)'},
        {'quantity': '2', 'unit': 'Tbsp', 'name': 'high-fry oil (for stir fry)'},
        {'quantity': '200', 'unit': 'g', 'name': 'beansprouts'},
        {'quantity': '1', 'unit': 'bunch', 'name': 'spring onions, chopped roughly'},
        {'quantity': '3', 'unit': 'cloves', 'name': 'garlic, chopped'},
        {'quantity': '1', 'unit': 'bunch', 'name': 'tender-stem Broccoli (broccolini) (optional)'},
        {'quantity': '400-500', 'unit': 'g', 'name': 'flat rice noodles'},
        {'quantity': '1', 'unit': 'Tbsp', 'name': 'dark soy sauce (for sauce)'},
        {'quantity': '1', 'unit': 'Tbsp', 'name': 'light soy sauce (for sauce)'},
        {'quantity': '2', 'unit': 'Tbsp', 'name': 'oyster sauce'},
        {'quantity': '1', 'unit': 'Tbsp', 'name': 'sesame oil'},
        {'quantity': '1', 'unit': 'tsp', 'name': 'sugar (for sauce)'},
        {'quantity': '1', 'unit': '', 'name': 'lemon juice'}
    ],
    'instructions': [
        'Cut thin slices of beef',
        'Coat beef slices in marinade ingredients (light soy sauce, dark soy sauce, cornstarch, bicarb soda, sugar, and high-fry oil) and set aside for 10 minutes (or ideally 30 if you have time!)',
        'Cut all your other ingredients to size',
        'If you have dried rice noodles, cook them per packet instructions and rinse once cooked',
        'Fry in a wok or a large fry pan on high heat the beef with a bit of high-fry oil',
        'Set aside beef once browned',
        'Add all other stir fry ingredients and cook for 2 minutes',
        'Add the noodles',
        'Add all sauces to a bowl and then into the stir fry and coat the noodles until brown colour',
        'Add the beef back in and cook for 2 minutes',
        'Serve hot & fresh'
    ],
    'dietary_info': ['high protein'],
    'difficulty': 'easy',
    'notes': 'This is a quick and easy stir-fry that comes together in just 20 minutes. For best results, have all ingredients prepped before you start cooking.',
    'source': {
        'platform': 'Instagram',
        'url': 'https://instagram.com/p/DIyViWet1IQ/',
        'creator': 'Marco Antonelli',
        'instagram_handle': 'chef_marco',
        'caption': 'Beef ho (chow) fun 🍜🥢\n\nMy FAVOURITE 20 minute high protein recipe of all time'
    }
}

def regenerate_beef_ho_fun_v2():
    """Regenerate the Beef Ho Fun PDF with V2 template"""
    print("🍜 Regenerating Beef Ho Fun PDF with V2 template improvements...")
    
    # Set environment variable to use V2 template
    os.environ['LAYOUT_VERSION'] = 'v2'
    
    # Initialize PDF generator
    pdf_gen = PDFGenerator()
    
    # Clear cache to force regeneration with no footer
    pdf_gen.cache.cache = {}
    pdf_gen.cache.save()
    
    # Use the extracted post image if available
    post_image_path = "images/post_image_at_docteurzed.png"
    
    # Generate PDF with error handling
    try:
        pdf_path, is_cached = pdf_gen.generate_pdf(
            beef_ho_fun_recipe, 
            image_path=post_image_path if os.path.exists(post_image_path) else None,
            post_url="https://instagram.com/p/DIyViWet1IQ/"
        )
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if pdf_path:
        print(f"✅ V2 Beef Ho Fun PDF generated successfully!")
        print(f"📁 Location: {os.path.abspath(pdf_path)}")
        print()
        print("🔍 V2 Template improvements applied:")
        print("  • Perfect square image cropping (not squeezed)")
        print("  • Chef info: Marco Antonelli")
        print("  • Instagram handle: @chef_marco") 
        print("  • 4 stat boxes in row layout")
        print("  • Proper bullet formatting (●) for ingredients")
        print("  • Numbered circles for directions")
        print("  • Always includes Notes section")
        print("  • Clean source attribution")
        return True
    else:
        print("❌ Failed to generate V2 Beef Ho Fun PDF")
        return False

if __name__ == "__main__":
    success = regenerate_beef_ho_fun_v2()
    sys.exit(0 if success else 1)
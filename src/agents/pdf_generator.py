# src/agents/pdf_generator.py
import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from fpdf import FPDF
import tempfile
import requests
from urllib.parse import urlparse
from PIL import Image
import io

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handler if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class PDFGenerator:
    """
    PDF Generator Agent for creating recipe PDF cards
    """
    
    def __init__(self, output_dir='pdfs'):
        """
        Initialize PDF Generator Agent
        
        Args:
            output_dir (str): Directory to save PDFs
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Define design settings
        self.text_color = (51, 51, 51)  # Dark gray
        self.accent_color = (235, 87, 87)  # Coral red
        self.bg_color = (255, 255, 255)  # White
        self.font_family = 'Helvetica'
    
    def generate_pdf(self, recipe_data: Dict) -> str:
        """
        Generate a PDF recipe card
        
        Args:
            recipe_data (dict): Structured recipe data
            
        Returns:
            str: Path to generated PDF file
        """
        try:
            logger.info(f"Generating PDF for recipe: {recipe_data.get('title', 'Untitled Recipe')}")
            
            # Create PDF object
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Add a page
            pdf.add_page()
            
            # Set font
            pdf.set_font(self.font_family, '', 12)
            pdf.set_text_color(*self.text_color)
            
            # Add title
            pdf.set_font(self.font_family, 'B', 24)
            pdf.set_text_color(*self.accent_color)
            title = recipe_data.get('title', 'Untitled Recipe')
            pdf.cell(0, 15, title, ln=True, align='C')
            pdf.ln(5)
            
            # Add description if available
            description = recipe_data.get('description')
            if description:
                pdf.set_font(self.font_family, 'I', 12)
                pdf.set_text_color(*self.text_color)
                pdf.multi_cell(0, 6, description)
                pdf.ln(5)
            
            # Add recipe image if available
            image_urls = recipe_data.get('image_urls', [])
            if image_urls and len(image_urls) > 0:
                try:
                    image_url = image_urls[0]
                    self._add_image_from_url(pdf, image_url)
                    pdf.ln(5)
                except Exception as e:
                    logger.warning(f"Failed to add image to PDF: {str(e)}")
            
            # Add recipe info section
            self._add_recipe_info(pdf, recipe_data)
            pdf.ln(10)
            
            # Add ingredients section
            pdf.set_font(self.font_family, 'B', 16)
            pdf.set_text_color(*self.accent_color)
            pdf.cell(0, 10, 'Ingredients', ln=True)
            pdf.ln(2)
            
            ingredients = recipe_data.get('ingredients', [])
            if ingredients:
                self._add_ingredients(pdf, ingredients)
            else:
                pdf.set_font(self.font_family, '', 12)
                pdf.set_text_color(*self.text_color)
                pdf.cell(0, 10, 'No ingredients listed', ln=True)
            
            pdf.ln(10)
            
            # Add instructions section
            pdf.set_font(self.font_family, 'B', 16)
            pdf.set_text_color(*self.accent_color)
            pdf.cell(0, 10, 'Instructions', ln=True)
            pdf.ln(2)
            
            instructions = recipe_data.get('instructions', [])
            if instructions:
                self._add_instructions(pdf, instructions)
            else:
                pdf.set_font(self.font_family, '', 12)
                pdf.set_text_color(*self.text_color)
                pdf.cell(0, 10, 'No instructions listed', ln=True)
            
            # Add footer with source
            self._add_footer(pdf, recipe_data)
            
            # Save the PDF
            filename = self._get_filename(recipe_data)
            filepath = os.path.join(self.output_dir, filename)
            pdf.output(filepath)
            
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            return None
    
    def _add_image_from_url(self, pdf, image_url):
        """
        Add an image from URL to the PDF
        
        Args:
            pdf (FPDF): PDF object
            image_url (str): URL of the image
        """
        try:
            # Download image
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            # Create temporary file for the image
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                # Save image to temporary file
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            # Resize image if needed
            try:
                # Open the image
                image = Image.open(temp_file_path)
                
                # Get original dimensions
                width, height = image.size
                
                # Calculate new dimensions to fit PDF width (180mm) while maintaining aspect ratio
                max_width = 180
                new_width = min(width, max_width)
                new_height = int(height * (new_width / width))
                
                # Resize image
                resized_image = image.resize((new_width * 3, new_height * 3))  # × 3 for better quality
                
                # Save resized image
                resized_image.save(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to resize image: {str(e)}")
            
            # Add image to PDF
            pdf.image(temp_file_path, x=10, w=190)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
        except Exception as e:
            logger.warning(f"Failed to add image from URL: {str(e)}")
    
    def _add_recipe_info(self, pdf, recipe_data):
        """
        Add recipe information (prep time, servings, etc.)
        
        Args:
            pdf (FPDF): PDF object
            recipe_data (dict): Recipe data
        """
        pdf.set_font(self.font_family, 'B', 12)
        pdf.set_text_color(*self.text_color)
        
        # Create info grid
        info_items = []
        
        if recipe_data.get('prep_time'):
            info_items.append(('Prep Time', recipe_data['prep_time']))
        
        if recipe_data.get('cook_time'):
            info_items.append(('Cook Time', recipe_data['cook_time']))
        
        if recipe_data.get('total_time'):
            info_items.append(('Total Time', recipe_data['total_time']))
        
        if recipe_data.get('servings'):
            info_items.append(('Servings', recipe_data['servings']))
        
        if recipe_data.get('difficulty'):
            info_items.append(('Difficulty', recipe_data['difficulty'].capitalize()))
        
        # Display dietary info if available
        dietary_info = recipe_data.get('dietary_info', [])
        if dietary_info:
            info_items.append(('Dietary', ', '.join(dietary_info)))
        
        # Draw info grid (2 columns)
        if info_items:
            # Calculate column width
            col_width = 95
            
            # Create rows
            for i in range(0, len(info_items), 2):
                # First item
                pdf.set_font(self.font_family, 'B', 10)
                pdf.cell(30, 6, info_items[i][0] + ':', 0)
                
                pdf.set_font(self.font_family, '', 10)
                pdf.cell(col_width - 30, 6, info_items[i][1], 0)
                
                # Second item (if available)
                if i + 1 < len(info_items):
                    pdf.set_font(self.font_family, 'B', 10)
                    pdf.cell(30, 6, info_items[i + 1][0] + ':', 0)
                    
                    pdf.set_font(self.font_family, '', 10)
                    pdf.cell(col_width - 30, 6, info_items[i + 1][1], 0)
                
                pdf.ln(6)
    
    def _add_ingredients(self, pdf, ingredients):
        """
        Add ingredients list to PDF
        
        Args:
            pdf (FPDF): PDF object
            ingredients (list): List of ingredients
        """
        pdf.set_font(self.font_family, '', 12)
        pdf.set_text_color(*self.text_color)
        
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                # Extract ingredient components
                quantity = ingredient.get('quantity', '')
                unit = ingredient.get('unit', '')
                name = ingredient.get('name', '')
                
                # Format ingredient text
                if quantity and unit:
                    ingredient_text = f"• {quantity} {unit} {name}"
                elif quantity:
                    ingredient_text = f"• {quantity} {name}"
                else:
                    ingredient_text = f"• {name}"
            else:
                # Handle string ingredients
                ingredient_text = f"• {ingredient}"
            
            # Add to PDF
            pdf.multi_cell(0, 6, ingredient_text)
    
    def _add_instructions(self, pdf, instructions):
        """
        Add instructions to PDF
        
        Args:
            pdf (FPDF): PDF object
            instructions (list): List of instruction steps
        """
        pdf.set_font(self.font_family, '', 12)
        pdf.set_text_color(*self.text_color)
        
        for i, step in enumerate(instructions, 1):
            # Format step number
            pdf.set_font(self.font_family, 'B', 12)
            step_number = f"{i}. "
            pdf.cell(10, 6, step_number)
            
            # Format step text
            pdf.set_font(self.font_family, '', 12)
            # Account for step number width
            pdf.multi_cell(0, 6, step)
            pdf.ln(2)
    
    def _add_footer(self, pdf, recipe_data):
        """
        Add footer with source information
        
        Args:
            pdf (FPDF): PDF object
            recipe_data (dict): Recipe data
        """
        # Move to bottom of page
        pdf.set_y(-30)
        
        # Add source information
        pdf.set_font(self.font_family, 'I', 9)
        pdf.set_text_color(128, 128, 128)  # Gray
        
        # Get source information
        source = recipe_data.get('source', {})
        platform = source.get('platform', 'Unknown')
        url = source.get('url', '')
        
        if platform and url:
            source_text = f"Source: {platform} - {url}"
        elif platform:
            source_text = f"Source: {platform}"
        else:
            source_text = "Generated by Fetch Bites"
        
        pdf.cell(0, 5, source_text, 0, 1, 'C')
        
        # Add generation timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 5, f"Generated on {timestamp}", 0, 1, 'C')
    
    def _get_filename(self, recipe_data):
        """
        Generate a filename for the PDF
        
        Args:
            recipe_data (dict): Recipe data
            
        Returns:
            str: Filename
        """
        # Clean title for filename
        title = recipe_data.get('title', 'Untitled Recipe')
        clean_title = ''.join(c if c.isalnum() or c.isspace() else '_' for c in title)
        clean_title = clean_title.replace(' ', '_')
        
        # Add timestamp to ensure uniqueness
        timestamp = int(time.time())
        
        return f"{clean_title}_{timestamp}.pdf"
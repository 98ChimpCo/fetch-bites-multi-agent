# src/agents/pdf_generator.py
import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import tempfile
import requests
from io import BytesIO
from PIL import Image

# Use ReportLab instead of FPDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage, TableStyle

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
    PDF Generator Agent for creating recipe PDF cards using ReportLab
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
        
        # Define colors and styles
        self.accent_color = colors.HexColor('#EB5757')  # Coral red
        self.text_color = colors.HexColor('#333333')    # Dark gray
        
        # Page width (in points - 595.27 for A4)
        self.page_width = A4[0]
        
        # Initialize styles
        self.styles = getSampleStyleSheet()
        
        # Create custom styles
        self.styles.add(ParagraphStyle(
            name='RecipeTitle',
            fontName='Helvetica-Bold',
            fontSize=18,
            alignment=1,  # Center alignment
            textColor=self.accent_color,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=self.accent_color,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='IngredientItem',
            fontName='Helvetica',
            fontSize=10,
            leftIndent=20,
            firstLineIndent=-15,  # Hanging indent for bullet
            spaceAfter=3
        ))
        
        self.styles.add(ParagraphStyle(
            name='InstructionItem',
            fontName='Helvetica',
            fontSize=10,
            leftIndent=20,
            firstLineIndent=-15,  # Hanging indent for numbering
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            fontName='Helvetica-Oblique',
            fontSize=8,
            textColor=colors.gray,
            alignment=1  # Center alignment
        ))
    
    def generate_pdf(self, recipe_data: Dict) -> str:
        """
        Generate a PDF recipe card using ReportLab
        
        Args:
            recipe_data (dict): Structured recipe data
            
        Returns:
            str: Path to generated PDF file
        """
        try:
            logger.info(f"Generating PDF for recipe: {recipe_data.get('title', 'Untitled Recipe')}")
            
            # Create a filename for the PDF
            filename = self._get_filename(recipe_data)
            filepath = os.path.join(self.output_dir, filename)
            
            # Create a PDF document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # Content elements
            elements = []
            
            # Add title
            title = recipe_data.get('title', 'Untitled Recipe')
            elements.append(Paragraph(title, self.styles['RecipeTitle']))
            elements.append(Spacer(1, 12))
            
            # Add description if available
            description = recipe_data.get('description')
            if description:
                elements.append(Paragraph(description, self.styles['Normal']))
                elements.append(Spacer(1, 12))
            
            # Add recipe info (prep time, cook time, etc.)
            info_elements = self._create_recipe_info(recipe_data, doc.width)
            if info_elements:
                elements.extend(info_elements)
                elements.append(Spacer(1, 12))
            
            # Add ingredients section
            elements.append(Paragraph('Ingredients', self.styles['SectionTitle']))
            elements.append(Spacer(1, 6))
            
            ingredients = recipe_data.get('ingredients', [])
            if ingredients:
                ingredient_elements = self._create_ingredients_list(ingredients)
                elements.extend(ingredient_elements)
            else:
                elements.append(Paragraph('No ingredients listed', self.styles['Normal']))
            
            elements.append(Spacer(1, 12))
            
            # Add instructions section
            elements.append(Paragraph('Instructions', self.styles['SectionTitle']))
            elements.append(Spacer(1, 6))
            
            instructions = recipe_data.get('instructions', [])
            if instructions:
                instruction_elements = self._create_instructions_list(instructions)
                elements.extend(instruction_elements)
            else:
                elements.append(Paragraph('No instructions listed', self.styles['Normal']))
            
            elements.append(Spacer(1, 20))
            
            # Add footer
            footer_elements = self._create_footer(recipe_data)
            elements.extend(footer_elements)
            
            # Build the PDF
            doc.build(elements)
            
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            return None
    
    def _create_recipe_info(self, recipe_data, page_width):
        """
        Create recipe info section with prep time, cook time, etc.
        
        Args:
            recipe_data (dict): Recipe data
            page_width (float): Width of the page
            
        Returns:
            list: Elements for recipe info section
        """
        elements = []
        
        # Collect info items
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
        
        if not info_items:
            return elements
        
        # Create a table for the info section
        # Arrange into rows of 2 columns
        table_data = []
        row = []
        
        for i, (label, value) in enumerate(info_items):
            # Create a cell with label and value
            cell = f"<b>{label}:</b> {value}"
            row.append(Paragraph(cell, self.styles['Normal']))
            
            # Add row after every 2 items
            if i % 2 == 1 or i == len(info_items) - 1:
                # If odd number of items, add empty cell to complete the row
                if i % 2 == 0:
                    row.append(Paragraph("", self.styles['Normal']))
                
                table_data.append(row)
                row = []
        
        # Create table with calculated widths
        if table_data:
            col_width = (page_width - 60) / 2  # Account for margins
            table = Table(table_data, colWidths=[col_width, col_width])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _create_ingredients_list(self, ingredients):
        """
        Create a formatted list of ingredients
        
        Args:
            ingredients (list): List of ingredients
            
        Returns:
            list: Elements for ingredients list
        """
        elements = []
        
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
            
            # Add as paragraph
            elements.append(Paragraph(ingredient_text, self.styles['IngredientItem']))
        
        return elements
    
    def _create_instructions_list(self, instructions):
        """
        Create a formatted list of instruction steps
        
        Args:
            instructions (list): List of instruction steps
            
        Returns:
            list: Elements for instructions list
        """
        elements = []
        
        for i, step in enumerate(instructions, 1):
            # Format with step number
            step_text = f"{i}. {step}"
            
            # Add as paragraph
            elements.append(Paragraph(step_text, self.styles['InstructionItem']))
        
        return elements
    
    def _create_footer(self, recipe_data):
        """
        Create footer section with source information
        
        Args:
            recipe_data (dict): Recipe data
            
        Returns:
            list: Elements for footer section
        """
        elements = []
        
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
        
        # Add source info
        elements.append(Paragraph(source_text, self.styles['Footer']))
        
        # Add generation timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated on {timestamp}", self.styles['Footer']))
        
        return elements
    
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
        
        # Limit filename length to avoid issues
        if len(clean_title) > 50:
            clean_title = clean_title[:50]
        
        # Add timestamp to ensure uniqueness
        timestamp = int(time.time())
        
        return f"{clean_title}_{timestamp}.pdf"
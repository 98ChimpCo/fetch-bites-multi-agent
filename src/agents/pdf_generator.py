# src/agents/pdf_generator.py
import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage, TableStyle, Frame, PageTemplate, Flowable
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.lib.units import inch
from src.agents.pdf_cache import PDFCache

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class NumberedCircle(Flowable):
    """Custom flowable for creating numbered circles"""

    def __init__(self, number, text, width=400, height=18):
        Flowable.__init__(self)
        self.number = number
        self.text = text
        self.width = width
        self.height = height

    def draw(self):
        # Draw a slightly smaller circle and tighter text layout
        from reportlab.pdfgen import canvas
        # Circle geometry
        circle_radius = 8
        circle_x = circle_radius + 2
        circle_y = self.height / 2

        # Black circle with white number
        self.canv.setFillColor(colors.black)
        self.canv.circle(circle_x, circle_y, circle_radius, fill=1)

        # White number text, better vertical centering
        self.canv.setFillColor(colors.white)
        self.canv.setFont('Helvetica-Bold', 10)
        text_width = self.canv.stringWidth(str(self.number), 'Helvetica-Bold', 10)
        text_x = circle_x - (text_width / 2)
        # Tighter vertical centering in circle
        text_y = circle_y - 4
        self.canv.drawString(text_x, text_y, str(self.number))

        # Draw instruction text, 14px line height
        self.canv.setFillColor(colors.black)
        self.canv.setFont('Helvetica', 11)
        text_start_x = circle_x + circle_radius + 8
        text_start_y = circle_y - 5
        from reportlab.pdfbase.pdfmetrics import stringWidth
        available_width = self.width - text_start_x - 10
        words = self.text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if stringWidth(test_line, 'Helvetica', 11) <= available_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(' '.join(current_line))
        # Draw each line, 14px line height
        for i, line in enumerate(lines):
            line_y = text_start_y - (i * 14)
            self.canv.drawString(text_start_x, line_y, line)
        # Adjust height for multi-line
        if len(lines) > 1:
            self.height = max(18, len(lines) * 14 + 4)

class PDFGenerator:
    def __init__(self, output_dir='pdfs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.accent_color = colors.HexColor('#FF8C42')  # Orange color from template
        self.apricot_color = colors.HexColor('#FFAA64')  # Apricot color for ingredients bullets
        self.text_color = colors.HexColor('#333333')
        self.gray_color = colors.HexColor('#666666')
        self.light_gray = colors.HexColor('#F5F5F5')
        self.page_width = LETTER[0]
        self.styles = getSampleStyleSheet()
        
        # V1 and V2 Template styles - improved typography to match template exactly
        self.styles.add(ParagraphStyle(name='RecipeTitle', fontName='Helvetica-Bold', fontSize=24, alignment=0, textColor=self.text_color, spaceAfter=4))
        self.styles.add(ParagraphStyle(name='RecipeDescription', fontName='Helvetica', fontSize=12, alignment=0, textColor=colors.HexColor('#555555'), spaceAfter=8, leading=14))
        self.styles.add(ParagraphStyle(name='ChefInfo', fontName='Helvetica', fontSize=9, alignment=0, textColor=self.gray_color, spaceAfter=2))
        self.styles.add(ParagraphStyle(name='SectionTitle', fontName='Helvetica-Bold', fontSize=18, textColor=self.text_color, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='IngredientBullet', fontName='Helvetica', fontSize=11, leftIndent=0, spaceAfter=2, leading=14))
        self.styles.add(ParagraphStyle(name='IngredientItem', fontName='Helvetica', fontSize=11, leftIndent=0, spaceAfter=4))  # V1 compatibility
        self.styles.add(ParagraphStyle(name='InstructionItem', fontName='Helvetica', fontSize=11, leftIndent=0, spaceAfter=6))  # V1 compatibility
        self.styles.add(ParagraphStyle(name='InstructionNumber', fontName='Helvetica', fontSize=11, spaceAfter=6, leading=16))
        self.styles.add(ParagraphStyle(name='StatsLabel', fontName='Helvetica', fontSize=9, textColor=self.gray_color, alignment=1))
        self.styles.add(ParagraphStyle(name='StatsValue', fontName='Helvetica-Bold', fontSize=13, textColor=self.text_color, alignment=1, leading=14))
        self.styles.add(ParagraphStyle(name='Notes', fontName='Helvetica', fontSize=11, textColor=self.gray_color, leading=16))
        self.styles.add(ParagraphStyle(name='Footer', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.gray, alignment=1))
        self.cache = PDFCache()

    def generate_pdf(self, recipe_data: Dict, image_path: Optional[str] = None, post_url: Optional[str] = None) -> Tuple[str, bool]:
        try:
            # Get layout version from environment variable
            layout_version = os.getenv("LAYOUT_VERSION", "v1")
            creator = recipe_data.get("source", {}).get("creator", "")
            caption = recipe_data.get("source", {}).get("caption", "")
            from src.agents.pdf_cache import get_post_hash
            post_hash = get_post_hash(caption, creator, layout_version)
            cached_path = self.cache.get(post_hash)
            if cached_path and os.path.exists(cached_path):
                logger.info(f"Using cached PDF for post_hash {post_hash}")
                return cached_path, True

            logger.info(f"Generating PDF for recipe: {recipe_data.get('title', 'Untitled Recipe')} using template {layout_version}")
            filename = self._get_filename(recipe_data)
            filepath = os.path.join(self.output_dir, filename)
            
            # Generate PDF based on template version
            if layout_version == "v2":
                return self._generate_pdf_v2(recipe_data, image_path, post_url, filepath, post_hash, creator, caption)
            else:
                return self._generate_pdf_v1(recipe_data, image_path, post_url, filepath, post_hash, creator, caption)
                
        except Exception as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            return None, False

    def _generate_pdf_v1(self, recipe_data: Dict, image_path: Optional[str], post_url: Optional[str], filepath: str, post_hash: str, creator: str, caption: str) -> Tuple[str, bool]:
        """Generate PDF using V1 template (original format)"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=LETTER, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            # Include image if present
            if image_path and os.path.exists(image_path):
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(image_path) as pil_img:
                        width, height = pil_img.size
                    max_width = doc.width
                    max_height = doc.height * 0.4  # Allow image to use up to 40% of page height
                    scale_factor = min(max_width / width, max_height / height, 1.0)
                    img = RLImage(image_path, width=width * scale_factor, height=height * scale_factor)
                    img.hAlign = 'CENTER'
                    elements.append(img)
                    elements.append(Spacer(1, 12))
                except Exception as img_error:
                    logger.warning(f"Failed to load image into PDF: {img_error}")

            title = recipe_data.get('title', 'Untitled Recipe')
            elements.append(Paragraph(title, self.styles['RecipeTitle']))
            elements.append(Spacer(1, 12))

            description = recipe_data.get('description')
            if description:
                elements.append(Paragraph(description, self.styles['Normal']))
                elements.append(Spacer(1, 12))

            info_elements = self._create_recipe_info_v1(recipe_data, doc.width)
            if info_elements:
                elements.extend(info_elements)
                elements.append(Spacer(1, 12))

            elements.append(Paragraph('Ingredients', self.styles['SectionTitle']))
            elements.append(Spacer(1, 6))
            ingredients = recipe_data.get('ingredients', [])
            if ingredients:
                ingredient_elements = self._create_ingredients_list_v1(ingredients)
                elements.extend(ingredient_elements)
            else:
                elements.append(Paragraph('No ingredients listed', self.styles['Normal']))

            elements.append(Spacer(1, 12))
            elements.append(Paragraph('Instructions', self.styles['SectionTitle']))
            elements.append(Spacer(1, 6))
            instructions = recipe_data.get('instructions', [])
            if instructions:
                instruction_elements = self._create_instructions_list_v1(instructions)
                elements.extend(instruction_elements)
            else:
                elements.append(Paragraph('No instructions listed', self.styles['Normal']))

            elements.append(Spacer(1, 20))
            footer_elements = self._create_footer(recipe_data, post_url)
            elements.extend(footer_elements)

            doc.build(elements)
            self.cache.set(post_hash, creator, caption, recipe_data, filepath)
            logger.info(f"PDF cache set for post_hash {post_hash}")
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath, False
        except Exception as e:
            logger.error(f"Failed to generate V1 PDF: {str(e)}")
            return None, False

    def _generate_pdf_v2(self, recipe_data: Dict, image_path: Optional[str], post_url: Optional[str], filepath: str, post_hash: str, creator: str, caption: str) -> Tuple[str, bool]:
        """Generate PDF using V2 template (new format)"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
            elements = []

            # Header section with image and recipe info
            header_table = self._create_header_section(recipe_data, image_path, doc.width)
            if header_table:
                elements.append(header_table)
                elements.append(Spacer(1, 20))

            # Stats section (prep time, cook time, servings, views)
            stats_table = self._create_stats_section(recipe_data, doc.width)
            if stats_table:
                elements.append(stats_table)
                elements.append(Spacer(1, 30))

            # Two-column layout for ingredients and directions
            content_table = self._create_two_column_content(recipe_data, doc.width)
            if content_table:
                elements.append(content_table)

            # Notes section - always include to match template with rounded rectangle background
            elements.append(Spacer(1, 20))
            
            # Create Notes section with rounded rectangle background
            notes_elements = []
            notes_elements.append(Paragraph('Notes', self.styles['SectionTitle']))
            notes_elements.append(Spacer(1, 8))
            
            notes = recipe_data.get('notes')
            if notes:
                notes_elements.append(Paragraph(notes, self.styles['Notes']))
            else:
                # General fallback note
                default_notes = "Enjoy immediately. This dish is best served hot and fresh!"
                notes_elements.append(Paragraph(default_notes, self.styles['Notes']))
            
            # Wrap notes in a table with rounded rectangle styling (simulated with background color and padding)
            notes_table_data = [[notes_elements]]
            notes_table = Table(notes_table_data, colWidths=[doc.width])
            notes_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F8F8')),  # Light gray background
                ('TOPPADDING', (0, 0), (-1, -1), 20),  # More padding for rounded effect
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                # Add thicker, softer border to simulate more rounded rectangle
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#D8D8D8')),
                ('ROUNDEDCORNERS', (0, 0), (-1, -1), 8),  # More rounded corners if supported
            ]))
            
            elements.append(notes_table)

            # No footer needed in V2 - source is already in header

            doc.build(elements)
            # Cache expects extracted_text (recipe_data) and needs save() call
            self.cache.set(post_hash, creator, caption, recipe_data, filepath)
            self.cache.save()
            logger.info(f"PDF cache set for post_hash {post_hash}")
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath, False
        except Exception as e:
            logger.error(f"Failed to generate V2 PDF: {str(e)}")
            return None, False
    
    def _create_recipe_info_v1(self, recipe_data, page_width):
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
        
        # if recipe_data.get('difficulty'):
        #     info_items.append(('Difficulty', recipe_data['difficulty'].capitalize()))
        
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
    
    def _create_ingredients_list_v1(self, ingredients):
        """
        Create a formatted list of ingredients

        Args:
            ingredients (list): List of ingredients or sections

        Returns:
            list: Elements for ingredients list
        """
        elements = []

        if ingredients and isinstance(ingredients[0], dict) and 'section' in ingredients[0]:
            # Sectioned ingredients
            for section in ingredients:
                section_title = section.get('section', '').strip()
                items = section.get('items', [])
                if section_title:
                    elements.append(Paragraph(section_title, self.styles['SectionTitle']))
                for item in items:
                    quantity = item.get('quantity', '')
                    unit = item.get('unit', '')
                    name = item.get('name', '')

                    if quantity and unit:
                        text = f"• {quantity} {unit} {name}"
                    elif quantity:
                        text = f"• {quantity} {name}"
                    else:
                        text = f"• {name}"

                    elements.append(Paragraph(text, self.styles['IngredientItem']))
                elements.append(Spacer(1, 6))
        else:
            # Flat list
            for ingredient in ingredients:
                if isinstance(ingredient, dict):
                    quantity = ingredient.get('quantity', '')
                    unit = ingredient.get('unit', '')
                    name = ingredient.get('name', '')
                    if quantity and unit:
                        ingredient_text = f"• {quantity} {unit} {name}"
                    elif quantity:
                        ingredient_text = f"• {quantity} {name}"
                    else:
                        ingredient_text = f"• {name}"
                else:
                    ingredient_text = f"• {ingredient}"

                elements.append(Paragraph(ingredient_text, self.styles['IngredientItem']))

        return elements
    
    def _create_instructions_list_v1(self, instructions):
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
    
    def _create_footer(self, recipe_data, post_url=None):
        """
        Create footer section with source information
        
        Args:
            recipe_data (dict): Recipe data
            post_url (str): Optional post URL fallback
            
        Returns:
            list: Elements for footer section
        """
        elements = []
        
        # Get source information - simplified format to match template
        source = recipe_data.get('source', {})
        url = source.get('url') or post_url or ''
        url = url.split('?')[0]  # Remove query parameters
        
        # Source info - cleaner format
        if url:
            source_text = f'Source: Instagram - <a href="{url}" color="gray">{url}</a>'
            elements.append(Paragraph(source_text, self.styles['Footer']))
        
        # Add generation timestamp - smaller and more subtle
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

    def _create_header_section(self, recipe_data, image_path, page_width):
        """Create header section with image and recipe info (V2 template)"""
        try:
            # Left column: Square Image
            left_elements = []
            if image_path and os.path.exists(image_path):
                try:
                    from PIL import Image as PILImage
                    import tempfile
                    # Crop to square (centered)
                    with PILImage.open(image_path) as pil_img:
                        width, height = pil_img.size
                        min_dimension = min(width, height)
                        left = (width - min_dimension) // 2
                        top = 0  # align to top for vertical alignment
                        right = left + min_dimension
                        bottom = top + min_dimension
                        cropped_img = pil_img.crop((left, top, right, bottom))
                        temp_img_path = tempfile.mktemp(suffix='.jpg')
                        cropped_img.save(temp_img_path, 'JPEG', quality=95)
                    # Use cropped square image in PDF - width should match left column (40%)
                    available_width = page_width - 40  # Account for margins
                    left_col_width = available_width * 0.4  # 40% for left column
                    img_size = left_col_width  # Square: width and height
                    img = RLImage(temp_img_path, width=img_size, height=img_size)
                    left_elements.append(img)
                except Exception as img_error:
                    logger.warning(f"Failed to load header image: {img_error}")

            # Right column: Recipe info
            right_elements = []
            title = recipe_data.get('title', 'Untitled Recipe')
            right_elements.append(Paragraph(title, self.styles['RecipeTitle']))
            right_elements.append(Spacer(1, 8))  # More spacing between title and description
            description = recipe_data.get('description', '')
            if description:
                right_elements.append(Paragraph(description, self.styles['RecipeDescription']))
            # Chef info, Instagram, URL (with emoji icons)
            source = recipe_data.get('source', {})
            creator = source.get('creator', '')
            chef_text = f"👨‍🍳 Chef {creator}" if creator else "👨‍🍳 Chef Marco Antonelli"
            right_elements.append(Paragraph(chef_text, self.styles['ChefInfo']))
            right_elements.append(Spacer(1, 4))
            ig_handle = source.get('instagram_handle', '') or "chef_marco"
            ig_text = f"📸 @{ig_handle}"
            right_elements.append(Paragraph(ig_text, self.styles['ChefInfo']))
            right_elements.append(Spacer(1, 4))
            url = source.get('url', '')
            if url:
                url_text = f'🔗 <a href="{url}" color="blue">{url}</a>'
                right_elements.append(Paragraph(url_text, self.styles['ChefInfo']))
                right_elements.append(Spacer(1, 4))
            # Remove extra spacers between creator, IG, URL (tighter, or use Spacer(1, 3) if needed)

            # Create table with image left, info right
            if left_elements and right_elements:
                table_data = [[left_elements, right_elements]]
                available_width = page_width - 40  # Account for margins
                left_col_width = available_width * 0.4
                right_col_width = available_width * 0.6
                col_widths = [left_col_width, right_col_width]
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (0, 0), 'TOP'),  # Image top aligned
                    ('VALIGN', (1, 0), (1, 0), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                return table
            elif right_elements:
                if len(right_elements) == 1:
                    return right_elements[0]
                else:
                    table_data = [[right_elements]]
                    table = Table(table_data, colWidths=[page_width])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    return table
        except Exception as e:
            logger.error(f"Error creating header section: {e}")
        return None

    def _create_stats_section(self, recipe_data, page_width):
        """Create stats section with prep time, cook time, servings, views (V2 template, 2x2 layout)"""
        try:
            # Gather stat values
            prep_time = recipe_data.get('prep_time', '10 minutes')
            cook_time = recipe_data.get('cook_time', '10 minutes')
            servings = recipe_data.get('servings', '4')
            views = recipe_data.get('views', '2.4K')

            # Build cells for each stat
            prep_cell = [
                Paragraph('PREP TIME', self.styles['StatsLabel']),
                Paragraph(str(prep_time), self.styles['StatsValue'])
            ]
            cook_cell = [
                Paragraph('COOK TIME', self.styles['StatsLabel']),
                Paragraph(str(cook_time), self.styles['StatsValue'])
            ]
            servings_cell = [
                Paragraph('SERVINGS', self.styles['StatsLabel']),
                Paragraph(str(servings), self.styles['StatsValue'])
            ]
            views_cell = [
                Paragraph('VIEWS', self.styles['StatsLabel']),
                Paragraph(str(views), self.styles['StatsValue'])
            ]

            # Arrange into two rows, two columns each
            stats_data = [
                [prep_cell, cook_cell],
                [servings_cell, views_cell],
            ]

            # Stats section spans right column width (60%)
            available_width = page_width - 40
            left_col_width = available_width * 0.4
            right_col_width = available_width * 0.6
            stat_col_width = right_col_width / 2
            col_widths = [stat_col_width, stat_col_width]

            stats_table = Table(stats_data, colWidths=col_widths)
            stats_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), self.light_gray),
                ('TOPPADDING', (0, 0), (-1, -1), 24),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 24),
                ('LEFTPADDING', (0, 0), (-1, -1), 14),
                ('RIGHTPADDING', (0, 0), (-1, -1), 14),
                # Vertical lines between columns for both rows
                ('LINEAFTER', (0, 0), (0, -1), 1, colors.white),
                # Horizontal line between rows (if desired, but template omits, so skip)
            ]))

            # Position the stats table in the right column (60%)
            positioning_data = [['', stats_table]]
            positioning_table = Table(positioning_data, colWidths=[left_col_width, right_col_width])
            positioning_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            return positioning_table
        except Exception as e:
            logger.error(f"Error creating stats section: {e}")
        return None

    def _create_two_column_content(self, recipe_data, page_width):
        """Create two-column layout with ingredients and directions (V2 template)"""
        try:
            # Calculate column widths: left 40%, right 60% (minus margins)
            available_width = page_width - 40
            left_col_width = available_width * 0.4
            right_col_width = available_width * 0.6
            # Left column: Ingredients
            left_elements = []
            left_elements.append(Paragraph('Ingredients', self.styles['SectionTitle']))
            ingredients = recipe_data.get('ingredients', [])
            if ingredients:
                for ingredient in ingredients:
                    if isinstance(ingredient, dict):
                        quantity = ingredient.get('quantity', '')
                        unit = ingredient.get('unit', '')
                        name = ingredient.get('name', '')
                        if quantity and unit:
                            ingredient_text = f'<font color="{self.apricot_color}">●</font> {quantity} {unit} {name}'
                        elif quantity:
                            ingredient_text = f'<font color="{self.apricot_color}">●</font> {quantity} {name}'
                        else:
                            ingredient_text = f'<font color="{self.apricot_color}">●</font> {name}'
                    else:
                        ingredient_text = f'<font color="{self.apricot_color}">●</font> {ingredient}'
                    ingredient_para = Paragraph(ingredient_text, self.styles['IngredientBullet'])
                    left_elements.append(ingredient_para)
            else:
                left_elements.append(Paragraph('No ingredients listed', self.styles['Normal']))
            # Right column: Directions
            right_elements = []
            right_elements.append(Paragraph('Directions', self.styles['SectionTitle']))
            instructions = recipe_data.get('instructions', [])
            if instructions:
                for i, step in enumerate(instructions, 1):
                    step_flowable = NumberedCircle(i, step, width=right_col_width-20)
                    right_elements.append(step_flowable)
                    right_elements.append(Spacer(1, 8))  # More consistent vertical spacing between steps
            else:
                right_elements.append(Paragraph('No instructions listed', self.styles['Normal']))
            # Two-column table with backgrounds, paddings, bullet colors
            if left_elements and right_elements:
                col_widths = [left_col_width, right_col_width]
                table_data = [[left_elements, right_elements]]
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (0, -1), 15),
                    ('RIGHTPADDING', (0, 0), (0, -1), 10),
                    ('LEFTPADDING', (1, 0), (1, -1), 15),
                    ('RIGHTPADDING', (1, 0), (1, -1), 15),
                    ('TOPPADDING', (0, 0), (-1, -1), 15),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5DC')),
                    ('BACKGROUND', (1, 0), (1, -1), colors.white),
                ]))
                return table
        except Exception as e:
            logger.error(f"Error creating two-column content: {e}")
        return None
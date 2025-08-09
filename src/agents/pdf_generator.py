# src/agents/pdf_generator.py
import os
import logging
import time
import json
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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

    def __init__(self, number, text, width=400, height=18, *, circle_radius=8, num_offset_y=-4, text_size=11, line_height=13):
        Flowable.__init__(self)
        self.number = number
        self.text = text
        self.width = width
        self.height = height
        self.circle_radius = circle_radius
        self.num_offset_y = num_offset_y
        self.text_size = text_size
        self.line_height = line_height

    def draw(self):
        # Draw a slightly smaller circle and tighter text layout
        from reportlab.pdfgen import canvas
        # Circle geometry
        circle_radius = self.circle_radius
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

        # Draw instruction text, line height from layout
        self.canv.setFillColor(colors.black)
        self.canv.setFont('Helvetica', self.text_size)
        text_start_x = circle_x + circle_radius + 8
        text_start_y = circle_y + self.num_offset_y + 1
        from reportlab.pdfbase.pdfmetrics import stringWidth
        available_width = self.width - text_start_x - 10
        words = self.text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if stringWidth(test_line, 'Helvetica', self.text_size) <= available_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(' '.join(current_line))
        # Draw each line, layout-driven line height
        for i, line in enumerate(lines):
            line_y = text_start_y - (i * self.line_height)
            self.canv.drawString(text_start_x, line_y, line)
        # Adjust height for multi-line
        if len(lines) > 1:
            self.height = max(18, len(lines) * self.line_height + 4)

# --- RoundedTable Flowable for notes background ---
class RoundedTable(Flowable):
    """A wrapper that draws a rounded rectangle behind a Table/Flowable."""
    def __init__(self, inner_table, width, padding=16, radius=6, bg=colors.HexColor('#F8F8F8'), stroke=colors.HexColor('#E0E0E0'), stroke_width=1):
        super().__init__()
        self.inner = inner_table
        self.width = width
        self.padding = padding
        self.radius = radius
        self.bg = bg
        self.stroke = stroke
        self.stroke_width = stroke_width
        self._wrapped = False
        self._inner_w = 0
        self._inner_h = 0

    def wrap(self, availWidth, availHeight):
        # Constrain to provided width
        iw, ih = self.inner.wrap(self.width - 2*self.padding, availHeight)
        self._inner_w, self._inner_h = iw, ih
        total_w = self.width
        total_h = ih + 2*self.padding
        self._wrapped = True
        return total_w, total_h

    def draw(self):
        if not self._wrapped:
            # Fallback sizing if wrap was not called
            self._inner_w, self._inner_h = self.inner.wrap(self.width - 2*self.padding, 10000)
        w = self.width
        h = self._inner_h + 2*self.padding
        r = self.radius
        c = self.canv
        c.saveState()
        # Background rounded rect
        c.setFillColor(self.bg)
        c.setStrokeColor(self.stroke)
        c.setLineWidth(self.stroke_width)
        c.roundRect(0, 0, w, h, r, stroke=1, fill=1)
        # Draw inner at padding offset
        self.inner.drawOn(c, self.padding, self.padding)
        c.restoreState()

class PDFGenerator:
    def _icon_text_cell(self, icon_filename: str, text: str, *, style_name: str = 'StatsInline', icon_px: int = 12):
        """Return a small [icon + text] cell (Table) if icon exists, else a Paragraph(text).
        Looks for icons under assets/icons/; default style is 'StatsInline'. Use style_name='ChefInfo' for header rows.
        """
        try:
            from reportlab.platypus import Table, TableStyle, Paragraph, Image as RLImage
            path = os.path.join('assets', 'icons', icon_filename)
            if os.path.exists(path):
                img = RLImage(path, width=icon_px, height=icon_px)
                t = Table([[img, Paragraph(text, self.styles[style_name])]], colWidths=[icon_px + 2, None])
                t.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                return t
        except Exception as e:
            logger.warning(f"_icon_text_cell fallback to text: {e}")
        # Fallback: text only
        return Paragraph(text, self.styles.get(style_name, self.styles['StatsInline']))
    def __init__(self, output_dir='pdfs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.accent_color = colors.HexColor('#FF8C42')  # Orange color from template
        self.text_color = colors.HexColor('#333333')
        self.gray_color = colors.HexColor('#666666')
        self.light_gray = colors.HexColor('#F5F5F5')
        self.notes_bg = colors.HexColor('#F8F8F8')  # Light gray for notes background
        self.page_width = LETTER[0]
        self.styles = getSampleStyleSheet()

        # --- Font registration: SF Pro (.otf) if available ---
        def _register_sf_font(alias, filenames):
            for fn in filenames:
                path = os.path.join('assets', 'fonts', fn)
                if os.path.exists(path):
                    try:
                        pdfmetrics.registerFont(TTFont(alias, path))
                        logger.info(f"Registered font {alias} from {path}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to register {alias} from {path}: {e}")
            return False

        has_light   = _register_sf_font('SFPro-Light',    ['SFProText-Light.otf', 'SFProText-LightItalic.otf', 'SF-Pro-Text-Light.otf'])
        has_regular = _register_sf_font('SFPro-Regular',  ['SFProText-Regular.otf', 'SF-Pro-Text-Regular.otf'])
        has_semibold= _register_sf_font('SFPro-Semibold', ['SFProText-Semibold.otf', 'SF-Pro-Text-Semibold.otf'])
        has_bold    = _register_sf_font('SFPro-Bold',     ['SFProText-Bold.otf', 'SF-Pro-Text-Bold.otf'])

        if has_regular and has_bold:
            try:
                pdfmetrics.registerFontFamily('SFPro', normal='SFPro-Regular', bold='SFPro-Bold', italic='SFPro-Regular', boldItalic='SFPro-Bold')
            except Exception as e:
                logger.warning(f"Could not register font family SFPro: {e}")

        # Load external layout config if provided
        self.layout = self._load_layout()

        def _lv(keys, default):
            node = self.layout or {}
            for k in keys:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    return default
            return node
        self._lv = _lv
        logger.info(f"Layout config path: {os.getenv('LAYOUT_CONFIG', 'layout.v2.json')} | keys: {list(self.layout.keys()) if isinstance(self.layout, dict) else 'none'}")

        # --- SF Pro font selection for styles ---
        base_title_font = 'SFPro-Bold' if has_bold else 'Helvetica-Bold'
        base_heading_font = 'SFPro-Semibold' if has_semibold else ('SFPro-Bold' if has_bold else 'Helvetica-Bold')
        base_body_font = 'SFPro-Light' if has_light else ('SFPro-Regular' if has_regular else 'Helvetica')
        base_meta_font = 'SFPro-Regular' if has_regular else 'Helvetica'

        # Typography tuned lighter, with more breathing room
        self.styles.add(ParagraphStyle(name='RecipeTitle', fontName=base_meta_font, fontSize=22, leading=24, alignment=0, textColor=self.text_color, spaceAfter=12))
        self.styles.add(ParagraphStyle(name='RecipeDescription', fontName=base_body_font, fontSize=10.5, leading=14, alignment=0, textColor=colors.HexColor('#555555'), spaceAfter=0))
        self.styles.add(ParagraphStyle(name='ChefInfo', fontName=base_meta_font, fontSize=10, leading=12, alignment=0, textColor=self.gray_color, spaceAfter=2))
        self.styles.add(ParagraphStyle(name='SectionTitle', fontName=base_heading_font, fontSize=15, leading=17, textColor=self.text_color, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='SectionTitleCentered', fontName=base_heading_font, fontSize=15, leading=17, textColor=self.text_color, alignment=1, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='NotesTitle', fontName=base_meta_font, fontSize=15, leading=17, textColor=self.text_color, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='IngredientItem', fontName=base_body_font, fontSize=10.5, leading=15, leftIndent=0, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='InstructionItem', fontName=base_body_font, fontSize=10.5, leading=16, leftIndent=0, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='InstructionNumber', fontName=base_body_font, fontSize=10.5, leading=15, spaceAfter=4))
        self.styles.add(ParagraphStyle(name='StatsInline', fontName=base_meta_font, fontSize=10.5, leading=14, textColor=self.gray_color, alignment=0, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='StatsLabel', fontName=base_meta_font, fontSize=9, leading=12, textColor=self.gray_color, alignment=1))
        self.styles.add(ParagraphStyle(name='StatsValue', fontName=base_heading_font, fontSize=12.5, leading=14, textColor=self.text_color, alignment=1))
        self.styles.add(ParagraphStyle(name='Notes', fontName=base_body_font, fontSize=10.5, leading=15, textColor=self.gray_color))
        self.styles.add(ParagraphStyle(name='Footer', fontName=base_meta_font, fontSize=8.5, leading=10, textColor=colors.gray, alignment=1))
        self.cache = PDFCache()

    def _load_layout(self):
        path = os.getenv('LAYOUT_CONFIG', 'layout.v2.json')
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.info(f"Layout config not loaded ({path}): {e}")
        return {}

    def generate_pdf(self, recipe_data: Dict, image_path: Optional[str] = None, post_url: Optional[str] = None) -> Tuple[str, bool]:
        try:
            # Get layout version from environment variable
            layout_version = os.getenv("LAYOUT_VERSION", "v2")
            # Check if caching is disabled (useful for testing)
            disable_cache = os.getenv("DISABLE_PDF_CACHE", "false").lower() == "true"
            # --- LOG SETTINGS ---
            logger.info(f"[PDF] LAYOUT_VERSION={layout_version}")
            logger.info(f"[PDF] LAYOUT_CONFIG={os.getenv('LAYOUT_CONFIG')}")
            # --------------------
            if not disable_cache:
                creator = recipe_data.get("source", {}).get("creator", "")
                caption = recipe_data.get("source", {}).get("caption", "")
                from src.agents.pdf_cache import get_post_hash
                post_hash = get_post_hash(caption, creator, layout_version)
                cached_path = self.cache.get(post_hash)
                if cached_path and os.path.exists(cached_path):
                    logger.info(f"Using cached PDF for post_hash {post_hash}")
                    return cached_path, True
            else:
                logger.info("PDF caching disabled via DISABLE_PDF_CACHE environment variable")
                post_hash = None

            logger.info(f"Generating PDF for recipe: {recipe_data.get('title', 'Untitled Recipe')} using template {layout_version}")
            filename = self._get_filename(recipe_data)
            filepath = os.path.join(self.output_dir, filename)
            # Generate PDF based on template version
            if layout_version == "v2":
                if disable_cache:
                    return self._generate_pdf_v2(recipe_data, image_path, post_url, filepath, None, "", "")
                else:
                    return self._generate_pdf_v2(recipe_data, image_path, post_url, filepath, post_hash, creator, caption)
            else:
                if disable_cache:
                    return self._generate_pdf_v1(recipe_data, image_path, post_url, filepath, None, "", "")
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
                    elements.append(Spacer(1, 8))
                except Exception as img_error:
                    logger.warning(f"Failed to load image into PDF: {img_error}")

            title = recipe_data.get('title', 'Untitled Recipe')
            elements.append(Paragraph(title, self.styles['RecipeTitle']))
            elements.append(Spacer(1, 8))

            description = recipe_data.get('description')
            if description:
                elements.append(Paragraph(description, self.styles['Normal']))
                elements.append(Spacer(1, 8))

            info_elements = self._create_recipe_info_v1(recipe_data, doc.width)
            if info_elements:
                elements.extend(info_elements)
                elements.append(Spacer(1, 8))

            elements.append(Paragraph('Ingredients', self.styles['SectionTitle']))
            elements.append(Spacer(1, 4))
            ingredients = recipe_data.get('ingredients', [])
            if ingredients:
                ingredient_elements = self._create_ingredients_list_v1(ingredients)
                elements.extend(ingredient_elements)
            else:
                elements.append(Paragraph('No ingredients listed', self.styles['Normal']))

            elements.append(Spacer(1, 8))
            elements.append(Paragraph('Instructions', self.styles['SectionTitle']))
            elements.append(Spacer(1, 4))
            instructions = recipe_data.get('instructions', [])
            if instructions:
                instruction_elements = self._create_instructions_list_v1(instructions)
                elements.extend(instruction_elements)
            else:
                elements.append(Paragraph('No instructions listed', self.styles['Normal']))

            elements.append(Spacer(1, 16))
            footer_elements = self._create_footer(recipe_data, post_url)
            elements.extend(footer_elements)

            doc.build(elements)
            if post_hash:
                self.cache.set(post_hash, creator, caption, recipe_data, filepath)
                logger.info(f"PDF cache set for post_hash {post_hash}")
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath, False
        except Exception as e:
            logger.error(f"Failed to generate V1 PDF: {str(e)}")
            return None, False

    def _generate_pdf_v2(self, recipe_data: Dict, image_path: Optional[str], post_url: Optional[str], filepath: str, post_hash: str, creator: str, caption: str) -> Tuple[str, bool]:
        """Generate PDF using V2 template (new format matching template)"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=35, bottomMargin=35)
            elements = []

            # Header section with image and recipe info (including inline stats)
            header_table = self._create_header_section_v2(recipe_data, image_path, doc.width)
            if header_table:
                elements.append(header_table)
                elements.append(Spacer(1, 20))

            # Two-column layout for ingredients and directions
            content_table = self._create_two_column_content_v2(recipe_data, doc.width)
            if content_table:
                elements.append(content_table)

            # Notes section with rounded rectangle background
            elements.append(Spacer(1, 10))
            notes_section = self._create_notes_section(recipe_data, doc.width)
            if notes_section:
                elements.append(notes_section)

            doc.build(elements)
            # Cache if needed
            if post_hash:
                self.cache.set(post_hash, creator, caption, recipe_data, filepath)
                self.cache.save()
                logger.info(f"PDF cache set for post_hash {post_hash}")
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath, False
        except Exception as e:
            logger.error(f"Failed to generate V2 PDF: {str(e)}")
            return None, False
    
    def _create_recipe_info_v1(self, recipe_data, page_width):
        """Create recipe info section with prep time, cook time, etc."""
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
        
        # Display dietary info if available
        dietary_info = recipe_data.get('dietary_info', [])
        if dietary_info:
            info_items.append(('Dietary', ', '.join(dietary_info)))
        
        if not info_items:
            return elements
        
        # Create a table for the info section
        table_data = []
        row = []
        
        for i, (label, value) in enumerate(info_items):
            cell = f"<b>{label}:</b> {value}"
            row.append(Paragraph(cell, self.styles['Normal']))
            
            if i % 2 == 1 or i == len(info_items) - 1:
                if i % 2 == 0:
                    row.append(Paragraph("", self.styles['Normal']))
                
                table_data.append(row)
                row = []
        
        if table_data:
            col_width = (page_width - 60) / 2
            table = Table(table_data, colWidths=[col_width, col_width])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _create_ingredients_list_v1(self, ingredients):
        """Create a formatted list of ingredients without bullets"""
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
                        text = f"{quantity} {unit} {name}"
                    elif quantity:
                        text = f"{quantity} {name}"
                    else:
                        text = name

                    elements.append(Paragraph(text, self.styles['IngredientItem']))
                elements.append(Spacer(1, 4))
        else:
            # Flat list
            for ingredient in ingredients:
                if isinstance(ingredient, dict):
                    quantity = ingredient.get('quantity', '')
                    unit = ingredient.get('unit', '')
                    name = ingredient.get('name', '')
                    if quantity and unit:
                        ingredient_text = f"{quantity} {unit} {name}"
                    elif quantity:
                        ingredient_text = f"{quantity} {name}"
                    else:
                        ingredient_text = name
                else:
                    ingredient_text = ingredient

                elements.append(Paragraph(ingredient_text, self.styles['IngredientItem']))

        return elements
    
    def _create_instructions_list_v1(self, instructions):
        """Create a formatted list of instruction steps"""
        elements = []
        
        for i, step in enumerate(instructions, 1):
            step_text = f"{i}. {step}"
            elements.append(Paragraph(step_text, self.styles['InstructionItem']))
        
        return elements
    
    def _create_footer(self, recipe_data, post_url=None):
        """Create footer section with source information"""
        elements = []
        
        # Get source information
        source = recipe_data.get('source', {})
        url = source.get('url') or post_url or ''
        url = url.split('?')[0]  # Remove query parameters
        
        # Source info
        if url:
            source_text = f'Source: Instagram - <a href="{url}" color="gray">{url}</a>'
            elements.append(Paragraph(source_text, self.styles['Footer']))
        
        # Add generation timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated on {timestamp}", self.styles['Footer']))
        
        return elements
    
    def _get_filename(self, recipe_data):
        """Generate a filename for the PDF"""
        title = recipe_data.get('title', 'Untitled Recipe')
        clean_title = ''.join(c if c.isalnum() or c.isspace() else '_' for c in title)
        clean_title = clean_title.replace(' ', '_')
        
        if len(clean_title) > 50:
            clean_title = clean_title[:50]
        
        timestamp = int(time.time())
        
        return f"{clean_title}_{timestamp}.pdf"

    def _create_header_section_v2(self, recipe_data, image_path, page_width):
        """Create header section with image, recipe info, and inline stats (V2 template)"""
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
                    # Use cropped square image in PDF
                    available_width = page_width
                    left_col_width = available_width * 0.4
                    img_size = left_col_width  # Square: width and height
                    img = RLImage(temp_img_path, width=img_size, height=img_size)
                    left_elements.append(img)
                except Exception as img_error:
                    logger.warning(f"Failed to load header image: {img_error}")

            # Right column: Recipe info
            right_elements = []
            title = recipe_data.get('title', 'Untitled Recipe')
            right_elements.append(Paragraph(title, self.styles['RecipeTitle']))

            # (Subtitle moved to notes section; keep header tighter)
            right_elements.append(Spacer(1, 2))

            source = recipe_data.get('source', {})
            creator = source.get('creator', '')
            ig_handle = source.get('instagram_handle', '') or "chef_marco"
            # Single meta line to match template: "Chef Marco Antonelli @chef_marco"
            meta_line = f"Chef {creator} @{ig_handle}" if creator else f"Chef Marco Antonelli @{ig_handle}"
            right_elements.append(self._icon_text_cell('chef-hat.png', meta_line, style_name='ChefInfo', icon_px=12))

            url = source.get('url', '')
            if url:
                url_text = f'<a href="{url}" color="blue">{url}</a>'
                right_elements.append(self._icon_text_cell('external-link.png', url_text, style_name='ChefInfo', icon_px=12))

            # Inline stats below meta/link with a small gap
            right_elements.append(Spacer(1, 18))
            stats_para = self._create_inline_stats(recipe_data)
            right_elements.append(stats_para)

            # Create table with image left, info right
            if left_elements and right_elements:
                table_data = [[left_elements, right_elements]]
                available_width = page_width
                left_col_width = available_width * 0.4
                right_col_width = available_width * 0.6
                col_widths = [left_col_width, right_col_width]
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (0, 0), 'TOP'),
                    ('VALIGN', (1, 0), (1, 0), 'TOP'),
                    # Increase gutter between image (col 0) and text (col 1)
                    ('RIGHTPADDING', (0, 0), (0, 0), 12),
                    ('LEFTPADDING',  (1, 0), (1, 0), 12),  # match right-column body padding
                    ('LEFTPADDING',  (0, 0), (0, 0), 0),
                    ('RIGHTPADDING', (1, 0), (1, 0), 0),
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

    def _create_inline_stats(self, recipe_data):
        """Create two-row stats with small inline icons (PNG). Falls back to text when icons missing."""
        try:
            def _fmt(v, default='—'):
                if v is None:
                    return default
                s = str(v).strip()
                return s if s else default

            prep_time = _fmt(recipe_data.get('prep_time', '15 min'))
            cook_time = _fmt(recipe_data.get('cook_time', '25 min'))
            servings  = _fmt(recipe_data.get('servings', '4'))
            likes_val = recipe_data.get('likes')
            views_val = recipe_data.get('views')
            likes     = _fmt(likes_val if likes_val is not None else views_val, '—')

            # Build four cells: [timer + prep] [flame + cook] / [plate + feeds] [heart + likes]
            c1 = self._icon_text_cell('timer.png',  f"{prep_time} (Prep)")
            c2 = self._icon_text_cell('flame.png',  f"{cook_time} (Cook)")
            c3 = self._icon_text_cell('plate.png',  f"{servings} (Feeds)")
            c4 = self._icon_text_cell('heart.png',  f"{likes} (Likes)")

            outer = Table([[c1, c2], [c3, c4]])
            outer.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            return outer
        except Exception as e:
            logger.error(f"Error creating inline stats: {e}")
            # Graceful fallback
            try:
                line1 = f"{_fmt(recipe_data.get('prep_time', '15 min'))} (Prep)    {_fmt(recipe_data.get('cook_time', '25 min'))} (Cook)"
                likes_fb = recipe_data.get('likes') or recipe_data.get('views')
                line2 = f"{_fmt(recipe_data.get('servings', '4'))} (Feeds)    {_fmt(likes_fb, '—')} (Likes)"
                html = f"<b>{line1}</b><br/><b>{line2}</b>"
                return Paragraph(html, self.styles['StatsInline'])
            except Exception:
                return Paragraph("", self.styles['StatsInline'])

    def _number_badge(self, n: int, diameter: int = 16):
        """Return a small circular number badge as a Drawing for table cell usage."""
        d = Drawing(diameter, diameter)
        r = diameter / 2.0
        d.add(Circle(r, r, r, fillColor=colors.black, strokeColor=colors.black))
        # Center the number; Helvetica-Bold 9 fits well in 16px circle
        d.add(String(r, r - 3, str(n), fontName='Helvetica-Bold', fontSize=9, fillColor=colors.white, textAnchor='middle'))
        return d

    def _create_two_column_content_v2(self, recipe_data, page_width):
        """Create two-column layout with ingredients (no bullets) and directions (V2 template)"""
        try:
            # Calculate column widths
            available_width = page_width
            left_col_width = available_width * 0.4
            right_col_width = available_width * 0.6

            # Left column: Ingredients (no bullets)
            left_elements = []
            left_elements.append(Paragraph('Ingredients', self.styles['SectionTitleCentered']))
            left_elements.append(Spacer(1, 6))
            ingredients = recipe_data.get('ingredients', [])
            if ingredients:
                for ingredient in ingredients:
                    if isinstance(ingredient, dict):
                        quantity = ingredient.get('quantity', '')
                        unit = ingredient.get('unit', '')
                        name = ingredient.get('name', '')
                        # NO BULLETS - just clean text
                        if quantity and unit:
                            ingredient_text = f'{quantity} {unit} {name}'
                        elif quantity:
                            ingredient_text = f'{quantity} {name}'
                        else:
                            ingredient_text = name
                    else:
                        ingredient_text = ingredient

                    ingredient_para = Paragraph(ingredient_text, self.styles['IngredientItem'])
                    left_elements.append(ingredient_para)
            else:
                left_elements.append(Paragraph('No ingredients listed', self.styles['Normal']))

            # Right column: Directions
            right_elements = []
            right_elements.append(Paragraph('Directions', self.styles['SectionTitleCentered']))
            right_elements.append(Spacer(1, 6))
            instructions = recipe_data.get('instructions', [])
            if instructions:
                rows = []
                badge_w = 18  # fixed badge column width
                for i, step in enumerate(instructions, 1):
                    badge = self._number_badge(i, diameter=16)
                    para = Paragraph(step, self.styles['InstructionItem'])
                    rows.append([badge, para])
                steps_table = Table(rows, colWidths=[badge_w, right_col_width - badge_w - 4])
                steps_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  # row gutter
                ]))
                right_elements.append(steps_table)
            else:
                right_elements.append(Paragraph('No instructions listed', self.styles['Normal']))

            # Two-column table
            if left_elements and right_elements:
                col_widths = [left_col_width, right_col_width]
                table_data = [[left_elements, right_elements]]
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (0, -1), 12),
                    ('RIGHTPADDING', (0, 0), (0, -1), 8),
                    # Increase left padding for directions column (col 1) by ~10 units (was 12, now 22)
                    ('LEFTPADDING', (1, 0), (1, -1), 22),
                    ('RIGHTPADDING', (1, 0), (1, -1), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ]))
                return table
        except Exception as e:
            logger.error(f"Error creating two-column content: {e}")
        return None

    def _create_notes_section(self, recipe_data, page_width):
        """Create notes section with rounded rectangle background"""
        try:
            notes_elements = []
            has_any = False
            # Title will be added only if we end up with content

            # Move subtitle/description into notes top
            desc = recipe_data.get('description')
            if desc:
                notes_elements.append(Paragraph(' '.join(str(desc).split()), self.styles['RecipeDescription']))
                notes_elements.append(Spacer(1, 6))
                has_any = True

            notes = recipe_data.get('notes')
            if notes:
                notes_elements.append(Paragraph(notes, self.styles['Notes']))
                has_any = True

            if not has_any:
                return None
            # Add a lightweight title only when content exists
            notes_elements.insert(0, Spacer(1, 6))
            notes_elements.insert(0, Paragraph("Chef's Notes", self.styles['NotesTitle']))

            # Wrap notes in a table with rounded rectangle styling
            notes_table_data = [[notes_elements]]
            notes_table = Table(notes_table_data, colWidths=[page_width])
            # Add left padding for notes table contents
            notes_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING', (0, 0), (-1, -1), -8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            rounded = RoundedTable(
                notes_table,
                width=page_width,
                padding=16,
                radius=6,
                bg=self.notes_bg,
                stroke=colors.HexColor('#E0E0E0'),
                stroke_width=1
            )
            return rounded
        except Exception as e:
            logger.error(f"Error creating notes section: {e}")
        return None
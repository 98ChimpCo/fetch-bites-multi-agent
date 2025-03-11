# src/agents/pdf_generator.py
import os
import json
import logging
import qrcode
from io import BytesIO
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from fpdf import FPDF
from PIL import Image

logger = logging.getLogger(__name__)

class RecipePDF(FPDF):
    """Custom PDF class for recipe cards"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font('DejaVu', '', 'src/utils/fonts/DejaVuSans.ttf', uni=True)
        self.add_font('DejaVu', 'B', 'src/utils/fonts/DejaVuSans-Bold.ttf', uni=True)
        self.add_font('DejaVu', 'I', 'src/utils/fonts/DejaVuSans-Oblique.ttf', uni=True)
    
    def header(self):
        # No header for recipe cards
        pass
    
    def footer(self):
        # Add page number
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('DejaVu', 'B', 14)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)
    
    def chapter_body(self, body):
        self.set_font('DejaVu', '', 11)
        self.multi_cell(0, 5, body)
        self.ln()

class PDFGeneratorAgent:
    """Agent for generating PDF recipe cards"""
    
    def __init__(self):
        self.generated_count = 0
        self.last_generated = None
        self._load_stats()
        
        # Create fonts directory if it doesn't exist
        os.makedirs("src/utils/fonts", exist_ok=True)
        
        # Download DejaVu fonts if they don't exist
        self._ensure_fonts()
    
    def _ensure_fonts(self):
        """Ensure that required fonts are available"""
        font_urls = {
            "DejaVuSans.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf",
            "DejaVuSans-Oblique.ttf": "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Oblique.ttf"
        }
        
        for font_name, url in font_urls.items():
            font_path = f"src/utils/fonts/{font_name}"
            if not os.path.exists(font_path):
                try:
                    logger.info(f"Downloading font: {font_name}")
                    response = requests.get(url)
                    with open(font_path, "wb") as f:
                        f.write(response.content)
                except Exception as e:
                    logger.error(f"Error downloading font {font_name}: {str(e)}")
    
    def _load_stats(self):
        """Load generator statistics"""
        try:
            if os.path.exists("data/processed/generator_stats.json"):
                with open("data/processed/generator_stats.json", "r") as f:
                    stats = json.load(f)
                    self.generated_count = stats.get("generated_count", 0)
                    self.last_generated = stats.get("last_generated")
        except Exception as e:
            logger.error(f"Error loading generator stats: {str(e)}")
    
    def _save_stats(self):
        """Save generator statistics"""
        try:
            os.makedirs("data/processed", exist_ok=True)
            with open("data/processed/generator_stats.json", "w") as f:
                stats = {
                    "generated_count": self.generated_count,
                    "last_generated": self.last_generated
                }
                json.dump(stats, f)
        except Exception as e:
            logger.error(f"Error saving generator stats: {str(e)}")
    
    async def generate_pdf(self, recipe_data: Dict) -> str:
        """Generate a PDF recipe card from recipe data"""
        try:
            # Create PDF document
            pdf = RecipePDF()
            pdf.add_page()
            
            # Add title
            pdf.set_font('DejaVu', 'B', 16)
            pdf.cell(0, 10, recipe_data.get("title", "Recipe Card"), 0, 1, 'C')
            pdf.ln(5)
            
            # Add thumbnail if available
            if "thumbnail_url" in recipe_data and recipe_data["thumbnail_url"]:
                try:
                    response = requests.get(recipe_data["thumbnail_url"])
                    img = Image.open(BytesIO(response.content))
                    
                    # Resize image if needed
                    max_width = 180
                    width, height = img.size
                    if width > max_width:
                        ratio = max_width / width
                        new_height = int(height * ratio)
                        img = img.resize((max_width, new_height))
                    
                    # Save temporary image file
                    temp_img_path = "data/processed/temp_thumbnail.jpg"
                    img.save(temp_img_path)
                    
                    # Add to PDF
                    image_width = min(180, width)
                    pdf.image(temp_img_path, x=(210-image_width)/2, y=pdf.get_y(), w=image_width)
                    pdf.ln(5)
                    
                    # Remove temporary file
                    os.remove(temp_img_path)
                except Exception as e:
                    logger.error(f"Error adding thumbnail: {str(e)}")
            
            # Add description if available
            if "description" in recipe_data and recipe_data["description"]:
                pdf.set_font('DejaVu', 'I', 11)
                pdf.multi_cell(0, 5, recipe_data["description"])
                pdf.ln(5)
            
            # Add recipe info table (time, servings, difficulty)
            info_items = []
            
            if "prep_time" in recipe_data and recipe_data["prep_time"]:
                info_items.append(f"Prep: {recipe_data['prep_time']}")
            
            if "cook_time" in recipe_data and recipe_data["cook_time"]:
                info_items.append(f"Cook: {recipe_data['cook_time']}")
            
            if "total_time" in recipe_data and recipe_data["total_time"]:
                info_items.append(f"Total: {recipe_data['total_time']}")
            
            if "servings" in recipe_data and recipe_data["servings"]:
                info_items.append(f"Serves: {recipe_data['servings']}")
            
            if "difficulty" in recipe_data and recipe_data["difficulty"]:
                info_items.append(f"Difficulty: {recipe_data['difficulty']}")
            
            if info_items:
                pdf.set_font('DejaVu', '', 10)
                pdf.set_fill_color(240, 240, 240)
                
                # Calculate cell width based on number of items
                cell_width = 180 / min(len(info_items), 3)
                
                # Print info items in rows with up to 3 items per row
                for i in range(0, len(info_items), 3):
                    row_items = info_items[i:i+3]
                    for item in row_items:
                        pdf.cell(cell_width, 8, item, 1, 0, 'C', 1)
                    pdf.ln()
                
                pdf.ln(5)
            
            # Add dietary info if available
            if "dietary_info" in recipe_data and recipe_data["dietary_info"]:
                dietary_info = ", ".join(recipe_data["dietary_info"])
                pdf.set_font('DejaVu', 'I', 10)
                pdf.cell(0, 6, f"Dietary: {dietary_info}", 0, 1, 'L')
                pdf.ln(2)
            
            # Add ingredients
            pdf.chapter_title("Ingredients")
            
            ingredients = recipe_data.get("ingredients", [])
            if ingredients:
                for ingredient in ingredients:
                    # Format ingredient line
                    if isinstance(ingredient, dict):
                        # Format as quantity + unit + name
                        quantity = ingredient.get("quantity", "")
                        unit = ingredient.get("unit", "")
                        name = ingredient.get("name", "")
                        
                        # Format the ingredient text
                        if quantity and unit:
                            ingredient_text = f"{quantity} {unit} {name}".strip()
                        elif quantity:
                            ingredient_text = f"{quantity} {name}".strip()
                        else:
                            ingredient_text = name
                    else:
                        # If ingredient is just a string
                        ingredient_text = str(ingredient)
                    
                    # Add to PDF
                    pdf.set_font('DejaVu', '', 10)
                    pdf.cell(5, 5, "•", 0, 0, 'R')
                    pdf.cell(0, 5, ingredient_text, 0, 1, 'L')
            else:
                pdf.set_font('DejaVu', 'I', 10)
                pdf.cell(0, 5, "No ingredients listed", 0, 1, 'L')
            
            pdf.ln(5)
            
            # Add instructions
            pdf.chapter_title("Instructions")
            
            instructions = recipe_data.get("instructions", [])
            if instructions:
                for i, instruction in enumerate(instructions, 1):
                    pdf.set_font('DejaVu', 'B', 10)
                    pdf.cell(8, 5, f"{i}.", 0, 0, 'L')
                    
                    pdf.set_font('DejaVu', '', 10)
                    pdf.multi_cell(172, 5, instruction)
                    pdf.ln(2)
            else:
                pdf.set_font('DejaVu', 'I', 10)
                pdf.cell(0, 5, "No instructions listed", 0, 1, 'L')
            
            # Add source information and QR code
            if "source" in recipe_data and "url" in recipe_data["source"]:
                pdf.ln(10)
                
                # Add separator line
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                
                source_url = recipe_data["source"]["url"]
                
                # Generate QR code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(source_url)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_path = "data/processed/temp_qr.png"
                qr_img.save(qr_path)
                
                # Add QR code
                pdf.image(qr_path, x=170, y=pdf.get_y(), w=20)
                
                # Add source text
                pdf.set_font('DejaVu', 'I', 8)
                pdf.cell(160, 5, "Original Recipe:", 0, 1, 'L')
                pdf.cell(160, 5, source_url, 0, 1, 'L')
                
                # Remove temporary QR file
                os.remove(qr_path)
            
            # Save PDF file
            os.makedirs("data/processed/pdfs", exist_ok=True)
            
            # Generate filename from recipe title
            title_slug = recipe_data.get("title", "recipe").lower()
            title_slug = "".join(c if c.isalnum() else "_" for c in title_slug)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            pdf_filename = f"data/processed/pdfs/{title_slug}_{timestamp}.pdf"
            
            pdf.output(pdf_filename)
            
            # Update stats
            self.generated_count += 1
            self.last_generated = datetime.now().isoformat()
            self._save_stats()
            
            logger.info(f"Generated PDF: {pdf_filename}")
            return pdf_filename
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return ""
    
    def get_generated_count(self) -> int:
        """Get the number of PDFs generated"""
        return self.generated_count

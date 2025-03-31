from fpdf import FPDF
import os
import re
from datetime import datetime

def generate_pdf_and_return_path(recipe_dict, output_dir="generated_pdfs"):
    """
    Generate a PDF from a dictionary containing recipe information.
    
    Args:
        recipe_dict (dict): Dictionary containing title, ingredients, steps, etc.
        output_dir (str): Directory to save the PDF
    
    Returns:
        str: Path to the generated PDF file
    """
    os.makedirs(output_dir, exist_ok=True)

    title = recipe_dict.get("title", "Untitled Recipe")
    ingredients = recipe_dict.get("ingredients", [])
    steps = recipe_dict.get("steps", [])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    safe_title = re.sub(r'[^a-zA-Z0-9_]+', '', title.replace(" ", "_"))
    filename = f"{safe_title}_{timestamp}.pdf"
    filename = f"{title.replace(' ', '_')}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, title, ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(200, 10, "Ingredients:", ln=True)
    for ingredient in ingredients:
        pdf.multi_cell(0, 10, f"- {ingredient}")

    pdf.ln(5)
    pdf.cell(200, 10, "Instructions:", ln=True)
    for i, step in enumerate(steps, 1):
        pdf.multi_cell(0, 10, f"{i}. {step}")
        pdf.ln(1)

    pdf.output(filepath)
    return filepath
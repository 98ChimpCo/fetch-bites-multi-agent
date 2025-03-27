import os
from fpdf import FPDF

def generate_pdf_and_return_path(recipe_dict, output_dir="generated_pdfs"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    title = recipe_dict.get("title", "Untitled Recipe")
    ingredients = recipe_dict.get("ingredients", [])
    instructions = recipe_dict.get("instructions", [])

    filename = f"{title.replace(' ', '_')}.pdf"
    filepath = os.path.join(output_dir, filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.multi_cell(0, 10, txt=f"Recipe: {title}", align='L')
    pdf.ln()

    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt="Ingredients:", align='L')
    for item in ingredients:
        pdf.multi_cell(0, 10, txt=f"• {item}", align='L')
    pdf.ln()

    pdf.multi_cell(0, 10, txt="Instructions:", align='L')
    for step in instructions:
        pdf.multi_cell(0, 10, txt=f"• {step}", align='L')

    pdf.output(filepath)
    return filepath
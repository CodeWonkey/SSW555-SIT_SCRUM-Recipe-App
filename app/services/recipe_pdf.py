"""Printable PDF downloads of saved recipes."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.models import Recipe
from app.services.recipe_share import ingredient_text


FONT_PATH = Path(__file__).resolve().parents[1] / "fonts" / "DejaVuSans.ttf"
pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))
BODY = ParagraphStyle("Recipe text", fontName="DejaVuSans", fontSize=11, leading=16, spaceAfter=5)
TITLE = ParagraphStyle("Recipe title", parent=BODY, fontSize=24, leading=30, spaceAfter=8)
HEADING = ParagraphStyle("Section", parent=BODY, fontName="Helvetica-Bold", fontSize=15,
                         leading=19, spaceBefore=12, keepWithNext=True)
ITEM = ParagraphStyle("List item", parent=BODY, leftIndent=30, bulletFontName="DejaVuSans")


def recipe_pdf(recipe: Recipe) -> BytesIO:
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, title=recipe.title,
                                 leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=48)
    content = [
        Paragraph(escape(recipe.title), TITLE),
        Paragraph(f"Servings: {recipe.servings}", BODY),
        Paragraph("Ingredients", HEADING),
    ]
    for ingredient in recipe.ingredients:
        content.append(Paragraph(escape(ingredient_text(ingredient)), ITEM, bulletText="•"))
    content.append(Paragraph("Instructions", HEADING))
    for number, step in enumerate(recipe.steps, 1):
        content.append(Paragraph(escape(step), ITEM, bulletText=f"{number}."))

    document.build(content)
    output.seek(0)
    return output

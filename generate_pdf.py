from pypdf import PdfWriter
from io import BytesIO
from reportlab.pdfgen import canvas

def create_pdf():
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 750, "This is a test document about Solid State Batteries.")
    c.drawString(100, 730, "Solid state batteries use a solid electrolyte instead of a liquid one.")
    c.drawString(100, 710, "They offer higher energy density and safety.")
    c.save()
    buffer.seek(0)
    
    with open("test.pdf", "wb") as f:
        f.write(buffer.read())

if __name__ == "__main__":
    create_pdf()

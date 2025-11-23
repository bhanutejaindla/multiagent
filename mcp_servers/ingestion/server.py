from mcp.server.fastmcp import FastMCP
import pypdf
import docx
import os

mcp = FastMCP("ingestion")


@mcp.tool()
def read_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"

    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


@mcp.tool()
def read_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"

    try:
        doc = docx.Document(file_path)
        text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
        return text.strip()
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"


if __name__ == "__main__":
    mcp.run()

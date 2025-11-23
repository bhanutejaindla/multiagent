from mcp.server.fastmcp import FastMCP
import re

mcp = FastMCP("compliance")

@mcp.tool()
def redact_pii(text: str) -> str:
    """Redact PII (emails, phone numbers) from text."""
    # Redact emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    text = re.sub(email_pattern, "[REDACTED_EMAIL]", text)
    
    # Redact phone numbers (simple pattern)
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    text = re.sub(phone_pattern, "[REDACTED_PHONE]", text)
    
    return text

if __name__ == "__main__":
    mcp.run()

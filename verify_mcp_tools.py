import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from mcp_servers.research.server import web_search
from mcp_servers.compliance.server import redact_pii
from mcp_servers.citation_validation.server import parse_web_search_results
from mcp_servers.ingestion.server import read_pdf, read_docx

async def test_research():
    print("--- Testing Research MCP ---")
    try:
        results = await asyncio.to_thread(web_search, "latest python version", max_results=2)
        print(f"Research Result (Length: {len(results)}):\n{results[:200]}...")
        return results
    except Exception as e:
        print(f"Research Failed: {e}")
        return ""

async def test_compliance():
    print("\n--- Testing Compliance MCP ---")
    text = "Contact me at test@example.com or 555-123-4567."
    try:
        redacted = await asyncio.to_thread(redact_pii, text)
        print(f"Original: {text}")
        print(f"Redacted: {redacted}")
        if "[REDACTED_EMAIL]" in redacted and "[REDACTED_PHONE]" in redacted:
            print("✓ Redaction Successful")
        else:
            print("✗ Redaction Failed")
    except Exception as e:
        print(f"Compliance Failed: {e}")

async def test_citation(web_results):
    print("\n--- Testing Citation MCP (Parsing) ---")
    try:
        sources = parse_web_search_results(web_results)
        print(f"Parsed {len(sources)} sources.")
        if len(sources) > 0:
            print(f"First Source: {sources[0]}")
            print("✓ Parsing Successful")
        else:
            print("⚠ No sources parsed (might be expected if search failed)")
    except Exception as e:
        print(f"Citation Parsing Failed: {e}")

async def test_ingestion():
    print("\n--- Testing Ingestion MCP ---")
    # Create dummy files
    with open("test.txt", "w") as f:
        f.write("Dummy text")
    
    # We can't easily test PDF/DOCX without actual files, but we can test the error handling
    result = read_pdf("non_existent.pdf")
    print(f"PDF Read Result (Expected Error): {result}")
    
    if "Error: File not found" in result:
        print("✓ Error Handling Successful")
    
    os.remove("test.txt")

async def main():
    web_results = await test_research()
    await test_citation(web_results)
    await test_compliance()
    await test_ingestion()

if __name__ == "__main__":
    asyncio.run(main())

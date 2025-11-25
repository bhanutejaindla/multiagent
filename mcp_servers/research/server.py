from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

mcp = FastMCP("research")

@mcp.tool()
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Perform a web search using DuckDuckGo."""
    try:
        results = DDGS().text(query, max_results=max_results)
        return list(results)
    except Exception as e:
        return [{"error": f"Error performing search: {str(e)}"}]

if __name__ == "__main__":
    mcp.run()

from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

mcp = FastMCP("research")

@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """Perform a web search using DuckDuckGo."""
    try:
        results = DDGS().text(query, max_results=max_results)
        formatted_results = ""
        for i, res in enumerate(results):
            formatted_results += f"{i+1}. [{res['title']}]({res['href']})\n{res['body']}\n\n"
        return formatted_results
    except Exception as e:
        return f"Error performing search: {str(e)}"

if __name__ == "__main__":
    mcp.run()

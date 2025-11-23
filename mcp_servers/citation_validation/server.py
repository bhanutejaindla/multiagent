from mcp.server.fastmcp import FastMCP
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import re
import json
from typing import List, Dict, Any

load_dotenv()

mcp = FastMCP("citation_validation")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

@mcp.tool()
def parse_web_search_results(web_results: str) -> List[Dict[str, Any]]:
    """
    Parses the raw web search results string into a structured list of sources.
    Expected format: "1. [Title](URL)\nBody..."
    """
    sources = []
    # Split by the numbered list pattern (e.g., "1. [")
    # This regex looks for a number, a dot, a space, and then a bracket
    raw_entries = re.split(r'\n(\d+)\. \[', "\n" + web_results)
    
    # The first element is usually empty or text before the first item
    for i in range(1, len(raw_entries), 2):
        if i + 1 >= len(raw_entries):
            break
            
        index = raw_entries[i]
        content = "[" + raw_entries[i+1] # Add back the bracket
        
        # Extract title, URL, and body
        # Format: [Title](URL)\nBody
        match = re.match(r'\[(.*?)\]\((.*?)\)\s*(.*)', content, re.DOTALL)
        if match:
            title = match.group(1)
            url = match.group(2)
            body = match.group(3).strip()
            
            sources.append({
                "id": index,
                "title": title,
                "url": url,
                "text": body
            })
            
    return sources

@mcp.tool()
async def verify_citations_internal(draft_answer: str, sources: List[Dict[str, Any]], strict_mode: bool = False) -> Dict[str, Any]:
    """
    Verifies citations in the draft answer against the provided sources.
    Returns a structured dictionary with score, issues, and validity status.
    """
    
    # Prepare sources text for the prompt
    sources_text = ""
    for source in sources:
        sources_text += f"Source [{source['id']}]: {source['title']}\n{source['text']}\n\n"
        
    verification_prompt = ChatPromptTemplate.from_template(
        """Verify the following answer for accuracy and proper citation usage based on the sources.
        
        Draft Answer: {draft_answer}
        
        Sources:
        {sources_text}
        
        INSTRUCTIONS:
        1. Check if every factual claim is supported by the cited source.
        2. Check if the citations (e.g., [1]) actually exist in the provided sources.
        3. Check for hallucinations (claims not found in any source).
        4. Check for temporal accuracy (e.g., "current" status matches the latest info).
        
        Return the result in the following JSON format:
        {{
            "score": <float between 0.0 and 1.0>,
            "is_valid": <boolean>,
            "supported_claims": <int>,
            "total_claims": <int>,
            "issues": [
                "<description of issue 1>",
                "<description of issue 2>"
            ],
            "summary": "<brief summary of verification>"
        }}
        """
    )
    
    chain = verification_prompt | llm
    response = await chain.ainvoke({
        "draft_answer": draft_answer,
        "sources_text": sources_text
    })
    
    try:
        # Clean up the response to ensure it's valid JSON
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        result = json.loads(content)
        return result
    except Exception as e:
        return {
            "score": 0.0,
            "is_valid": False,
            "supported_claims": 0,
            "total_claims": 0,
            "issues": [f"Failed to parse verification result: {str(e)}"],
            "summary": "Verification failed due to parsing error."
        }

if __name__ == "__main__":
    mcp.run()

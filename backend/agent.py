from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv
from .rag import query_documents
import asyncio

# Direct imports from MCP server files (Python functions)
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_servers.research.server import web_search
from mcp_servers.compliance.server import redact_pii
from mcp_servers.citation_validation.server import verify_citations_internal, parse_web_search_results

from .report_generator import ReportGenerator
from datetime import datetime
from typing import Optional
from langfuse.langchain import CallbackHandler

load_dotenv()

# Initialize LLM
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("WARNING: OPENAI_API_KEY not found. Using mock LLM response.")
    llm = None
else:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

from .graph import graph
from langchain_core.messages import HumanMessage

from .agents.orchestrator_agent import OrchestratorAgent

class ResearchAgent:
    def __init__(self):
        self.graph = graph
        self.langfuse_handler = CallbackHandler()
        self.orchestrator = OrchestratorAgent(self.graph)

    async def run(self, query: str, thread_id: str = "default", job_id: Optional[int] = None):
        """Executes the agent workflow for a given query."""
        # Use provided job_id or try to parse from thread_id
        if job_id is None and thread_id.isdigit():
            job_id = int(thread_id)
            
        print(f"--- Starting ResearchAgent for Query: {query} (job_id: {job_id}) ---")
        
        try:
            result = await self.orchestrator.run_research_flow(query, job_id=job_id)
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Agent execution failed: {e}")
            return {
                "answer": f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}",
                "reports": {}
            }

    async def chat_with_context(self, query: str, context: str):
        """Answers a query based on the provided context (report)."""
        # Access the LLM from one of the agents or create a new one
        llm = self.orchestrator.chat_agent.llm
        if not llm:
             return "LLM not available."
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer the user's question based ONLY on the following report content. If the answer is not in the report, say so."},
            {"role": "user", "content": f"Report Content:\n{context}\n\nQuestion: {query}"}
        ]
        response = await llm.ainvoke(messages)
        return response.content

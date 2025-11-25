from __future__ import annotations

import asyncio
import json
import os
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .base import BaseAgent, AgentCard
from ..report_generator import ReportGenerator

 
class SynthesisReportAgent(BaseAgent):
    """Generates structured reports from gathered evidence."""

    def __init__(self) -> None:
        super().__init__(
            AgentCard(
                name="synthesis_report_agent",
                description="Creates structured research reports with inline citations and exports.",
                capabilities=[
                    "generate_sections",
                    "produce_tables",
                    "export_report",
                ],
                rate_limit_per_minute=6,
            )
        )

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        self.prompt = ChatPromptTemplate.from_template(
            """
You are the Synthesis & Report agent.
Create a structured research report using ONLY the provided evidence.

User Query: {query}
Web Findings: {web_findings}
Retrieved Evidence: {rag_context}

CRITICAL INSTRUCTION:
- Focus STRICTLY on the User Query.
- Ignore any information in the "Retrieved Evidence" that is not directly relevant to the User Query.
- Do not include project metadata, assignment details, or unrelated examples unless requested.


Return STRICT JSON:
{{
  "summary": "...",
  "sections": [
    {{"title": "Section Title", "content": "Long content with citations [1]"}}
  ],
  "tables": [
    {{"title": "Table Title", "rows": [["col1","col2"],["v1","v2"]]}}
  ],
  "citations": [
    {{"id": 1, "source": "Title", "url": "...", "quote": "..."}}
  ]
}}
"""
        )

        self.generator = ReportGenerator()     

    async def generate_report(self, query: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Generates structured JSON report using LLM."""
        
        # Mock fallback if no API key
        if not os.getenv("OPENAI_API_KEY"):
            print("WARNING: OPENAI_API_KEY not found. Using mock synthesis response.")
            return {
                "summary": f"Mock Report for: {query}",
                "sections": [
                    {"title": "Introduction", "content": "This is a mock introduction based on the query."}
                ],
                "tables": [],
                "citations": []
            }

        chain = self.prompt | self.llm

        response = await chain.ainvoke(
            {
                "query": query,
                "web_findings": evidence.get("web_results", ""),
                "rag_context": evidence.get("context", ""),
            }
        )

        raw = response.content.strip()

        # Handle triple-backtick code formatting
        if raw.startswith("```"):
            raw = raw.split("```")[1]

        # Parse JSON safely
        try:
            parsed = json.loads(raw)
        except Exception as e:
            parsed = {
                "summary": raw,
                "sections": [],
                "tables": [],
                "citations": [],
                "error": f"JSON parsing failed: {str(e)}"
            }

        return parsed

    def format_report(self, report: Dict[str, Any]) -> str:
        """Formats the structured report dictionary into a string."""
        lines = []
        if "summary" in report:
            lines.append(f"Summary\n=======\n{report['summary']}\n")
        
        if "sections" in report:
            for section in report["sections"]:
                lines.append(f"\n{section.get('title', 'Section')}\n{'-'*len(section.get('title', 'Section'))}\n{section.get('content', '')}")
        
        if "tables" in report:
            for table in report["tables"]:
                lines.append(f"\nTable: {table.get('title', '')}")
                for row in table.get("rows", []):
                    lines.append(" | ".join(str(x) for x in row))
        
        if "citations" in report:
            lines.append("\nReferences\n==========")
            for cit in report["citations"]:
                lines.append(f"[{cit.get('id')}] {cit.get('source')} - {cit.get('url')}")
        
        return "\n".join(lines)

    async def export(self, final_answer: str | Dict[str, Any], job_id: int | None = None) -> Dict[str, str]:
        """Exports DOCX and PDF versions of the final report."""
        filename = f"report_{job_id}" if job_id else "report_preview"

        # Format dictionary to string if needed
        content = final_answer
        if isinstance(final_answer, dict):
            content = self.format_report(final_answer)

        docx_path = await asyncio.to_thread(
            self.generator.generate_docx, content, filename
        )
        pdf_path = await asyncio.to_thread(
            self.generator.generate_pdf, content, filename
        )

        return {"docx": docx_path, "pdf": pdf_path}

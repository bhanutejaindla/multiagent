from __future__ import annotations

import asyncio

import os

from typing import Dict, Any, List

from langchain_openai import ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate

from pydantic import BaseModel, Field

from .base import BaseAgent, AgentCard

from ..report_generator import ReportGenerator

# ----------------------------

# Pydantic Models

# ----------------------------

class Citation(BaseModel):

    id: int

    source: str

    url: str

    quote: str

class TableRow(BaseModel):

    cells: List[str]

class Table(BaseModel):

    title: str

    headers: List[str]

    rows: List[TableRow]

class Section(BaseModel):

    title: str

    content: str

class ResearchReport(BaseModel):

    summary: str

    sections: List[Section]

    tables: List[Table] = []

    citations: List[Citation] = []

# ----------------------------

# Agent Implementation

# ----------------------------

class SynthesisReportAgent(BaseAgent):

    def __init__(self):

        super().__init__(

            AgentCard(

                name="synthesis_report_agent",

                description="Creates structured research reports with citations.",

                capabilities=["generate_sections", "produce_tables", "export_report"],

                rate_limit_per_minute=10,

            )

        )

        # IMPORTANT: Use large model for long structured output

        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

        self.structured_llm = self.llm.with_structured_output(ResearchReport)

        self.prompt = ChatPromptTemplate.from_template(

            """

You are an expert Research Analyst.

Write a long, detailed research report based ONLY on the evidence.

----------------

USER QUERY:

{query}

----------------

WEB FINDINGS:

{web_block}

----------------

RAG CONTEXT:

{rag_block}

----------------

CITATION SOURCES:

{citation_block}

----------------

INSTRUCTIONS:

- Produce a structured research report.

- The executive summary must be 2–3 paragraphs.

- Each section MUST contain 3–4 paragraphs.

- Each paragraph MUST be 5–8 sentences minimum. Never compress content.

- Every section should include inline citations using [1], [2], etc.

- The "citations" list MUST correspond exactly to the inline IDs used.

- If evidence is weak, clearly state limitations.

"""

        )

        self.generator = ReportGenerator()

    # -----------------------------

    # MAIN METHOD CALLED BY GRAPH

    # -----------------------------

    async def generate_report(self, query: str, evidence: Dict[str, Any]) -> Dict[str, Any]:

        

        # Build WEB BLOCK
        web_sources = evidence.get("web_results", [])
        web_block = ""
        citation_block = ""

        # Fix Issue 2: Auto-generate IDs
        for i, src in enumerate(web_sources, 1):
            # Ensure ID exists, default to loop index
            src_id = src.get("id", str(i))
            title = src.get("title", "Unknown Source")
            url = src.get("url", "N/A")
            quote = src.get("quote", "") or src.get("snippet", "") or src.get("body", "")
            
            web_block += f"[{src_id}] {title}\nURL: {url}\nQuote: {quote}\n\n"
            citation_block += f"[{src_id}] {title} — {url}\n"

        # Fix Issue 1: Ensure RAG context is string
        rag_raw = evidence.get("context", "")
        if isinstance(rag_raw, (dict, list)):
            rag_block = str(rag_raw)
        else:
            rag_block = str(rag_raw)

        # Run LLM with structured output
        chain = self.prompt | self.structured_llm

        try:

            report: ResearchReport = await chain.ainvoke({

                "query": query,

                "web_block": web_block,

                "rag_block": rag_block,

                "citation_block": citation_block,

            })

            parsed = report.model_dump()

            # flatten table rows

            for table in parsed.get("tables", []):

                table["rows"] = [row["cells"] for row in table.get("rows", [])]

            return parsed

        except Exception as e:

            return {

                "summary": "Failed to generate structured report.",

                "sections": [

                    {"title": "Error", "content": f"Error: {str(e)}"}

                ],

                "tables": [],

                "citations": []

            }

    # -----------------------------

    # FORMATTER FOR EXPORT

    # -----------------------------

    def format_report(self, report: Dict[str, Any]) -> str:

        out = []

        out.append("Summary\n=======\n")

        out.append(report["summary"])

        out.append("\n")

        for sec in report["sections"]:

            out.append(f"\n{sec['title']}\n{'-'*len(sec['title'])}\n{sec['content']}\n")

        if report.get("tables"):

            for t in report["tables"]:

                out.append(f"\nTable: {t['title']}")

                out.append(" | ".join(t["headers"]))

                for row in t["rows"]:

                    out.append(" | ".join(row))

        if report.get("citations"):

            out.append("\nReferences\n==========")

            for c in report["citations"]:

                out.append(f"[{c['id']}] {c['source']} — {c['url']}")

        return "\n".join(out)

    # -----------------------------

    # EXPORT PDF + DOCX

    # -----------------------------

    async def export(self, final_answer, job_id=None) -> Dict[str, str]:

        filename = f"report_{job_id}" if job_id else "report_preview"

        if isinstance(final_answer, dict):

            final_answer = self.format_report(final_answer)

        docx = await asyncio.to_thread(self.generator.generate_docx, final_answer, filename)

        pdf = await asyncio.to_thread(self.generator.generate_pdf, final_answer, filename)

        return {"docx": docx, "pdf": pdf}

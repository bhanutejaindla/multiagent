from __future__ import annotations

from typing import Dict, Any
from langchain_core.messages import HumanMessage

from .ingestion_agent import IngestionRetrievalAgent
from .web_research_agent import WebResearchAgent
from .synthesis_agent import SynthesisReportAgent
from .citation_agent import CitationAgent
from .compliance_agent import ComplianceAgent
from .chat_agent import ChatAgent



class OrchestratorAgent:
    """Plans and routes work across specialist agents using LangGraph or direct calls."""

    def __init__(self, graph_runner) -> None:
        self.ingestion_agent = IngestionRetrievalAgent()
        self.web_agent = WebResearchAgent()
        self.synthesis_agent = SynthesisReportAgent()
        self.citation_agent = CitationAgent()
        self.compliance_agent = ComplianceAgent()
        self.chat_agent = ChatAgent()
        self.graph = graph_runner



    async def run_research_flow(self, query: str, job_id: int | None = None) -> Dict[str, Any]:
        """
        Execute the graph-based multi-agent research flow.
        """
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "next_step": "start",
            "artifacts": {},
            "research_data": {},
            "final_report": {},
            "job_id": job_id,
        }

        final_state = await self.graph.ainvoke(
            initial_state,
            config={
                "configurable": {"thread_id": str(job_id) if job_id else "adhoc"},
            },
        )
        final_answer = final_state["artifacts"].get("final_answer", "No answer generated.")
        report_paths = final_state.get("final_report", {})
        return {"answer": final_answer, "reports": report_paths}

    async def ingest_and_retrieve(self, content: str, source: str, job_id: int | None = None):
        return await self.ingestion_agent.ingest_text(content, source, job_id)

    async def retrieve_context(self, query: str):
        return await self.ingestion_agent.retrieve(query)

    async def handle_chat(self, thread_id: str, message: str):
        human = HumanMessage(content=message)
        self.chat_agent.append_message(thread_id, human)
        summary = await self.chat_agent.summarize(thread_id)
        return {"summary": summary}


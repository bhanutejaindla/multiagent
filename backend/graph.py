from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
import os
from dotenv import load_dotenv
import asyncio

# Import tools/functions from existing modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime
from datetime import datetime
from .agents.ingestion_agent import IngestionRetrievalAgent
from .agents.web_research_agent import WebResearchAgent
from .agents.synthesis_agent import SynthesisReportAgent
from .agents.citation_agent import CitationAgent
from .agents.citation_agent import CitationAgent
from .agents.compliance_agent import ComplianceAgent
from .database import engine
from sqlmodel import Session
from .models import Report
from sqlalchemy import update



load_dotenv()

# --- State Definition ---

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_step: str
    job_id: Optional[int]
    artifacts: Dict[str, Any]
    research_data: Dict[str, Any] # Store research results
    final_report: Dict[str, str] # Store paths to generated reports

# --- Nodes ---

from pydantic import BaseModel
from typing import Literal

class Router(BaseModel):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Literal["research", "synthesis", "citation", "compliance", "report", "FINISH"]

async def supervisor_node(state: AgentState):
    """
    Supervisor node that routes to the next worker based on the conversation state.
    """
    messages = state["messages"]
    next_step = state.get("next_step", "start")
    
    # If we just started, default to research
    if next_step == "start":
        return {"next_step": "research"}
        
    # If we just finished report, we are done
    if next_step == "report":
        return {"next_step": "end"}

    # For other steps, use LLM to decide (or keep simple linear flow if preferred, 
    # but user asked for LLM decision. However, strictly linear dependencies 
    # (Research -> Synthesis -> Compliance -> Report) are often better enforced 
    # by the graph structure itself for this specific pipeline. 
    # But to satisfy "LLM should decide", we can give it the option.)
    
    # Actually, for this specific "Research Agent", the flow is quite linear.
    # But let's implement the Router pattern to allow for loops (e.g. Synthesis -> Research -> Synthesis).
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY not found. Using deterministic routing.")
        # Linear fallback: research -> synthesis -> citation -> compliance -> report -> end
        if next_step == "research":
            return {"next_step": "synthesis"}
        elif next_step == "synthesis":
            return {"next_step": "citation"}
        elif next_step == "citation":
            return {"next_step": "compliance"}
        elif next_step == "compliance":
            return {"next_step": "report"}
        elif next_step == "report":
            return {"next_step": "end"}
        else:
            return {"next_step": "end"}

    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        " following workers:  [research, synthesis, compliance, report].\n"
        "Given the following user request and current state, respond with the worker to act next.\n"
        "1. If research is needed or missing, choose 'research'.\n"
        "2. If research is done but no draft answer exists, choose 'synthesis'.\n"
        "3. If draft exists but not verified, choose 'citation'.\n"
        "4. If verified but not checked for compliance, choose 'compliance'.\n"
        "5. If compliance is done, choose 'report'.\n"
        "6. If everything is complete, choose 'FINISH'."
    )
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(Router)
    
    # Create a prompt with history
    # We simplify history for the router to avoid token limits
    response = await structured_llm.ainvoke(
        [{"role": "system", "content": system_prompt}] + messages[-5:]
    )
    
    next_node = response.next
    if next_node == "FINISH":
        next_node = "end"
        
    return {"next_step": next_node}

ingestion_agent = IngestionRetrievalAgent()
web_agent = WebResearchAgent()
synthesis_agent = SynthesisReportAgent()
citation_agent = CitationAgent()
compliance_agent = ComplianceAgent()


async def research_node(state: AgentState):
    """
    Performs RAG and Web Research.
    """
    print("--- Node: Research ---")
    job_id = state.get("job_id")
    
    query = state["messages"][0].content
    
    # 1. RAG
    # 1. RAG
    print(f"--- RAG Retrieval for: {query} (Job ID: {job_id}) ---")
    try:
        context = await ingestion_agent.call("retrieve", query, job_id=job_id)
        rag_count = len(context) if context else 0
        print(f"--- RAG Result: Retrieved {rag_count} chars ---")
    except Exception as e:
        print(f"--- RAG Error: {e} ---")
        context = ""
        rag_count = 0
    
    # 2. Web Search
    print(f"--- Web Search for: {query} ---")
    try:
        web_results = await web_agent.call("search", query, max_results=5)
    except Exception as e:
        web_results = [{"error": str(e)}]
        
    return {
        "research_data": {
            "context": context,
            "web_results": web_results
        },
        "messages": [AIMessage(content=f"Research complete. Retrieved {rag_count} chars from RAG and found {len(web_results)} web sources.")]
    }

async def synthesis_node(state: AgentState):
    """
    Synthesizes the answer using LLM.
    """
    print("--- Node: Synthesis ---")
    job_id = state.get("job_id")
    
    query = state["messages"][0].content
    data = state["research_data"]
    
    response_payload = await synthesis_agent.call(
        "generate_report",
        query,
        {
            "web_results": data.get("web_results", ""),
            "context": data.get("context", ""),
            "sections": [],
            "citations": [],
        },
    )
    
    # Manual merge of artifacts
    current_artifacts = state.get("artifacts", {}).copy()
    # Store the FULL structured report, not just the summary
    current_artifacts.update({"draft_answer": response_payload})
    
    # Format the full report for the chat output
    full_report_text = synthesis_agent.format_report(response_payload)
    
    return {
        "messages": [AIMessage(content=full_report_text)],
        "artifacts": current_artifacts
    }

async def citation_node(state: AgentState):
    """
    Verifies citations in the draft answer.
    """
    print("--- Node: Citation ---")
    job_id = state.get("job_id")
    
    draft = state["artifacts"].get("draft_answer", "")
    
    # If draft is a dict (structured report), format it to string for verification
    if isinstance(draft, dict):
        draft_text = synthesis_agent.format_report(draft)
    else:
        draft_text = draft
    data = state["research_data"]
    
    # Combine web results and context into a single list of sources for verification
    # Note: This is a simplification. Ideally, we'd have a structured list of sources.
    # For now, we'll pass the raw data and let the agent/tool handle parsing if needed,
    # or we can construct a simple list here.
    
    # Assuming web_results is a list of dicts as per recent fix
    sources = data.get("web_results", [])
    if isinstance(sources, list):
        # Ensure it matches what verify_citations_internal expects (id, title, text)
        # WebResearchAgent returns: title, date, quote, url
        formatted_sources = []
        for i, s in enumerate(sources):
            formatted_sources.append({
                "id": str(i+1),
                "title": s.get("title", "Unknown"),
                "text": s.get("quote", ""),
                "url": s.get("url", "")
            })
        sources = formatted_sources
    else:
        sources = []

    verification_result = await citation_agent.call("verify", draft_text, sources)
    
    # Manual merge of artifacts
    current_artifacts = state.get("artifacts", {}).copy()
    current_artifacts.update({"verification_result": verification_result})

    return {
        "messages": [AIMessage(content=f"Citation verification complete. Score: {verification_result.get('score', 0)}")],
        "artifacts": current_artifacts
    }

async def compliance_node(state: AgentState):
    """
    Checks for PII and compliance.
    """
    print("--- Node: Compliance ---")
    job_id = state.get("job_id")
    
    draft = state["artifacts"].get("draft_answer", "")
    
    # If draft is a dict (structured report), format it to string for redaction
    if isinstance(draft, dict):
        draft_text = synthesis_agent.format_report(draft)
    else:
        draft_text = draft
    
    # Redact PII
    # We force approval for demonstration of HITL
    
    # Check for PII first (mock check or real)
    # For this milestone, we interrupt to ask for confirmation
    
    # 1. Interrupt Graph
    # The value returned by interrupt() will be the payload provided when resuming
    approval_data = interrupt({"msg": "Approve redaction?"})
    
    print(f"--- Resume with data: {approval_data} ---")
    
    if approval_data.get("action") != "approve":
         return {
            "messages": [AIMessage(content="Compliance approval denied.")],
            "artifacts": {"final_answer": "[BLOCKED BY COMPLIANCE]"}
        }

    # 2. Proceed with enforcement
    compliance_result = await compliance_agent.call("redact", draft_text, require_approval=False)
    redacted = compliance_result["redacted_text"]
    
    # Manual merge of artifacts
    current_artifacts = state.get("artifacts", {}).copy()
    current_artifacts.update({"final_answer": redacted})
    
    return {
        "messages": [AIMessage(content="Compliance check complete. Approved.")],
        "artifacts": current_artifacts
    }

async def report_node(state: AgentState):
    print("\n" + "="*60)
    print("--- Node: Report Generation ---")
    print("="*60)
    
    job_id = state.get("job_id")
    # We manage session locally as it's not passed in state
    
    artifacts = state.get("artifacts", {})
    final_answer = artifacts.get("final_answer")

    if not final_answer:
        # fallback to draft
        draft = artifacts.get("draft_answer")
        if isinstance(draft, dict):
            final_answer = synthesis_agent.format_report(draft)
        elif isinstance(draft, str):
            final_answer = draft
        else:
            final_answer = "No content available for report."

    print(f"\n[REPORT] Generating PDF and DOCX...")
    print(f"  - Content length: {len(final_answer)} chars")
    print(f"  - Job ID: {job_id}")

    report_paths = {}
    report_id = state.get("report_id") # Check if passed, otherwise create
    print(f"  - Initial Report ID from state: {report_id}")
    
    with Session(engine) as db_session:
        # Fetch Job to get user_id and details
        from .models import Job, ReportStatus
        job = db_session.get(Job, job_id)
        if not job:
            print(f"  ✗ Job {job_id} not found!")
            return {"messages": [AIMessage(content="Job not found for report generation.")]}

        # Ensure we have a report record to update
        if not report_id:
            try:
                print("  - Creating new 'generating' report record...")
                initial_report = Report(
                    job_id=job_id, 
                    user_id=job.user_id,
                    title=f"Report: {job.name}",
                    type="comprehensive_report",
                    content={"summary": "Generating..."}, 
                    status=ReportStatus.generating
                )
                db_session.add(initial_report)
                db_session.commit()
                db_session.refresh(initial_report)
                report_id = initial_report.id
                print(f"  ✓ Created initial Report record: {report_id}")
            except Exception as e:
                print(f"  ✗ Failed to create initial report record: {e}")

        try:
            report_paths = await synthesis_agent.export(final_answer, job_id=job_id)
            print(f"  → Generated: {report_paths}")
            
            # Prepare structured content
            # If final_answer is already a dict, use it. If str, wrap it.
            if isinstance(final_answer, dict):
                structured_content = final_answer.copy()
            else:
                structured_content = {
                    "executive_summary": str(final_answer)[:500],
                    "full_text": str(final_answer)
                }
            
            # Ensure citations are present in content
            # We prioritize existing citations in the answer, but fallback/merge with research data
            if "citations" not in structured_content or not structured_content["citations"]:
                 structured_content["citations"] = state.get("research_data", {}).get("web_results", [])

            # ============================================
            # UPDATE DATABASE AFTER SUCCESSFUL GENERATION
            # ============================================
            if report_id:
                try:
                    # Update report status, file_url, and generated_at
                    stmt = update(Report).where(Report.id == report_id).values(
                        status=ReportStatus.completed,
                        file_url=report_paths.get('pdf', report_paths.get('docx', '')),
                        generated_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        content=structured_content,
                        report_metadata={
                            **artifacts.get("report_metadata", {}),
                            "report_paths": report_paths,
                            "compliance_assessment": artifacts.get("compliance_assessment"),
                            "verification_score": artifacts.get("verification_result", {}).get("score")
                        }
                    )
                    
                    db_session.execute(stmt)
                    db_session.commit()
                    
                    print(f"  ✓ Database updated: Report {report_id} marked as completed")
                    
                except Exception as db_error:
                    print(f"  ✗ DATABASE UPDATE ERROR: {db_error}")
                    db_session.rollback()
            else:
                print(f"  ⚠ No report_id available to update")
                
        except Exception as e:
            print(f"  ✗ REPORT ERROR: {e}")
            
            # Update status to failed if generation fails
            if report_id:
                try:
                    stmt = update(Report).where(Report.id == report_id).values(
                        status=ReportStatus.failed,
                        updated_at=datetime.utcnow()
                    )
                    
                    db_session.execute(stmt)
                    db_session.commit()
                    
                    print(f"  ✓ Database updated: Report {report_id} marked as failed")
                except Exception as db_error:
                    print(f"  ✗ DATABASE UPDATE ERROR: {db_error}")
                    db_session.rollback()

    # Update artifacts
    new_artifacts = artifacts.copy()
    new_artifacts["final_report"] = report_paths
    new_artifacts["report_id"] = report_id

    print("="*60 + "\n")
    
    return {
        "messages": [AIMessage(content=f"✓ Reports generated: {report_paths}")],
        "final_report": report_paths,
        "artifacts": new_artifacts,
    }

# --- Graph Construction ---

workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("research", research_node)
workflow.add_node("synthesis", synthesis_node)
workflow.add_node("citation", citation_node)
workflow.add_node("compliance", compliance_node)
workflow.add_node("report", report_node)

# Edges
workflow.set_entry_point("supervisor")

# Conditional edges from supervisor
def route_step(state: AgentState):
    return state["next_step"]

workflow.add_conditional_edges(
    "supervisor",
    route_step,
    {
        "research": "research",
        "synthesis": "synthesis",
        "citation": "citation",
        "compliance": "compliance",
        "report": "report",
        "end": END
    }
)

# Return to supervisor after each step
workflow.add_edge("research", "supervisor")
workflow.add_edge("synthesis", "supervisor")
workflow.add_edge("citation", "supervisor")
workflow.add_edge("compliance", "supervisor")
workflow.add_edge("report", "supervisor")

# Compile
checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

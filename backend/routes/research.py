from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.graph import graph  # Corrected import
import uuid
from typing import Optional, Dict, Any

router = APIRouter(prefix="/research", tags=["Research"])


class ResearchRequest(BaseModel):
    query: str
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    action: str   # "approve" or "deny"

@router.post("/run")
async def run_research(req: ResearchRequest):
    thread_id = req.thread_id or str(uuid.uuid4())

    init_state = {
        "messages": [],
        "next_step": "start",
        "job_id": None,
        "artifacts": {},
        "research_data": {},
        "final_report": {},
    }

    # Populate initial state with user query
    from langchain_core.messages import HumanMessage
    init_state["messages"] = [HumanMessage(content=req.query)]

    # Invoke graph with initial state
    result = await graph.ainvoke(
        init_state,
        config={"configurable": {"thread_id": thread_id}}
    )

    # Check for interrupt
    interrupt_event = result.get("__interrupt__")

    if interrupt_event:
        return {
            "thread_id": thread_id,
            "status": "WAITING_FOR_APPROVAL",
            "interrupt": interrupt_event[0].value, # Access value attribute of Interrupt object
        }

    return {
        "thread_id": thread_id,
        "status": "FINISHED",
        "result": result,
    }

@router.post("/resume/{thread_id}")
async def resume_research(thread_id: str, req: ResumeRequest):
    """
    Resume a previously paused graph with approval or denial.
    """
    # Resume payload to feed into the interrupt resume
    # The graph expects the value returned by interrupt() to be provided as 'resume'
    # In compliance_node: approval_data = interrupt({"msg": "Approve redaction?"})
    # So we pass {"action": req.action} as the resume value.
    
    from langgraph.types import Command
    
    resume_command = Command(resume={"action": req.action})

    try:
        result = await graph.ainvoke(
            resume_command,
            config={
                "configurable": {"thread_id": thread_id}
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if workflow stops again (rare case)
    interrupt_event = result.get("__interrupt__")
    if interrupt_event:
        return {
            "thread_id": thread_id,
            "status": "WAITING_FOR_APPROVAL",
            "interrupt": interrupt_event[0].value,
        }

    return {
        "thread_id": thread_id,
        "status": "FINISHED",
        "result": result,
    }

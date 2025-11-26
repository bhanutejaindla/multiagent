from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from ..database import get_session
from ..models import Job, JobStatus, User
from ..agent import ResearchAgent
from ..agents.ingestion_agent import IngestionRetrievalAgent
from ..agents.synthesis_agent import SynthesisReportAgent
import shutil
import os
import uuid
from langgraph.types import Command
from datetime import datetime

router = APIRouter(prefix="/research", tags=["Research"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

ingestor = IngestionRetrievalAgent()
agent_runner = ResearchAgent()
synthesis_agent = SynthesisReportAgent()

from ..auth import get_current_user

# ... imports ...

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    1. Upload PDF/DOCX.
    2. Create a new Job in DB linked to the authenticated user.
    3. Ingest document associated with this Job ID.
    """
    job = Job(
        name=f"Research: {file.filename}",
        type="research",
        status=JobStatus.pending,
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    job_id = str(job.id)
    
    # Save File
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Ingest
    chunks = 0
    try:
        text = await ingestor.extract_text(file_path)
        ingestion_result = await ingestor.ingest_text(text, source=file.filename, job_id=job_id)
        chunks = ingestion_result.get("chunks_added", 0)
        
        # Update Job Status
        job.status = JobStatus.running # Ready for query
        db.add(job)
        db.commit()
        
    except Exception as e:
        job.status = JobStatus.failed
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return {
        "message": "File uploaded and job created",
        "job_id": job.id,
        "filename": file.filename,
        "chunks": chunks
    }

@router.post("/chat")
async def chat_qa(
    job_id: int = Form(...),
    query: str = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Run the agent for a specific Job ID and Query.
    Ensures the job belongs to the authenticated user.
    """
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
    job.status = JobStatus.running
    db.add(job)
    db.commit()
    
    try:
        # Run agent with job_id as thread_id and pass job_id explicitly
        result = await agent_runner.run(query, thread_id=str(job_id), job_id=job_id)
        
        # Update job with result (optional, or just return it)
        # We could store the chat history or result in job.tasks
        
        job.status = JobStatus.completed
        db.add(job)
        db.commit()
        
        return {
            "job_id": job_id,
            "query": query,
            "answer": result.get("answer", "No answer generated"),
            "full_result": result
        }
        
    except Exception as e:
        job.status = JobStatus.failed
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate_report")
async def generate_report_route(
    job_id: int = Form(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate PDF/DOCX report for the job.
    Ensures the job belongs to the authenticated user.
    """
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to access this job")

    # Retrieve state from graph to get the final answer
    try:
        state = await agent_runner.graph.aget_state({"configurable": {"thread_id": str(job_id)}})
        if not state or not state.values:
             raise HTTPException(status_code=400, detail="No research data found for this job. Run chat first.")
             
        final_answer = state.values.get("artifacts", {}).get("final_answer")
        if not final_answer:
             # Fallback to draft answer
             final_answer = state.values.get("artifacts", {}).get("draft_answer")
             
        if not final_answer:
            raise HTTPException(status_code=400, detail="No answer available to generate report.")
            
        # Generate Report
        paths = await synthesis_agent.export(final_answer, job_id=job_id)
        
        return {
            "message": "Report generated",
            "paths": paths,
            "download_url_pdf": f"/research/download/{job_id}/pdf",
            "download_url_docx": f"/research/download/{job_id}/docx"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.get("/download/{job_id}/{file_type}")
async def download_report(job_id: int, file_type: str):
    filename = f"report_{job_id}.{file_type}"
    path = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, filename=filename)

@router.post("/resume")
async def resume_interrupt(thread_id: str, action: str):
    """
    Resume graph execution after an interrupt.
    """
    resume_command = Command(resume={"action": action})
    try:
        result = await agent_runner.graph.ainvoke(
            resume_command,
            config={"configurable": {"thread_id": thread_id}},
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
@router.get("/trace/{job_id}")
async def get_orchestration_trace(job_id: str):
    """
    Retrieve the execution trace (history) for a specific job.
    Returns the sequence of agent steps and their outputs.
    """
    try:
        # Retrieve state history from the graph
        # config = {"configurable": {"thread_id": job_id}}
        # history = []
        # async for state in agent_runner.graph.aget_state_history(config):
        #     history.append(state)
            
        # Since aget_state_history returns a generator of StateSnapshot, we need to process it.
        # We want to show the progression of steps.
        
        trace = []
        config = {"configurable": {"thread_id": job_id}}
        
        # Note: aget_state_history iterates from most recent to oldest
        async for snapshot in agent_runner.graph.aget_state_history(config):
            step_data = {
                "created_at": snapshot.created_at,
                "next": snapshot.next,
                "messages": [m.content for m in snapshot.values.get("messages", [])],
                "artifacts": snapshot.values.get("artifacts", {}),
                # "research_data": snapshot.values.get("research_data", {}) # Can be large
            }
            trace.append(step_data)
            
        # Reverse to show chronological order
        trace.reverse()
        
        return {"job_id": job_id, "trace": trace}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trace: {str(e)}")

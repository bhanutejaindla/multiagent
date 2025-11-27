from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlmodel import Session, select, SQLModel
from ..database import get_session
from ..models import Report, User, Job, ReportStatus
from ..auth import get_current_user
from ..agent import ResearchAgent
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

router = APIRouter(prefix="/reports", tags=["Reports"])
agent_runner = ResearchAgent()

from pydantic import BaseModel

class ReportResponse(BaseModel):
    id: int
    title: str
    type: str
    status: ReportStatus
    content: Optional[Union[Dict[str, Any], str]] = None
    file_url: Optional[str] = None
    version: int
    user_id: int
    job_id: Optional[int]
    report_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.get("/{job_id}", response_model=ReportResponse)
async def get_report(
    job_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Fetch report by job_id (get the latest one)
    statement = select(Report).where(Report.job_id == job_id).order_by(Report.created_at.desc())
    results = db.execute(statement)
    report = results.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this job")
    
    # Authorization check (via Job)
    if report.job.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return report

@router.get("/{job_id}/download")
async def download_report(
    job_id: int,
    format: str = "pdf",
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Fetch report by job_id
    statement = select(Report).where(Report.job_id == job_id).order_by(Report.created_at.desc())
    results = db.execute(statement)
    report = results.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this job")
        
    if report.job.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Determine file path based on format
    file_path = None
    
    # Check metadata for specific format paths
    if report.report_metadata and "report_paths" in report.report_metadata:
        paths = report.report_metadata["report_paths"]
        if format.lower() in paths:
            file_path = paths[format.lower()]
            
    # Fallback to main file_url if it matches the format or if no specific path found
    if not file_path and report.file_url:
        if report.file_url.lower().endswith(f".{format.lower()}"):
            file_path = report.file_url
        # If default request (pdf) and file_url exists but no extension check (legacy), might default to it
        elif format.lower() == 'pdf': 
             file_path = report.file_url

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"{format.upper()} report file not found")

    filename = os.path.basename(file_path)
    return FileResponse(file_path, filename=filename)

@router.get("", response_model=List[ReportResponse])
async def get_reports(
    job_id: int = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    query = select(Report)
    if job_id:
        query = query.where(Report.job_id == job_id)
    
    # Filter by user if not admin
    if current_user.role != "ADMIN":
        query = query.join(Report.job).where(Report.job.user_id == current_user.id)
        
    reports = db.execute(query).scalars().all()
    return reports

@router.put("/{job_id}", response_model=ReportResponse)
async def update_report(
    job_id: int,
    report_update: dict,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Fetch report by job_id
    statement = select(Report).where(Report.job_id == job_id).order_by(Report.created_at.desc())
    results = db.execute(statement)
    report = results.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this job")
        
    if report.job.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if "content" in report_update:
        # Create a new report version instead of overwriting
        new_version = report.version + 1
        
        new_report = Report(
            job_id=report.job_id,
            user_id=report.user_id,
            title=report.title,
            type=report.type,
            content=report_update["content"],
            version=new_version,
            status=ReportStatus.completed, # Assuming edited report is 'completed' (or maybe 'pending' if it needs regen?)
            # file_url is reset as content changed, needs regeneration
            report_metadata=report.report_metadata # Copy metadata? Or reset? Maybe keep verification scores but mark as stale?
        )
        
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        return new_report
        
    # If not updating content (e.g. just status), maybe update in place? 
    # But for now, assuming this endpoint is mainly for content edits.
    return report

@router.post("/{job_id}/chat")
async def chat_report(
    job_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the context of a specific report (via its Job).
    """
    # Verify report exists for this job
    statement = select(Report).where(Report.job_id == job_id).order_by(Report.created_at.desc())
    results = db.execute(statement)
    report = results.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this job")
        
    if report.job.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    query = body.get("message")
    if not query:
        raise HTTPException(status_code=400, detail="Message is required")
        
    # Run agent with job_id as thread_id
    try:
        # Format report content for context
        context = ""
        if isinstance(report.content, dict):
            # Use the synthesis agent's formatter if available, or simple string conversion
            try:
                context = agent_runner.orchestrator.synthesis_agent.format_report(report.content)
            except:
                context = str(report.content)
        else:
            context = str(report.content)

        answer = await agent_runner.chat_with_context(query, context)
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

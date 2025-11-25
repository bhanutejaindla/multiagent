from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from typing import List, Dict, Any
from ..database import get_session
from ..models import User, Job, JobStatus, UserRole
from ..auth import get_current_user
from mcp_servers.ingestion.server import read_pdf, read_docx
from mcp_servers.research.server import web_search
from mcp_servers.compliance.server import redact_pii
from mcp_servers.citation_validation.server import verify_citations_internal

router = APIRouter(prefix="/admin", tags=["admin"])

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

@router.get("/stats")
async def get_system_stats(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin_user)
):
    """
    Get system-wide statistics: total jobs, active jobs, completed jobs, total users.
    """
    total_jobs = session.exec(select(func.count(Job.id))).one()
    active_jobs = session.exec(select(func.count(Job.id)).where(Job.status == JobStatus.running)).one()
    completed_jobs = session.exec(select(func.count(Job.id)).where(Job.status == JobStatus.completed)).one()
    failed_jobs = session.exec(select(func.count(Job.id)).where(Job.status == JobStatus.failed)).one()
    total_users = session.exec(select(func.count(User.id))).one()
    
    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "total_users": total_users
    }

@router.get("/users", response_model=List[User])
async def get_users(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin_user)
):
    """
    List all users.
    """
    users = session.exec(select(User)).all()
    return users

@router.get("/tools")
async def get_tools_status(
    admin: User = Depends(get_current_admin_user)
):
    """
    List available MCP tools and their status (mock check).
    """
    # In a real system, we might ping the MCP servers.
    # Here we just list what we have integrated.
    return [
        {"name": "ingestion", "status": "available", "functions": ["read_pdf", "read_docx"]},
        {"name": "research", "status": "available", "functions": ["web_search"]},
        {"name": "compliance", "status": "available", "functions": ["redact_pii"]},
        {"name": "citation", "status": "available", "functions": ["verify_citations_internal"]},
    ]

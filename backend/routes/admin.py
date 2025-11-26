from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from typing import List, Dict, Any
from ..database import get_session
from ..models import User, Job, JobStatus, UserRole, ToolState
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

@router.put("/users/{user_id}/quota")
async def update_user_quota(
    user_id: int,
    quota: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin_user)
):
    """
    Update a user's job quota.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.quota_limit = quota
    session.add(user)
    session.commit()
    return {"message": "Quota updated", "user_id": user_id, "new_quota": quota}

@router.post("/tools/{tool_name}/toggle")
async def toggle_tool(
    tool_name: str,
    enabled: bool,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin_user)
):
    """
    Enable or disable a tool.
    """
    statement = select(ToolState).where(ToolState.name == tool_name)
    tool_state = session.exec(statement).first()
    
    if not tool_state:
        tool_state = ToolState(name=tool_name, is_enabled=enabled)
    else:
        tool_state.is_enabled = enabled
        
    session.add(tool_state)
    session.commit()
    return {"message": f"Tool {tool_name} {'enabled' if enabled else 'disabled'}"}

@router.get("/tools")
async def get_tools_status(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin_user)
):
    """
    List available MCP tools and their status.
    """
    # Define available tools
    tools_def = [
        {"name": "ingestion", "functions": ["read_pdf", "read_docx"]},
        {"name": "research", "functions": ["web_search"]},
        {"name": "compliance", "functions": ["redact_pii"]},
        {"name": "citation", "functions": ["verify_citations_internal"]},
    ]
    
    result = []
    for tool in tools_def:
        # Check DB for status override
        statement = select(ToolState).where(ToolState.name == tool["name"])
        tool_state = session.exec(statement).first()
        
        is_enabled = tool_state.is_enabled if tool_state else True # Default to enabled
        
        result.append({
            "name": tool["name"],
            "status": "available" if is_enabled else "disabled",
            "functions": tool["functions"],
            "is_enabled": is_enabled
        })
        
    return result

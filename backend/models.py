from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    full_name: Optional[str] = None
    name: str # Keeping for backward compatibility or display name
    quota_limit: int = Field(default=10)
    jobs: List["Job"] = Relationship(back_populates="user")

class ToolState(SQLModel, table=True):
    __tablename__ = "tool_states"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    is_enabled: bool = Field(default=True)

class Agent(SQLModel, table=True):
    __tablename__ = "agents"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    current_job_id: Optional[int] = Field(default=None, foreign_key="jobs.id")
    current_job: Optional["Job"] = Relationship(back_populates="agents")

class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str
    status: JobStatus = Field(default=JobStatus.pending)
    user_id: int = Field(foreign_key="users.id", index=True)
    user: Optional[User] = Relationship(back_populates="jobs")
    progress: float = Field(default=0.0)
    tasks: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    agents: List[Agent] = Relationship(back_populates="current_job")

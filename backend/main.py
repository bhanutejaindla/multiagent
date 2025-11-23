from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
import asyncio
from .rag import add_document
from .database import engine
from datetime import datetime
# Direct imports from MCP servers
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_servers.ingestion.server import read_pdf, read_docx
from contextlib import asynccontextmanager
from .database import create_db_and_tables, get_session
from .models import Job, User, JobStatus
from .kafka_client import consume_events, KafkaProducerClient, TOPIC_NAME
from sqlmodel import Session, select
from mcp_servers.research.server import web_search
from mcp_servers.compliance.server import redact_pii
from mcp_servers.citation_validation.server import verify_citations_internal, parse_web_search_results
from .rag import add_document, query_documents
from typing import List, Dict, Any
from fastapi import Depends, status

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # Start Kafka Consumer in background
    task = asyncio.create_task(consume_events())
    yield
    task.cancel()

app = FastAPI(title="Research Agent Platform API", lifespan=lifespan)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"message": "Research Agent Platform API is running"}

@app.post("/chat")
async def chat_only(request: ChatRequest):
    try:
        # Create a new job in DB for this chat request
        with Session(engine) as session:
            # Ensure a user exists for this demo
            statement = select(User).where(User.name == "demo_user")
            user = session.exec(statement).first()
            if not user:
                user = User(name="demo_user")
                session.add(user)
                session.commit()
                session.refresh(user)
                
            job = Job(type="chat", user_id=user.id, status=JobStatus.running)
            session.add(job)
            session.commit()
            session.refresh(job)
            
        # Use Linear Agent Pipeline with direct calls
        from .agent import run_agent
        # generate_report=False for simple chat
        result = await run_agent(request.message, job_id=job.id, generate_report=False)
        return {
            "response": result["answer"], 
            "job_id": job.id
        }
    except Exception as e:
        # Fallback if LLM/Agent fails
        return {"response": f"Agent Error: {str(e)}. (Ensure OpenAI Key is set for this demo)"}

@app.post("/generate-document")
async def chat(request: ChatRequest):
    try:
        # Create a new job in DB for this chat request
        with Session(engine) as session:
            # Ensure a user exists for this demo
            statement = select(User).where(User.name == "demo_user")
            user = session.exec(statement).first()
            if not user:
                user = User(name="demo_user")
                session.add(user)
                session.commit()
                session.refresh(user)
                
            job = Job(type="chat", user_id=user.id, status=JobStatus.running)
            session.add(job)
            session.commit()
            session.refresh(job)
            
        # Use Linear Agent Pipeline with direct calls
        from .agent import run_agent
        result = await run_agent(request.message, job_id=job.id, generate_report=True)
        return {
            "response": result["answer"], 
            "reports": result["reports"],
            "job_id": job.id
        }
    except Exception as e:
        # Fallback if LLM/Agent fails
        return {"response": f"Agent Error: {str(e)}. (Ensure OpenAI Key is set for this demo)"}

# --- Auth Routes ---
from fastapi.security import OAuth2PasswordRequestForm
from .auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from datetime import timedelta

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "USER"  # "USER" or "ADMIN"

class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/auth/signup", response_model=Token)
async def signup(user_data: UserCreate, session: Session = Depends(get_session)):
    from .models import UserRole
    
    # Validate role
    if user_data.role not in ["USER", "ADMIN"]:
        raise HTTPException(status_code=400, detail="Role must be 'USER' or 'ADMIN'")
    
    # Check if email exists
    statement = select(User).where(User.email == user_data.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    statement = select(User).where(User.username == user_data.username)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    hashed_pw = get_password_hash(user_data.password)
    user_role = UserRole.USER if user_data.role == "USER" else UserRole.ADMIN
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pw,
        role=user_role,
        name=user_data.username  # Use username as display name
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # Generate token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email, "username": new_user.username, "role": new_user.role}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    statement = select(User).where(User.email == form_data.username)
    user = session.exec(statement).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Tool Testing Routes ---

class ResearchRequest(BaseModel):
    query: str

@app.post("/test/research")
async def test_research(request: ResearchRequest):
    results = await asyncio.to_thread(web_search, request.query, max_results=3)
    return {"results": results}

class ComplianceRequest(BaseModel):
    text: str

@app.post("/test/compliance")
async def test_compliance(request: ComplianceRequest):
    redacted = await asyncio.to_thread(redact_pii, request.text)
    return {"original": request.text, "redacted": redacted}

class CitationRequest(BaseModel):
    draft_answer: str
    sources: List[Dict[str, Any]]

@app.post("/test/citation")
async def test_citation(request: CitationRequest):
    verification = await asyncio.to_thread(
        verify_citations_internal, 
        request.draft_answer, 
        request.sources
    )
    return verification

class RagAddRequest(BaseModel):
    text: str
    source: str

@app.post("/test/rag/add")
async def test_rag_add(request: RagAddRequest):
    count = add_document(request.text, request.source)
    return {"chunks_added": count}

class RagQueryRequest(BaseModel):
    query: str

@app.post("/test/rag/query")
async def test_rag_query(request: RagQueryRequest):
    context = query_documents(request.query)
    return {"context": context}


@app.post("/jobs")
async def create_job(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Create a new job in DB
    job = Job(type="research", user_id=current_user.id, name="New Research Job")
    session.add(job)
    session.commit()
    session.refresh(job)
    
    # Send initial event
    producer = KafkaProducerClient()
    await producer.start()
    try:
        event = {
            "job_id": job.id,
            "status": "pending",
            "timestamp": datetime.utcnow().isoformat()
        }
        await producer.send_message(TOPIC_NAME, event)
    finally:
        await producer.stop()
        
    return {"job_id": job.id, "status": job.status}

@app.get("/jobs", response_model=List[Job])
async def get_jobs(
    skip: int = 0, 
    limit: int = 10, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Job).where(Job.user_id == current_user.id).offset(skip).limit(limit).order_by(Job.created_at.desc())
    jobs = session.exec(statement).all()
    return jobs

@app.get("/jobs/{job_id}", response_model=Job)
async def get_job(
    job_id: int, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Job).where(Job.id == job_id)
    job = session.exec(statement).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to view this job")
    return job

@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # 1. Create Job
    job = Job(
        name=f"Ingest {file.filename}",
        type="ingestion",
        status=JobStatus.running,
        user_id=current_user.id,
        progress=0.0,
        tasks=[{"step": "upload", "status": "completed"}]
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    
    upload_dir = "uploads"
    file_location = os.path.join(upload_dir, file.filename)
    os.makedirs(upload_dir, exist_ok=True)
    
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Update Job: File Saved
        job.progress = 0.2
        job.tasks.append({"step": "save_file", "status": "completed", "path": file_location})
        session.add(job)
        session.commit()
        
        # Trigger ingestion tool directly
        text_content = ""
        if file.filename.endswith(".pdf"):
            text_content = await asyncio.to_thread(read_pdf, os.path.abspath(file_location))
        elif file.filename.endswith(".docx"):
            text_content = await asyncio.to_thread(read_docx, os.path.abspath(file_location))
        else:
            job.status = JobStatus.failed
            job.tasks.append({"step": "extract_text", "status": "failed", "error": "Unsupported file type"})
            session.add(job)
            session.commit()
            return {"message": "File saved, but type not supported for extraction.", "path": file_location}
            
        # Update Job: Text Extracted
        job.progress = 0.6
        job.tasks.append({"step": "extract_text", "status": "completed", "length": len(text_content)})
        session.add(job)
        session.commit()

        # Index in Vector DB
        num_chunks = await asyncio.to_thread(add_document, text_content, source=file.filename)
        
        # Update Job: Completed
        job.status = JobStatus.completed
        job.progress = 1.0
        job.tasks.append({"step": "index_document", "status": "completed", "chunks": num_chunks})
        session.add(job)
        session.commit()
            
        return {
            "message": "File ingested and indexed successfully", 
            "job_id": job.id,
            "chunks_added": num_chunks,
            "content_preview": text_content[:200]
        }
    except Exception as e:
        job.status = JobStatus.failed
        job.progress = 0.0
        job.tasks.append({"step": "ingestion", "status": "failed", "error": str(e)})
        session.add(job)
        session.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

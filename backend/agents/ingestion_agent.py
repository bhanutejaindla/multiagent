from __future__ import annotations

from typing import Dict, Any
import asyncio

from .base import BaseAgent, AgentCard
from ..rag import add_document, query_documents


class IngestionRetrievalAgent(BaseAgent):
    """Handles document ingestion and retrieval (RAG)."""

    def __init__(self) -> None:
        super().__init__(
            AgentCard(
                name="ingestion_rag_agent",
                description="Ingests documents, maintains vector store and serves retrieval results.",
                capabilities=[
                    "ingest_text",
                    "retrieve",
                ],
                rate_limit_per_minute=15,
            )
        )

    async def ingest_text(self, content: str, source: str, job_id: int | str | None = None) -> Dict[str, Any]:
        chunks_added = await asyncio.to_thread(add_document, content, source=source, job_id=str(job_id) if job_id else None)
        return {"chunks_added": chunks_added}

    async def retrieve(self, query: str, top_k: int = 5, job_id: int | str | None = None) -> str:
        """Return raw retrieved text block."""
        result = await asyncio.to_thread(query_documents, query, n_results=top_k, job_id=str(job_id) if job_id else None)
        return result

    async def extract_text(self, file_path: str) -> str:
        """Extracts text from PDF or DOCX files."""
        ext = file_path.lower().split('.')[-1]
        text = ""
        try:
            if ext == "pdf":
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
            elif ext == "docx":
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
            elif ext == "txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                raise ValueError("Unsupported file type")
        except Exception as e:
            print(f"Extraction failed: {e}")
            raise e
            
        return text


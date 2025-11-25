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

    async def ingest_text(self, content: str, source: str, job_id: int | None = None) -> Dict[str, Any]:
        chunks_added = await asyncio.to_thread(add_document, content, source=source)
        return {"chunks_added": chunks_added}

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        """Return raw retrieved text block."""
        result = await asyncio.to_thread(query_documents, query)
        return result


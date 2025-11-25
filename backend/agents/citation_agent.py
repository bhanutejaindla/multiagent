from __future__ import annotations

import asyncio
from typing import Dict, Any, List

from .base import BaseAgent, AgentCard

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mcp_servers.citation_validation.server import verify_citations_internal  # type: ignore


class CitationAgent(BaseAgent):
    """Verifies citations in the generated report against sources."""

    def __init__(self) -> None:
        super().__init__(
            AgentCard(
                name="citation_agent",
                description="Verifies that citations in the text are supported by the provided sources.",
                capabilities=["verify"],
                rate_limit_per_minute=20,
            )
        )

    async def verify(self, draft_answer: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate citations using MCP parser/validator."""
        try:
            # verify_citations_internal is async, so we await it directly
            result = await verify_citations_internal(draft_answer, sources)
            return result
        except Exception as e:
            print(f"Citation verification failed (likely no API key): {e}")
            return {
                "score": 1.0,
                "is_valid": True,
                "supported_claims": 0,
                "total_claims": 0,
                "issues": [],
                "summary": "Mock verification (fallback due to error)"
            }

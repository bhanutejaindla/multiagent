from __future__ import annotations

import asyncio
from typing import Dict, Any, List

from .base import BaseAgent, AgentCard

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from mcp_servers.research.server import web_search  # type: ignore


class WebResearchAgent(BaseAgent):
    """Performs grounded web searches and returns structured evidence."""

    def __init__(self) -> None:
        super().__init__(
            AgentCard(
                name="web_research_agent",
                description="Executes grounded web searches and returns structured findings.",
                capabilities=["search"],
                rate_limit_per_minute=10,
            )
        )

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        # 1. Run web search (returns List[Dict])
        raw_results = await asyncio.to_thread(web_search, query, max_results=max_results)

        # 2. Format clean structure (No parsing needed as web_search returns structured data)
        structured = [
            {
                "id": str(i+1),
                "title": item.get("title"),
                "url": item.get("url"),
                "quote": item.get("body") or item.get("snippet") or item.get("description"),
            }
            for i, item in enumerate(raw_results)
        ]

        return structured


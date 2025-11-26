from __future__ import annotations

import asyncio
from typing import Dict, Any

from .base import BaseAgent, AgentCard

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mcp_servers.compliance.server import redact_pii  # type: ignore


class ComplianceAgent(BaseAgent):
    """Detects PII/sensitive content and enforces compliance policies."""

    def __init__(self) -> None:
        super().__init__(
            AgentCard(
                name="compliance_agent",
                description="Applies compliance rules, redacts sensitive content, manages policy approvals.",
                capabilities=["redact"],
                rate_limit_per_minute=20,
            )
        )

    async def redact(self, text: str, require_approval: bool = False) -> Dict[str, Any]:
        """
        Redact sensitive information using MCP compliance tool.
        """
        redacted = await asyncio.to_thread(redact_pii, text)

        return {
            "redacted_text": redacted,
            "approval_required": require_approval,
        }

    async def enforce(self, text: str, require_approval: bool = False) -> Dict[str, Any]:
        """Alias for redact to maintain compatibility."""
        return await self.redact(text, require_approval)

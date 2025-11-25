from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
import time
import asyncio
import structlog

logger = structlog.get_logger()


@dataclass
class AgentCard:
    """Metadata describing an agent in the A2A discovery layer."""

    name: str
    description: str
    capabilities: List[str]
    auth_required: bool = True
    rate_limit_per_minute: int = 60
    version: str = "1.0.0"
    contact: str | None = None
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """Base class for all agents with logging + rate limiting."""

    def __init__(self, card: AgentCard) -> None:
        self.card = card
        self._last_called = 0
        self._min_interval = 60 / self.card.rate_limit_per_minute

    # -------------------------
    # Rate Limit Handler
    # -------------------------
    async def _check_rate_limit(self):
        now = time.time()
        elapsed = now - self._last_called
        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            logger.info("rate_limit_wait", agent=self.card.name, wait=wait_time)
            await asyncio.sleep(wait_time)
        self._last_called = time.time()

    # -------------------------
    # Standard Agent Call Wrapper
    # -------------------------
    async def call(self, method: str, *args, **kwargs):
        """Wraps all agent method calls with rate limiting + logging."""
        if not hasattr(self, method):
            raise AttributeError(f"Agent '{self.card.name}' has no method '{method}'")

        await self._check_rate_limit()

        logger.info(
            "agent_call_start",
            agent=self.card.name,
            method=method,
            args=args,
            kwargs=kwargs,
        )

        fn = getattr(self, method)
        # Assuming all agent methods are async
        result = await fn(*args, **kwargs)

        logger.info(
            "agent_call_complete",
            agent=self.card.name,
            method=method,
            result=result,
        )

        return result

    def get_agent_card(self) -> AgentCard:
        return self.card




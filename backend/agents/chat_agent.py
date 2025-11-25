from __future__ import annotations

from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

from .base import BaseAgent, AgentCard


class ChatAgent(BaseAgent):
    """Maintains chat history and provides conversational summaries."""

    def __init__(self) -> None:
        super().__init__(
            AgentCard(
                name="chat_agent",
                description="Maintains conversation history and summarizes threads.",
                capabilities=["store_history", "summarize_thread", "chat_memory"],
            )
        )
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.history: Dict[str, List[BaseMessage]] = {}

    # ---------------------------------------------------------------
    # 1) Add message to conversation history
    # ---------------------------------------------------------------
    def append_message(self, thread_id: str, message: BaseMessage) -> None:
        self.history.setdefault(thread_id, []).append(message)

    # ---------------------------------------------------------------
    # 2) Retrieve full chat history for a thread
    # ---------------------------------------------------------------
    def get_history(self, thread_id: str) -> List[BaseMessage]:
        return self.history.get(thread_id, [])

    # ---------------------------------------------------------------
    # 3) Summarize the conversation
    # ---------------------------------------------------------------
    async def summarize(self, thread_id: str) -> str:
        history = self.get_history(thread_id)
        if not history:
            return "No conversation yet."

        # Use the last 6 messages for short-memory summarization
        recent_history = history[-6:]

        response = await self.llm.ainvoke(recent_history)
        return response.content

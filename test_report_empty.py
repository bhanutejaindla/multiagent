import asyncio
import sys
import os
from langchain_core.messages import HumanMessage
from langgraph.types import Command

# Ensure backend is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.graph import graph

async def test_report():
    print("\n==== RUNNING REPORT TEST ====\n")

    config = {"configurable": {"thread_id": "test_report_thread"}}

    # Mimic API initial state
    initial_state = {
        "messages": [HumanMessage(content="Explain the impact of AI in healthcare")],
        "next_step": "start",
        "job_id": None,
        "artifacts": {},
        "research_data": {},
        "final_report": {}
    }

    print("--- 1. Starting Graph Execution ---")
    result = await graph.ainvoke(initial_state, config=config)
    
    print("\n--- 2. Graph Interrupted ---")
    
    resume_command = Command(resume={"action": "approve"})
    
    print("\n--- 3. Resuming Graph ---")
    final_result = await graph.ainvoke(resume_command, config=config)

    print("\n==== FINAL GRAPH STATE ====\n")
    print(final_result)

    print("\n==== FINAL REPORT ====\n")
    print(final_result.get("final_report", "MISSING"))

if __name__ == "__main__":
    asyncio.run(test_report())

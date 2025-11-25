import asyncio
import sys
import os
from langchain_core.messages import HumanMessage
from langgraph.types import Command

# Ensure backend is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.graph import graph

async def test_hitl():
    print("\n==== RUNNING HITL TEST ====\n")

    # Use a thread_id to persist state for resumption
    config = {"configurable": {"thread_id": "test_thread_1"}}

    # Build initial state
    initial_state = {
        "messages": [HumanMessage(content="Explain the impact of AI in healthcare")],
        "next_step": "start",
        "job_id": 123, # Mock job ID
        "artifacts": {},
        "research_data": {},
        "final_report": {}
    }

    print("--- 1. Starting Graph Execution ---")
    # Run until interrupt
    # We use stream to see updates, or invoke. invoke will stop at interrupt.
    result = await graph.ainvoke(initial_state, config=config)
    
    print("\n--- 2. Graph Interrupted (Expected) ---")
    print("State at interrupt:", result)
    
    # Check if we have a final answer yet (should be empty or partial)
    print("Draft Answer:", result.get("artifacts", {}).get("draft_answer", "N/A"))
    print("Final Answer:", result.get("artifacts", {}).get("final_answer", "N/A"))

    print("\n--- 3. Resuming Graph with Approval ---")
    # Resume with approval command
    # The interrupt key was "msg", but we just need to pass the value expected by the variable assigned to interrupt()
    # In compliance_node: approval_data = interrupt(...)
    
    resume_command = Command(resume={"action": "approve"})
    
    # Run again with the same config (thread_id) and the resume command
    final_result = await graph.ainvoke(resume_command, config=config)

    print("\n==== FINAL GRAPH STATE ====\n")
    # print(final_result)

    print("\n==== FINAL ANSWER ====\n")
    print(final_result.get("artifacts", {}).get("final_answer", "(No answer)"))

    print("\n==== REPORT PATHS ====\n")
    print(final_result.get("final_report", {}))

if __name__ == "__main__":
    asyncio.run(test_hitl())

import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from backend.a2a import A2AClient, TaskRegistry, RESEARCH_AGENT_CARD, AgentTask

# Mock KafkaProducerClient
class MockProducer:
    async def start(self):
        print("[Mock] Producer started")

    async def stop(self):
        print("[Mock] Producer stopped")

    async def send_message(self, topic: str, message: dict):
        print(f"[Mock] Sent to {topic}: {message}")
        # Simulate receiving the task on the other side
        if message["type"] == "task_request":
            task_data = message["task"]
            print(f"[Mock] Task received: {task_data['task_id']}")

async def test_a2a_flow():
    print("--- Testing A2A Flow ---")
    
    # Patch the producer in a2a module
    with patch('backend.a2a.KafkaProducerClient', side_effect=MockProducer):
        client = A2AClient(source_agent_id="supervisor_agent")
        
        # 1. Send Task
        print("\n1. Sending Task...")
        task_id = await client.send_task(
            target_agent_card=RESEARCH_AGENT_CARD,
            capability="web_search",
            input_data={"query": "LangGraph tutorial"}
        )
        
        # 2. Verify Registry
        print("\n2. Verifying Registry...")
        task = TaskRegistry.get_task(task_id)
        if task:
            print(f"✓ Task found in registry: {task.task_id} (Status: {task.status})")
        else:
            print("✗ Task NOT found in registry")
            
        # 3. Simulate Task Update (e.g. from consumer)
        print("\n3. Updating Task Status...")
        TaskRegistry.update_task(task_id, status="running")
        task = TaskRegistry.get_task(task_id)
        print(f"Task Status: {task.status}")
        
        TaskRegistry.update_task(task_id, status="completed", result={"url": "http://example.com"})
        task = TaskRegistry.get_task(task_id)
        print(f"Task Status: {task.status}")
        print(f"Task Result: {task.result}")
        
        if task.status == "completed" and task.result:
            print("\n✓ A2A Flow Verified Successfully")

if __name__ == "__main__":
    asyncio.run(test_a2a_flow())

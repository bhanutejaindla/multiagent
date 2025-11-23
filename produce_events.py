import asyncio
import json
from backend.kafka_client import KafkaProducerClient, TOPIC_NAME
from datetime import datetime

async def produce_from_file(file_path: str):
    producer = KafkaProducerClient()
    await producer.start()
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    # Ensure timestamp is present
                    if "timestamp" not in event:
                        event["timestamp"] = datetime.utcnow().isoformat()
                    
                    print(f"Sending event: {event}")
                    await producer.send_message(TOPIC_NAME, event)
                    await asyncio.sleep(1) # Simulate delay
    finally:
        await producer.stop()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python produce_events.py <file_path>")
        # Create a dummy file for testing if not provided
        with open("events.jsonl", "w") as f:
            # Note: Job IDs must match what's in the DB. 
            # Since we can't know the ID ahead of time, we'll use a placeholder '1' 
            # assuming the first job created will have ID 1.
            f.write('{"job_id": 1, "status": "running", "progress": 0.5}\n')
            f.write('{"job_id": 1, "status": "completed", "progress": 1.0}\n')
        print("Created dummy events.jsonl with Job ID 1")
        asyncio.run(produce_from_file("events.jsonl"))
    else:
        asyncio.run(produce_from_file(sys.argv[1]))

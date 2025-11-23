import asyncio
import json
from datetime import datetime
from typing import Callable, Any

# Mock storage for events
MOCK_EVENTS = []

class KafkaProducerClient:
    def __init__(self):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send_message(self, topic: str, message: dict):
        print(f"[Mock Kafka] Sending to {topic}: {message}")
        MOCK_EVENTS.append(message)
        # Simulate consumer processing immediately for demo
        await process_mock_event(message)

async def process_mock_event(event: dict):
    # This mimics the consumer logic
    from .database import engine
    from .models import Job
    from sqlmodel import Session, select
    
    job_id = event.get("job_id")
    status = event.get("status")
    progress = event.get("progress")
    
    if job_id:
        with Session(engine) as session:
            statement = select(Job).where(Job.id == int(job_id))
            results = session.exec(statement)
            job = results.first()
            
            if job:
                if status:
                    job.status = status
                if progress is not None:
                    job.progress = progress
                
                job.updated_at = datetime.utcnow()
                session.add(job)
                session.commit()
                session.refresh(job)
                print(f"[Mock Consumer] Updated Job {job_id} status to {job.status}")

async def consume_events():
    print("[Mock Kafka] Consumer started (listening to mock events)")
    while True:
        await asyncio.sleep(1)

TOPIC_NAME = "agent.job.events"

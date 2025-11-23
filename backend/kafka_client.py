from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import asyncio
from sqlmodel import Session, select
from .database import engine
from .models import Job
from datetime import datetime

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC_NAME = "agent.job.events"

class KafkaProducerClient:
    def __init__(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def send_message(self, topic: str, message: dict):
        await self.producer.send_and_wait(topic, message)

async def consume_events():
    consumer = AIOKafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="agent-consumer-group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = msg.value
            print(f"Received event: {event}")
            
            # Update Job status in DB
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
                        print(f"Updated Job {job_id} status to {job.status}")
                    else:
                        print(f"Job {job_id} not found")
    finally:
        await consumer.stop()

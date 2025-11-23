import requests
import time
import sys
from sqlmodel import Session, select, create_engine
from backend.models import Job
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./multiagent_db.sqlite")
engine = create_engine(DATABASE_URL)

def test_chat_flow():
    url = "http://localhost:8000/chat"
    payload = {"message": "Who is the present CM of Telangana state?"}
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        print("Response received:")
        print(data)
        
        job_id = data.get("job_id")
        if not job_id:
            print("Error: No job_id returned")
            return

        print(f"Monitoring Job {job_id}...")
        for _ in range(10): # Poll for 10 seconds
            with Session(engine) as session:
                job = session.get(Job, job_id)
                if job:
                    print(f"Job Status: {job.status}, Progress: {job.progress}")
                    if job.status == "completed" or job.progress == 1.0:
                        print("Job completed successfully!")
                        break
                else:
                    print("Job not found in DB")
            time.sleep(1)
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_chat_flow()

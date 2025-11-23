import requests
import os

BASE_URL = "http://localhost:8000"

def test_dashboard_api():
    print("\n--- Testing Dashboard API ---")
    
    # 0. Signup (to ensure user exists)
    signup_url = f"{BASE_URL}/auth/signup"
    signup_data = {
        "username": "ingest_user",
        "email": "ingest@example.com",
        "password": "password123",
        "role": "USER"
    }
    try:
        print("0. Signing up...")
        response = requests.post(signup_url, json=signup_data)
        if response.status_code == 400:
            print("User already exists, proceeding to login.")
        else:
            response.raise_for_status()
            print("Signup successful.")
    except Exception as e:
        print(f"Signup failed: {e}")
        # Continue to login anyway

    # 1. Login to get token
    login_url = f"{BASE_URL}/auth/login"
    login_data = {
        "username": "ingest@example.com", 
        "password": "password123"
    }
    token = ""
    try:
        print("1. Logging in...")
        response = requests.post(login_url, data=login_data)
        response.raise_for_status()
        token = response.json()["access_token"]
        print("Login successful.")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1.5 Create a Job
    jobs_create_url = f"{BASE_URL}/jobs"
    try:
        print("1.5 Creating a dummy job...")
        response = requests.post(jobs_create_url, headers=headers)
        response.raise_for_status()
        print("Job created successfully.")
    except Exception as e:
        print(f"Failed to create job: {e}")

    # 2. Get Jobs List
    jobs_url = f"{BASE_URL}/jobs"
    try:
        print("2. Fetching jobs list...")
        response = requests.get(jobs_url, headers=headers, params={"limit": 5})
        response.raise_for_status()
        jobs = response.json()
        print(f"Success: Retrieved {len(jobs)} jobs.")
        print(jobs)
    except Exception as e:
        print(f"Failed to fetch jobs: {e}")
        return

    if not jobs:
        print("No jobs found to test detail view.")
        return

    # 3. Get Single Job Details
    job_id = jobs[0]["id"]
    job_url = f"{BASE_URL}/jobs/{job_id}"
    try:
        print(f"3. Fetching details for job {job_id}...")
        response = requests.get(job_url, headers=headers)
        response.raise_for_status()
        job = response.json()
        print(f"Success: Retrieved job {job['id']} - {job.get('name', 'No Name')}")
    except Exception as e:
        print(f"Failed to fetch job details: {e}")

if __name__ == "__main__":
    test_dashboard_api()

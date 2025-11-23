import requests
import os

BASE_URL = "http://localhost:8000"

def test_ingest_auth():
    print("\n--- Testing Authenticated Ingestion ---")
    
    # 1. Signup
    signup_url = f"{BASE_URL}/auth/signup"
    user_data = {
        "username": "ingest_user",
        "email": "ingest@example.com",
        "password": "password123",
        "role": "user"
    }
    try:
        print("1. Signing up...")
        response = requests.post(signup_url, json=user_data)
        if response.status_code == 400:
            print("User already exists, proceeding to login.")
        else:
            response.raise_for_status()
            print("Signup successful.")
    except Exception as e:
        print(f"Signup failed: {e}")
        return

    # 2. Login
    login_url = f"{BASE_URL}/auth/login"
    login_data = {
        "username": "ingest@example.com",
        "password": "password123"
    }
    token = ""
    try:
        print("2. Logging in...")
        response = requests.post(login_url, data=login_data)
        response.raise_for_status()
        token = response.json()["access_token"]
        print("Login successful, token received.")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # 3. Upload File
    ingest_url = f"{BASE_URL}/ingest"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a dummy PDF file
    with open("test_doc.pdf", "wb") as f:
        f.write(b"%PDF-1.4 test content")
        
    files = {"file": ("test_doc.pdf", open("test_doc.pdf", "rb"), "application/pdf")}
    
    try:
        print("3. Uploading file...")
        response = requests.post(ingest_url, headers=headers, files=files)
        response.raise_for_status()
        data = response.json()
        print("Response received:")
        print(data)
        
        if "job_id" in data:
            print(f"✅ Success: Job created with ID {data['job_id']}")
        else:
            print("❌ Failure: No job_id returned.")
            
    except Exception as e:
        print(f"Ingestion failed: {e}")
    finally:
        if os.path.exists("test_doc.pdf"):
            os.remove("test_doc.pdf")

if __name__ == "__main__":
    test_ingest_auth()

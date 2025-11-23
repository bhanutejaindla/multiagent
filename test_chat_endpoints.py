import requests
import time

BASE_URL = "http://localhost:8000"

def test_chat_only():
    print("\n--- Testing /chat (No Report) ---")
    url = f"{BASE_URL}/chat"
    payload = {"message": "Who is the CEO of Google?"}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        print("Response received:")
        print(data)
        
        if "reports" not in data:
            print("✅ Success: No reports returned as expected.")
        else:
            print("❌ Failure: Reports returned unexpectedly.")
            
    except Exception as e:
        print(f"Test failed: {e}")

def test_generate_document():
    print("\n--- Testing /generate-document (With Report) ---")
    url = f"{BASE_URL}/generate-document"
    payload = {"message": "Who is the CEO of Microsoft?"}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        print("Response received:")
        print(data)
        
        if "reports" in data and data["reports"]:
            print(f"✅ Success: Reports returned: {data['reports']}")
        else:
            print("❌ Failure: No reports returned.")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_chat_only()
    test_generate_document()

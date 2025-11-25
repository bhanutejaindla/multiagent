import requests
import sys

BASE_URL = "http://localhost:8000"

def test_admin_flow():
    print("\n==== TESTING ADMIN PANEL ====\n")

    # 1. Create Admin User
    print("--- 1. Creating Admin User ---")
    admin_data = {
        "username": "admin_test",
        "email": "admin@test.com",
        "password": "password123",
        "role": "ADMIN"
    }
    try:
        resp = requests.post(f"{BASE_URL}/auth/signup", json=admin_data)
        if resp.status_code == 200:
            print("Admin created successfully.")
            admin_token = resp.json()["access_token"]
        elif resp.status_code == 400 and "already registered" in resp.text:
            print("Admin already exists, logging in...")
            login_data = {"username": "admin@test.com", "password": "password123"}
            resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
            admin_token = resp.json()["access_token"]
        else:
            print(f"Failed to create admin: {resp.text}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Test Admin Stats
    print("\n--- 2. Testing GET /admin/stats ---")
    resp = requests.get(f"{BASE_URL}/admin/stats", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    if resp.status_code != 200:
        print("FAIL: Could not fetch stats")

    # 3. Test Admin Users
    print("\n--- 3. Testing GET /admin/users ---")
    resp = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    print(f"Status: {resp.status_code}")
    users = resp.json()
    print(f"Found {len(users)} users")
    if resp.status_code != 200:
        print("FAIL: Could not fetch users")

    # 4. Test Admin Tools
    print("\n--- 4. Testing GET /admin/tools ---")
    resp = requests.get(f"{BASE_URL}/admin/tools", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    if resp.status_code != 200:
        print("FAIL: Could not fetch tools")

    # 5. Test RBAC (Normal User)
    print("\n--- 5. Testing RBAC (Normal User) ---")
    user_data = {
        "username": "normal_user",
        "email": "normal@test.com",
        "password": "password123",
        "role": "USER"
    }
    try:
        resp = requests.post(f"{BASE_URL}/auth/signup", json=user_data)
        if resp.status_code == 200:
            user_token = resp.json()["access_token"]
        elif resp.status_code == 400:
            login_data = {"username": "normal@test.com", "password": "password123"}
            resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
            user_token = resp.json()["access_token"]
        else:
            print(f"Failed to create normal user: {resp.text}")
            return
    except:
        pass

    user_headers = {"Authorization": f"Bearer {user_token}"}
    resp = requests.get(f"{BASE_URL}/admin/stats", headers=user_headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 403:
        print("SUCCESS: Access denied for normal user.")
    else:
        print(f"FAIL: Normal user accessed admin route! Status: {resp.status_code}")

if __name__ == "__main__":
    test_admin_flow()

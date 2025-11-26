import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def test_admin_enhancements():
    print("\n==== TESTING ADMIN ENHANCEMENTS ====\n")

    # 1. Login as Admin (Assuming admin exists from previous test)
    print("--- 1. Logging in as Admin ---")
    login_data = {"username": "admin@test.com", "password": "password123"}
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if resp.status_code == 200:
            admin_token = resp.json()["access_token"]
            print("Admin logged in.")
        else:
            print(f"Failed to login admin: {resp.text}")
            # Try creating if not exists (in case DB was reset)
            admin_data = {
                "username": "admin_test",
                "email": "admin@test.com",
                "password": "password123",
                "role": "ADMIN"
            }
            resp = requests.post(f"{BASE_URL}/auth/signup", json=admin_data)
            if resp.status_code == 200:
                 admin_token = resp.json()["access_token"]
                 print("Admin created and logged in.")
            else:
                print("Could not create/login admin. Exiting.")
                return
    except Exception as e:
        print(f"Error: {e}")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get Users and Check Quota Field
    print("\n--- 2. Checking User Quota Field ---")
    resp = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    users = resp.json()
    if not users:
        print("No users found.")
        return
    
    target_user = users[0]
    print(f"User: {target_user['username']}, Quota: {target_user.get('quota_limit')}")
    if 'quota_limit' not in target_user:
        print("FAIL: quota_limit field missing in user response")
    
    # 3. Update Quota
    print("\n--- 3. Updating Quota ---")
    new_quota = 50
    resp = requests.put(f"{BASE_URL}/admin/users/{target_user['id']}/quota", params={"quota": new_quota}, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    if resp.status_code == 200 and resp.json()['new_quota'] == new_quota:
        print("SUCCESS: Quota updated.")
    else:
        print("FAIL: Quota update failed.")

    # 4. Toggle Tool
    print("\n--- 4. Toggling Tool ---")
    tool_name = "research"
    # Disable
    print(f"Disabling {tool_name}...")
    resp = requests.post(f"{BASE_URL}/admin/tools/{tool_name}/toggle", params={"enabled": "false"}, headers=headers)
    print(f"Status: {resp.status_code}")
    
    # Check status
    resp = requests.get(f"{BASE_URL}/admin/tools", headers=headers)
    tools = resp.json()
    research_tool = next((t for t in tools if t['name'] == tool_name), None)
    if research_tool and research_tool['status'] == 'disabled' and research_tool['is_enabled'] == False:
        print("SUCCESS: Tool disabled.")
    else:
        print(f"FAIL: Tool status mismatch. {research_tool}")

    # Enable back
    print(f"Enabling {tool_name}...")
    requests.post(f"{BASE_URL}/admin/tools/{tool_name}/toggle", params={"enabled": "true"}, headers=headers)

if __name__ == "__main__":
    test_admin_enhancements()

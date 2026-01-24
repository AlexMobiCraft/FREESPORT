import requests
import sys

# Configuration
BASE_URL = "http://localhost:8001/api/integration/1c/exchange/"
USER_EMAIL = "manual_test_user@example.com"
USER_PASS = "manual_test_pass_123"

def main():
    print(f"🔄 Testing 'mode=import' (Trigger Processing)...")
    
    session = requests.Session()
    session.auth = (USER_EMAIL, USER_PASS)

    # 1. Auth
    print("\n[Step 1] Authenticating...")
    try:
        resp = session.get(BASE_URL, params={'mode': 'checkauth'})
        if "success" not in resp.text:
            print(f"❌ Auth failed: {resp.text}")
            return
        
        lines = resp.text.strip().split('\n')
        cookie_name = lines[1].strip()
        sessid = lines[2].strip()
        session.cookies.set(cookie_name, sessid)
        print(f"✅ Authenticated.")

    except Exception:
        print("❌ Auth Error")
        return

    # 2. Try Import
    filename = "rests_current_day.xml"
    print(f"\n[Step 2] Sending 'mode=import' command for {filename}...")
    
    url = f"{BASE_URL}?mode=import&filename={filename}&sessid={sessid}"
    resp = session.get(url) # 1C usually uses GET for import, sometimes POST
    
    print(f"Response Code: {resp.status_code}")
    print(f"Response Body: {resp.text.strip()}")

    if "Unknown mode" in resp.text:
        print("\n💡 RESULT: As expected, 'import' mode is NOT implemented yet.")
        print("   This is the goal of Epic 3.")

if __name__ == "__main__":
    main()

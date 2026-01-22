import requests
import sys

# Configuration
BASE_URL = "http://localhost:8001/api/integration/1c/exchange/"
USER = "1c_test_user@example.com"
PASSWORD = "test_password_123"

def main():
    print(f"🔄 Starting 1C Connection Simulation...")
    print(f"Target: {BASE_URL}")
    print(f"User: {USER}")

    # 1. Check Auth (Handshake)
    print("\n[Step 1] Sending checkauth request...")
    try:
        response = requests.get(
            BASE_URL,
            params={'mode': 'checkauth'},
            auth=(USER, PASSWORD),
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print("Response Body:")
        print("-" * 20)
        print(response.text)
        print("-" * 20)

        if response.status_code == 200 and 'success' in response.text:
            print("✅ Connection Successful!")
            
            # Parse Cookie
            lines = response.text.strip().split('\n')
            if len(lines) >= 3:
                cookie_name = lines[1].strip()
                session_id = lines[2].strip()
                print(f"🍪 Session Cookie Obtained: {cookie_name}={session_id}")
            else:
                print("⚠️ Warning: Unexpected response format (lines mapping failed)")
        
        elif response.status_code == 401:
            print("❌ Authentication Failed (401). Check credentials.")
        
        elif response.status_code == 403:
            print("🚫 Permission Denied (403). User needs 'can_exchange_1c' permission or is_staff.")
            
        else:
            print(f"❌ Unexpected Error: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not reach the server. Is Docker running?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

import requests
import sys

# Configuration
BASE_URL = "http://localhost:8001/api/integration/1c/exchange/"
USER = "1c_test_user@example.com"
PASSWORD = "test_password_123"

def main():
    print(f"🔄 Testing POST Method...")
    print(f"Target: {BASE_URL}")

    try:
        # Try POST request with checkauth mode
        response = requests.post(
            BASE_URL,
            params={'mode': 'checkauth'},
            auth=(USER, PASSWORD),
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 405:
            print("✅ Successfully reproduced 405 Method Not Allowed")
        elif response.status_code == 200:
            print("❌ Unexpected 200 OK (Method allowed?)")
        else:
            print(f"❓ Other status: {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

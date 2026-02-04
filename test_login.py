import requests

# آدرس سرور (مطمئن شو main.py در حال اجراست)
BASE_URL = "http://127.0.0.1:8000"

def test_system():
    print("--- 1. Testing Registration ---")
    try:
        reg_data = {"username": "admin_test", "password": "123"}
        res = requests.post(f"{BASE_URL}/register", json=reg_data)
        
        if res.status_code == 200:
            print("✅ Registration Successful!")
        elif res.status_code == 400 and "registered" in res.text:
            print("⚠️ User already exists (That's OK).")
        else:
            print(f"❌ Registration Failed: {res.text}")
            return

        print("\n--- 2. Testing Login ---")
        login_data = {"username": "admin_test", "password": "123"}
        res = requests.post(f"{BASE_URL}/token", data=login_data)
        
        if res.status_code == 200:
            token = res.json().get("access_token")
            print(f"✅ Login Successful! Token received.")
            print("🎉 BACKEND IS WORKING PERFECTLY!")
        else:
            print(f"❌ Login Failed: {res.status_code} - {res.text}")
            print("👉 Hint: Did you install 'python-multipart'?")

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Make sure 'main.py' is running!")

if __name__ == "__main__":
    test_system()
from fastapi.testclient import TestClient

# تست 1: چک کنیم که ثبت‌نام درست کار میکنه
def test_register_user(client: TestClient):
    # یه یوزر جدید میسازیم
    response = client.post(
        "/register",
        json={"username": "ali_student", "password": "123"}
    )
    # باید کد 200 برگردونه (یعنی موفق)
    assert response.status_code == 200
    
    # چک میکنیم دیتایی که برمیگرده درست باشه
    data = response.json()
    assert data["username"] == "ali_student"
    assert data["quota"] == 120  # سهمیه اولیه باید 120 باشه

# تست 2: اگه یوزر تکراری بود ارور بده
def test_register_duplicate_user(client: TestClient):
    # بار اول میسازیم (موفق)
    client.post(
        "/register",
        json={"username": "reza", "password": "123"}
    )
    # بار دوم با همون اسم (باید ارور بده)
    response = client.post(
        "/register",
        json={"username": "reza", "password": "123"}
    )
    # کد 400 یعنی درخواست بد (Bad Request)
    assert response.status_code == 400

# تست 3: لاگین و گرفتن توکن
def test_login_success(client: TestClient):
    # اول باید ثبت‌نام کنیم
    client.post("/register", json={"username": "login_test", "password": "123"})
    
    # حالا لاگین میکنیم
    response = client.post(
        "/token",
        data={"username": "login_test", "password": "123"}
    )
    assert response.status_code == 200
    
    # چک میکنیم توکن توی خروجی باشه
    assert "access_token" in response.json()

# تست 4: لاگین با رمز اشتباه
def test_login_wrong_password(client: TestClient):
    client.post("/register", json={"username": "hacker", "password": "123"})
    
    # رمز رو اشتباه میزنیم
    response = client.post(
        "/token",
        data={"username": "hacker", "password": "WRONG_PASSWORD"}
    )
    # کد 401 یعنی غیرمجاز (Unauthorized)
    assert response.status_code == 401
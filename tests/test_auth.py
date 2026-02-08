"""
تست‌های سیستم احراز هویت (Authentication Tests)
-----------------------------------------------
این فایل سناریوهای مختلف ثبت‌نام و ورود کاربر را بررسی می‌کند:
1. ثبت‌نام موفق.
2. جلوگیری از ثبت‌نام تکراری.
3. ورود موفق و دریافت توکن.
4. ورود ناموفق (رمز اشتباه).
"""

from fastapi.testclient import TestClient

def test_register_user(client: TestClient):
    """
    تست سناریوی ثبت‌نام موفق.
    انتظار داریم کد 200 برگردد و سهمیه اولیه 120 باشد.
    """
    response = client.post(
        "/register",
        json={"username": "ali_student", "password": "123"}
    )
    # بررسی کد وضعیت HTTP
    assert response.status_code == 200
    
    # بررسی بدنه پاسخ (Response Body)
    data = response.json()
    assert data["username"] == "ali_student"
    assert data["quota"] == 120  # سهمیه پیش‌فرض

def test_register_duplicate_user(client: TestClient):
    """
    تست جلوگیری از ثبت‌نام تکراری.
    اگر کاربری قبلاً ثبت شده باشد، باید خطای 400 دریافت کنیم.
    """
    # بار اول: ثبت‌نام موفق
    client.post(
        "/register",
        json={"username": "reza", "password": "123"}
    )
    
    # بار دوم: تلاش برای ثبت‌نام با همان نام کاربری
    response = client.post(
        "/register",
        json={"username": "reza", "password": "123"}
    )
    
    # انتظار خطا داریم (Bad Request)
    assert response.status_code == 400

def test_login_success(client: TestClient):
    """
    تست ورود موفق و دریافت توکن JWT.
    """
    # پیش‌نیاز: ثبت‌نام کاربر
    client.post("/register", json={"username": "login_test", "password": "123"})
    
    # ارسال درخواست ورود (Login)
    # نکته: فرمت دیتا در OAuth2PasswordRequestForm به صورت Form-Data است، نه JSON.
    response = client.post(
        "/token",
        data={"username": "login_test", "password": "123"}
    )
    
    assert response.status_code == 200
    
    # باید فیلد access_token در پاسخ وجود داشته باشد
    assert "access_token" in response.json()

def test_login_wrong_password(client: TestClient):
    """
    تست امنیت ورود با رمز اشتباه.
    باید کد 401 (Unauthorized) دریافت کنیم.
    """
    client.post("/register", json={"username": "hacker", "password": "123"})
    
    # تلاش برای ورود با رمز غلط
    response = client.post(
        "/token",
        data={"username": "hacker", "password": "WRONG_PASSWORD"}
    )
    
    assert response.status_code == 401
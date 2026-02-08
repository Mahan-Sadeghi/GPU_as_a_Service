"""
تست‌های مدیریت درخواست‌ها (Job Management Tests)
-----------------------------------------------
این فایل منطق اصلی سرویس GPU را تست می‌کند:
1. ثبت درخواست و کسر سهمیه.
2. جلوگیری از درخواست بیش از حد سهمیه.
3. پروسه تایید درخواست توسط مدیر سیستم.
"""

from fastapi.testclient import TestClient

def test_create_job(client: TestClient):
    """
    تست ثبت درخواست جدید و بررسی کسر سهمیه.
    """
    # مرحله 1: ثبت‌نام و دریافت توکن
    client.post("/register", json={"username": "job_tester", "password": "123"})
    login_res = client.post("/token", data={"username": "job_tester", "password": "123"})
    token = login_res.json()["access_token"]
    
    # مرحله 2: ارسال درخواست پردازش (20 ثانیه)
    response = client.post(
        "/jobs/",
        json={
            "gpu_type": "T4",
            "gpu_count": 1,
            "command": "python main.py",
            "estimated_duration": 20
        },
        # ارسال توکن در هدر Authorization
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"

    # مرحله 3: بررسی پروفایل کاربر برای اطمینان از کسر سهمیه
    # سهمیه اولیه (120) - درخواست (20) = باید 100 باقی بماند
    user_res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert user_res.json()["quota"] == 100

def test_insufficient_quota(client: TestClient):
    """
    تست سناریوی کمبود سهمیه (Quota Limit).
    اگر درخواست بیشتر از سهمیه باقی‌مانده باشد، باید رد شود.
    """
    # ایجاد کاربر جدید (سهمیه پیش‌فرض: 120)
    client.post("/register", json={"username": "poor_guy", "password": "123"})
    login_res = client.post("/token", data={"username": "poor_guy", "password": "123"})
    token = login_res.json()["access_token"]
    
    # درخواست 200 ثانیه (که بیشتر از 120 است)
    response = client.post(
        "/jobs/",
        json={"gpu_type": "V100", "gpu_count": 1, "command": "run", "estimated_duration": 200},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # انتظار خطای 400 داریم
    assert response.status_code == 400
    assert "سهمیه ناکافی" in response.json()["detail"]

def test_admin_approve_job(client: TestClient):
    """
    تست چرخه کامل تایید درخواست توسط ادمین.
    """
    # 1. ایجاد اکانت ادمین
    client.post("/register", json={"username": "admin", "password": "123"})
    # فرض بر این است که در کد اصلی یا دیتابیس تست، اولین یوزر یا یوزر خاصی ادمین می‌شود
    # یا اینکه در اینجا فقط لاجیک تغییر وضعیت را تست می‌کنیم.
    admin_token = client.post("/token", data={"username": "admin", "password": "123"}).json()["access_token"]
    
    # 2. ایجاد کاربر عادی و ثبت درخواست
    client.post("/register", json={"username": "user2", "password": "123"})
    user_token = client.post("/token", data={"username": "user2", "password": "123"}).json()["access_token"]
    
    job_res = client.post(
        "/jobs/",
        json={"gpu_type": "T4", "gpu_count": 1, "command": "test", "estimated_duration": 10},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    job_id = job_res.json()["id"]
    
    # 3. تغییر وضعیت درخواست به APPROVED توسط ادمین
    update_res = client.put(
        f"/jobs/{job_id}?status_update=APPROVED",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "APPROVED"
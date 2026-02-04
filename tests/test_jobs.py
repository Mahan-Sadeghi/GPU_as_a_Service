from fastapi.testclient import TestClient

# تست 1: ثبت درخواست جدید (باید سهمیه کم بشه)
def test_create_job(client: TestClient):
    # مرحله 1: ثبت‌نام و لاگین
    client.post("/register", json={"username": "job_tester", "password": "123"})
    login_res = client.post("/token", data={"username": "job_tester", "password": "123"})
    token = login_res.json()["access_token"]
    
    # مرحله 2: ارسال درخواست پردازش
    response = client.post(
        "/jobs/",
        json={
            "gpu_type": "T4",
            "gpu_count": 1,
            "command": "python main.py",
            "estimated_duration": 20  # 20 ثانیه
        },
        # توکن رو باید توی هدر بفرستیم
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"

    # مرحله 3: چک کنیم سهمیه کم شده؟ (120 - 20 = 100)
    user_res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert user_res.json()["quota"] == 100

# تست 2: اگه سهمیه نداشت ارور بده
def test_insufficient_quota(client: TestClient):
    # یوزر جدید
    client.post("/register", json={"username": "poor_guy", "password": "123"})
    login_res = client.post("/token", data={"username": "poor_guy", "password": "123"})
    token = login_res.json()["access_token"]
    
    # درخواستی که از سهمیه بیشتره (200 > 120)
    response = client.post(
        "/jobs/",
        json={"gpu_type": "V100", "gpu_count": 1, "command": "run", "estimated_duration": 200},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # باید ارور 400 بده
    assert response.status_code == 400
    assert "سهمیه ناکافی" in response.json()["detail"]

# تست 3: ادمین بتونه درخواست رو تایید کنه
def test_admin_approve_job(client: TestClient):
    # ساخت ادمین و گرفتن توکن ادمین
    client.post("/register", json={"username": "admin", "password": "123"})
    admin_token = client.post("/token", data={"username": "admin", "password": "123"}).json()["access_token"]
    
    # ساخت کاربر عادی و ثبت یک جاب
    client.post("/register", json={"username": "user2", "password": "123"})
    user_token = client.post("/token", data={"username": "user2", "password": "123"}).json()["access_token"]
    
    job_res = client.post(
        "/jobs/",
        json={"gpu_type": "T4", "gpu_count": 1, "command": "test", "estimated_duration": 10},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    job_id = job_res.json()["id"]
    
    # ادمین وضعیت رو به APPROVED تغییر میده
    update_res = client.put(
        f"/jobs/{job_id}?status_update=APPROVED",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "APPROVED"
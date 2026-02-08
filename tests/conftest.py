"""
پیکربندی و تنظیمات اولیه تست‌ها (Test Configuration)
----------------------------------------------------
این فایل توسط Pytest به صورت خودکار اجرا می‌شود.
وظیفه اصلی آن:
1. ایجاد یک دیتابیس موقت و خالی (test_db.db) برای هر بار تست.
2. جایگزینی دیتابیس اصلی برنامه با این دیتابیس تست (Dependency Override).
3. فراهم کردن کلاینت تست (TestClient) برای ارسال درخواست‌ها.
"""

import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# اضافه کردن مسیر پروژه به sys.path تا بتوانیم ماژول‌ها را ایمپورت کنیم
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ایمپورت کردن برنامه اصلی و وابستگی‌ها
from main import app, get_db
from app.database import Base
from app.security import get_db as security_get_db

# آدرس دیتابیس مخصوص تست (فایلی جدا از دیتابیس اصلی)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"

# ایجاد موتور دیتابیس تست
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# ایجاد نشست‌های دیتابیس تست
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def client():
    """
    فیکسچر (Fixture) اصلی کلاینت تست.
    این تابع قبل از اجرای تست‌ها اجرا می‌شود و محیط را آماده می‌کند.
    scope="module": یعنی این تنظیمات برای کل فایل تست یکبار اجرا شود.
    """
    
    # الف) ساختن تمام جداول در دیتابیس تست (Create Tables)
    Base.metadata.create_all(bind=engine)

    # ب) تابع جایگزین برای وابستگی دیتابیس (Override)
    # این تابع به جای وصل شدن به دیتابیس اصلی، به test_db وصل می‌شود.
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # پ) اعمال جایگزینی روی تمام بخش‌های برنامه
    # هم در main.py و هم در security.py باید دیتابیس عوض شود.
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[security_get_db] = override_get_db

    # ت) ایجاد کلاینت تست و واگذاری آن به توابع تست
    with TestClient(app) as c:
        yield c

    # ث) پاکسازی نهایی (Teardown)
    # بعد از تمام شدن تست‌ها، جداول را حذف می‌کنیم تا محیط تمیز بماند.
    Base.metadata.drop_all(bind=engine)
import sys
import os

# مسیردهی
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# ایمپورت‌ها
from main import app, get_db
from app.database import Base
# 👇 این خط جدیده: ایمپورت کردن get_db از security
from app.security import get_db as security_get_db

# تنظیم دیتابیس تستی
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def client():
    # الف) ساختن جدول‌ها
    Base.metadata.create_all(bind=engine)

    # ب) دیتابیس جایگزین
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # پ) اعمال جایگزینی روی هر دو جا (هم main هم security)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[security_get_db] = override_get_db  # <--- این خط مشکل رو حل میکنه

    # ت) اجرای تست
    with TestClient(app) as c:
        yield c

    # ث) پاکسازی نهایی
    Base.metadata.drop_all(bind=engine)
"""
ماژول تنظیمات دیتابیس (Database Configuration).

این فایل وظیفه برقراری اتصال به SQLite و ایجاد نشست‌ها (Sessions) را بر عهده دارد.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# آدرس فایل دیتابیس (SQLite)
# در دایرکتوری اصلی پروژه فایلی به نام gpu_service.db ساخته می‌شود
SQLALCHEMY_DATABASE_URL = "sqlite:///./gpu_service.db"

# ایجاد موتور اتصال به دیتابیس
# check_same_thread=False برای SQLite ضروری است تا بتواند در چندین ترد (Thread) کار کند
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# کلاس سازنده نشست (Session) برای تعامل با دیتابیس
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# کلاس پایه برای مدل‌ها (Models)
# تمام جداول دیتابیس از این کلاس ارث‌بری می‌کنند
Base = declarative_base()
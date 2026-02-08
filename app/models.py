"""
مدل‌های داده (Database Models)
-----------------------------
تعریف ساختار جداول دیتابیس با استفاده از SQLAlchemy ORM.
شامل جداول کاربران (User) و درخواست‌ها (Job).
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    """
    جدول کاربران (Users Table)
    -------------------------
    اطلاعات احراز هویت و سهمیه کاربران در اینجا ذخیره می‌شود.
    """
    __tablename__ = "users"
    
    # ستون‌های جدول
    id = Column(Integer, primary_key=True, index=True)  # شناسه یکتا (Primary Key)
    username = Column(String, unique=True, index=True)  # نام کاربری (باید یکتا باشد)
    hashed_password = Column(String)                    # رمز عبور (به صورت هش شده ذخیره می‌شود)
    is_admin = Column(Boolean, default=False)           # تعیین سطح دسترسی (ادمین یا کاربر عادی)
    quota = Column(Integer, default=120)                # سهمیه پردازش (پیش‌فرض ۱۲۰ ثانیه)
    
    # ارتباط با جدول Job (One-to-Many Relationship)
    # هر کاربر می‌تواند چندین درخواست (Job) داشته باشد.
    jobs = relationship("Job", back_populates="owner")

class Job(Base):
    """
    جدول درخواست‌های پردازش (Jobs Table)
    -----------------------------------
    هر رکورد نشان‌دهنده یک درخواست برای استفاده از GPU است.
    """
    __tablename__ = "jobs"
    
    # مشخصات درخواست
    id = Column(Integer, primary_key=True, index=True)
    gpu_type = Column(String)          # نوع کارت گرافیک (مثلاً T4, V100)
    gpu_count = Column(Integer)        # تعداد کارت درخواستی
    command = Column(String)           # دستور اجرایی کاربر (مثلاً python train.py)
    estimated_duration = Column(Integer) # مدت تخمینی اجرا (ثانیه)
    
    # وضعیت درخواست (PENDING, RUNNING, COMPLETED, FAILED)
    status = Column(String, default="PENDING")
    
    # زمان‌بندی‌ها
    created_at = Column(DateTime, default=datetime.now) # زمان ثبت
    started_at = Column(DateTime, nullable=True)        # زمان شروع اجرا
    completed_at = Column(DateTime, nullable=True)      # زمان پایان
    
    # کلید خارجی (Foreign Key) برای ارتباط با کاربر
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # ارتباط معکوس با User
    owner = relationship("User", back_populates="jobs")
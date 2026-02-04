"""
مدل‌های دیتابیس (Database Models).

این فایل ساختار جداول (Users, Jobs) را برای SQLAlchemy تعریف می‌کند.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    """
    جدول کاربران سیستم.
    
    Attributes:
        id: شناسه یکتا.
        username: نام کاربری (باید یکتا باشد).
        hashed_password: رمز عبور هش شده.
        is_admin: تعیین نقش کاربر (مدیر/کاربر عادی).
        quota: میزان سهمیه باقی‌مانده کاربر به ثانیه.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    quota = Column(Integer, default=120)  # سهمیه پیش‌فرض
    
    # ارتباط با جدول Jobs (یک کاربر می‌تواند چندین جاب داشته باشد)
    jobs = relationship("Job", back_populates="owner")

class Job(Base):
    """
    جدول درخواست‌های پردازشی (Jobs).
    
    Attributes:
        id: شناسه یکتا.
        gpu_type: نوع کارت گرافیک درخواستی.
        gpu_count: تعداد کارت گرافیک.
        command: دستور اجرایی.
        status: وضعیت فعلی (PENDING, APPROVED, RUNNING, COMPLETED, FAILED).
        created_at: زمان ثبت درخواست.
        started_at: زمان شروع اجرا (توسط ورکر).
        completed_at: زمان پایان اجرا.
    """
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    gpu_type = Column(String)
    gpu_count = Column(Integer)
    command = Column(String)
    estimated_duration = Column(Integer)
    status = Column(String, default="PENDING")
    
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # کلید خارجی به جدول Users
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="jobs")
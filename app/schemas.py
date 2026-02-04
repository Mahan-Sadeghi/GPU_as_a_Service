"""
طرح‌واره‌ها (Pydantic Schemas).

این فایل برای اعتبارسنجی داده‌های ورودی و خروجی API استفاده می‌شود.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- مدیریت کاربران ---

class UserBase(BaseModel):
    """الگوی پایه کاربر شامل فیلدهای مشترک."""
    username: str

class UserCreate(UserBase):
    """داده‌های مورد نیاز برای ثبت‌نام (ورودی کاربر)."""
    password: str

class UserResponse(UserBase):
    """داده‌های قابل نمایش کاربر (خروجی API)."""
    id: int
    is_admin: bool
    quota: int  # نمایش سهمیه به کاربر
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """ساختار توکن احراز هویت."""
    access_token: str
    token_type: str

# --- مدیریت درخواست‌ها ---

class JobBase(BaseModel):
    """اطلاعات پایه یک درخواست پردازشی."""
    gpu_type: str
    gpu_count: int
    command: str
    estimated_duration: int

class JobCreate(JobBase):
    """داده‌های ورودی هنگام ثبت درخواست جدید."""
    pass

class JobResponse(JobBase):
    """داده‌های خروجی درخواست همراه با وضعیت و زمان‌بندی."""
    id: int
    owner_id: int
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
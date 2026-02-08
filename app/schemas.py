"""
طرح‌واره‌های اعتبارسنجی (Pydantic Schemas)
-----------------------------------------
این فایل وظیفه اعتبارسنجی داده‌های ورودی (Request) و فرمت‌دهی داده‌های خروجی (Response) را دارد.
جدا کردن Schema از Model باعث امنیت بیشتر می‌شود (مثلاً رمز عبور را در خروجی برنمی‌گردانیم).
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# =======================
# بخش مدیریت کاربران (User Schemas)
# =======================

class UserBase(BaseModel):
    """فیلدهای مشترک بین ورودی و خروجی"""
    username: str

class UserCreate(UserBase):
    """
    داده‌های لازم برای ثبت‌نام.
    شامل پسورد است (که فقط موقع ثبت‌نام دریافت می‌شود).
    """
    password: str

class UserResponse(UserBase):
    """
    داده‌هایی که به کلاینت برمی‌گردانیم.
    نکته مهم: پسورد در اینجا وجود ندارد (برای امنیت).
    """
    id: int
    is_admin: bool
    quota: int
    
    # تنظیمات برای سازگاری با SQLAlchemy ORM
    # این اجازه می‌دهد آبجکت‌های دیتابیس مستقیماً به Pydantic تبدیل شوند.
    class Config:
        from_attributes = True

class Token(BaseModel):
    """ساختار توکن JWT که به کلاینت داده می‌شود"""
    access_token: str
    token_type: str

# =======================
# بخش مدیریت درخواست‌ها (Job Schemas)
# =======================

class JobBase(BaseModel):
    """اطلاعات پایه درخواست"""
    gpu_type: str
    gpu_count: int
    command: str
    estimated_duration: int

class JobCreate(JobBase):
    """داده‌های ورودی کاربر برای ثبت درخواست"""
    pass

class JobResponse(JobBase):
    """
    داده‌های کامل درخواست که شامل وضعیت و زمان‌بندی‌هاست
    و توسط سیستم تولید شده است.
    """
    id: int
    owner_id: int
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
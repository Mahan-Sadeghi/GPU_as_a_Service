# schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- مدل‌های مربوط به توکن (برای لاگین) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- مدل‌های مربوط به کاربر (User) ---

# مدلی که کاربر موقع ثبت‌نام می‌فرستد
class UserCreate(BaseModel):
    username: str
    password: str

# مدلی که ما به کاربر برمی‌گردانیم (پسورد را نباید برگردانیم!)
class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    quota_limit: float

    class Config:
        from_attributes = True  # برای سازگاری با SQLAlchemy

# --- مدل‌های مربوط به تسک‌ها (Job) ---

# اطلاعاتی که کاربر برای ثبت یک تسک می‌فرستد
class JobCreate(BaseModel):
    gpu_type: str          # نوع گرافیک درخواستی
    gpu_count: int         # تعداد گرافیک
    estimated_duration: int # زمان تخمینی (ساعت)
    command: str           # دستور اجرا
    data_address: str      # آدرس فایل‌ها
    sensitivity: Optional[str] = "normal"

# اطلاعاتی که ما درباره تسک به کاربر نشان می‌دهیم
class JobResponse(JobCreate):
    id: int
    owner_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
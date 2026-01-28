from pydantic import BaseModel
from typing import List, Optional

# --- مدل‌های کاربر (User) ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_admin: bool  # <--- فیلد مهم جدید اینجاست
    # role و quota_limit را حذف کردیم چون در دیتابیس نیستند

    class Config:
        orm_mode = True

# --- مدل‌های تسک (Job) ---
class JobBase(BaseModel):
    gpu_type: str
    gpu_count: int
    estimated_duration: int
    command: str
    data_address: Optional[str] = "/data/default"
    sensitivity: Optional[str] = "normal"

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    status: str
    owner_id: int

    class Config:
        orm_mode = True

# --- مدل توکن (برای لاگین) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
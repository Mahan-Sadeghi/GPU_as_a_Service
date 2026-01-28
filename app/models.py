
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import datetime

# مدل جدول کاربران (Users)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String) # پسورد به صورت هش شده ذخیره می‌شود
    
    # نقش کاربر: طبق مستندات یا 'user' است یا 'admin'
    role = Column(String, default="user")
    
    # سقف سهمیه کاربر (بر حسب ساعت GPU). پیش‌فرض ۱۰۰ ساعت
    quota_limit = Column(Float, default=100.0)

    # ارتباط با جدول Jobها
    jobs = relationship("Job", back_populates="owner")

# مدل جدول تسک‌ها (Jobs)
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    
    # شناسه کاربری که این تسک را ساخته است
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # اطلاعات متادیتا طبق فایل نیازمندی‌ها
    gpu_type = Column(String)         # نوع پردازنده گرافیکی (مثلاً T4)
    gpu_count = Column(Integer)       # تعداد درخواستی
    estimated_duration = Column(Integer) # زمان تخمینی اجرا
    command = Column(String)          # دستور اجرایی
    data_address = Column(String)     # آدرس داده‌ها
    sensitivity = Column(String, default="normal") # سطح حساسیت
    
    # وضعیت تسک: PENDING -> APPROVED -> RUNNING -> COMPLETED / FAILED
    status = Column(String, default="PENDING")
    
    # زمان ثبت درخواست
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # ارتباط با جدول User
    owner = relationship("User", back_populates="jobs")
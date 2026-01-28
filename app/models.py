from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    # --- این خط جا افتاده بود: ---
    is_admin = Column(Boolean, default=False)

    # ارتباط با جدول تسک‌ها
    jobs = relationship("Job", back_populates="owner")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    gpu_type = Column(String, index=True)
    gpu_count = Column(Integer)
    estimated_duration = Column(Integer)
    status = Column(String, default="PENDING")
    
    # اطلاعات تکمیلی
    command = Column(String)
    data_address = Column(String)
    sensitivity = Column(String)

    # ارتباط با کاربر (مالک تسک)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="jobs")
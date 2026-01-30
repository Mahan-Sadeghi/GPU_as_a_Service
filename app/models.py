from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    
    jobs = relationship("Job", back_populates="owner")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    gpu_type = Column(String)
    gpu_count = Column(Integer)
    command = Column(String)
    estimated_duration = Column(Integer)
    status = Column(String, default="PENDING")
    
    # --- ستون‌های جدید زمان ---
    created_at = Column(DateTime, default=datetime.now) # زمان ثبت
    started_at = Column(DateTime, nullable=True)        # زمان شروع
    completed_at = Column(DateTime, nullable=True)      # زمان پایان
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="jobs")
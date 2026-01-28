# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# آدرس دیتابیس را اینجا مشخص می‌کنیم.
# این فایل 'gpu_service.db' کنار کدهای پروژه ساخته می‌شود.
SQLALCHEMY_DATABASE_URL = "sqlite:///./gpu_service.db"

# تنظیمات مخصوص SQLite برای جلوگیری از خطای Thread در FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# ساخت نشست (Session) برای ارتباط با دیتابیس
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# تابعی برای گرفتن ارتباط دیتابیس (که بعداً در API استفاده می‌کنیم)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
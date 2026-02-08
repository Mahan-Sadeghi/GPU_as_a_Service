"""
ماژول پیکربندی دیتابیس (Database Configuration)
---------------------------------------------
وظیفه: برقراری اتصال به دیتابیس SQLite و مدیریت نشست‌ها (Sessions).
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# مسیر فایل دیتابیس (Connection String)
# فایل gpu_service.db در پوشه اصلی پروژه ساخته خواهد شد.
SQLALCHEMY_DATABASE_URL = "sqlite:///./gpu_service.db"

# 1. ساخت موتور دیتابیس (Engine)
# آرگومان check_same_thread=False مخصوص SQLite است.
# چون SQLite به صورت پیش‌فرض اجازه نمی‌دهد یک ترد (Thread) متفاوت به کانکشن دسترسی داشته باشد،
# اما در FastAPI هر درخواست ممکن است در یک ترد جداگانه اجرا شود.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 2. ساخت کلاس SessionLocal
# این کلاس کارخانه (Factory) تولید نشست‌های دیتابیس است.
# autocommit=False: تغییرات تا زمانی که commit نکنیم اعمال نمی‌شوند (برای امنیت تراکنش).
# autoflush=False: تغییرات تا زمان commit به دیتابیس ارسال نمی‌شوند.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. کلاس پایه مدل‌ها (Base)
# تمام کلاس‌های موجود در models.py باید از این کلاس ارث‌بری کنند
# تا SQLAlchemy بتواند آن‌ها را شناسایی و تبدیل به جدول کند.
Base = declarative_base()
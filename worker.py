"""
سرویس پردازشگر پس‌زمینه (Background Worker)
------------------------------------------
این اسکریپت به صورت مستقل اجرا می‌شود و وظیفه شبیه‌سازی اجرای تسک‌ها روی GPU را دارد.
جدا کردن Worker از Main API باعث می‌شود سرور اصلی هنگام پردازش‌های سنگین قفل نشود (Non-blocking).
"""

import time
import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session

# اضافه کردن مسیر جاری به sys.path برای شناسایی پکیج 'app'
sys.path.append(os.getcwd())
from app import models, database

def process_jobs() -> None:
    """
    حلقه اصلی پردازش (Main Processing Loop).
    
    چرخه حیات یک تسک در اینجا:
    1. Polling: بررسی دیتابیس برای تسک‌های جدید (وضعیت APPROVED).
    2. Start: تغییر وضعیت به RUNNING و ثبت زمان شروع.
    3. Execution: شبیه‌سازی پردازش (استفاده از sleep به جای درگیر کردن واقعی GPU).
    4. Finish: تغییر وضعیت به COMPLETED و ثبت زمان پایان.
    """
    print("👷 Worker started! Waiting for APPROVED jobs... (Press Ctrl+C to stop)")
    
    while True:
        # ایجاد یک نشست دیتابیس جدید در هر دور حلقه
        db: Session = database.SessionLocal()
        try:
            # جستجو برای قدیمی‌ترین تسک که توسط ادمین تایید شده است (FIFO)
            job = db.query(models.Job).filter(models.Job.status == "APPROVED").first()

            if job:
                print(f"⚡ Processing Job #{job.id}: {job.command}")
                
                # --- مرحله ۱: شروع پردازش ---
                job.status = "RUNNING"
                job.started_at = datetime.now()
                db.commit()
                
                # --- مرحله ۲: شبیه‌سازی اجرا ---
                # در محیط واقعی، اینجا کد PyTorch یا TensorFlow اجرا می‌شود.
                # ما فعلاً با time.sleep زمان پردازش را شبیه‌سازی می‌کنیم.
                duration = job.estimated_duration or 10
                for i in range(duration):
                    # شبیه‌سازی پیشرفت کار (هر ثانیه)
                    time.sleep(1)
                    # (اختیاری: می‌توان درصد پیشرفت را در دیتابیس آپدیت کرد)

                # --- مرحله ۳: پایان پردازش ---
                job.status = "COMPLETED"
                job.completed_at = datetime.now()
                db.commit()
                print(f"✅ Job #{job.id} Completed successfully.\n")
            
            else:
                # اگر هیچ تسکی نبود، ۲ ثانیه صبر می‌کنیم تا فشار روی دیتابیس و CPU کم شود.
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Worker Error: {e}")
            # در صورت بروز خطا، بهتر است نشست دیتابیس بسته شود تا کانکشن باز نماند.
        finally:
            db.close()

if __name__ == "__main__":
    process_jobs()
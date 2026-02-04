import time
import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session

# افزودن مسیر پروژه به sys.path برای شناسایی ماژول‌ها
sys.path.append(os.getcwd())
from app import models, database

def process_jobs() -> None:
    """
    تابع اصلی ورکر (Worker Process).
    
    وظایف:
    1. بررسی دیتابیس برای تسک‌های 'APPROVED'.
    2. تغییر وضعیت به 'RUNNING'.
    3. شبیه‌سازی پردازش (Sleep).
    4. تغییر وضعیت به 'COMPLETED' پس از پایان.
    """
    print("👷 Worker started! Waiting for APPROVED jobs... (Press Ctrl+C to stop)")
    
    while True:
        db: Session = database.SessionLocal()
        try:
            # جستجو برای اولین تسک تایید شده
            job = db.query(models.Job).filter(models.Job.status == "APPROVED").first()

            if job:
                print(f"⚡ Processing Job #{job.id}: {job.command}")
                
                # شروع پردازش
                job.status = "RUNNING"
                job.started_at = datetime.now()
                db.commit()
                
                # شبیه‌سازی زمان اجرا
                duration = job.estimated_duration or 10
                for i in range(duration):
                    # اینجا می‌توان لاگ‌های لحظه‌ای را به دیتابیس فرستاد
                    time.sleep(1)
                    # print(f"   ⏳ Step {i+1}/{duration}...") 

                # پایان پردازش
                job.status = "COMPLETED"
                job.completed_at = datetime.now()
                db.commit()
                print(f"✅ Job #{job.id} Completed successfully.\n")
            
            else:
                # اگر تسکی نبود، وقفه کوتاه برای کاهش بار CPU
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Worker Error: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    process_jobs()
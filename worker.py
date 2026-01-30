import time
import sys
import os
from datetime import datetime

# اضافه کردن مسیر پروژه برای شناسایی ماژول‌ها
sys.path.append(os.getcwd())
from app import models, database

def process_jobs():
    """
    تابع اصلی ورکر (Worker)
    این تابع به صورت مداوم دیتابیس را چک می‌کند تا کارهای تایید شده را انجام دهد.
    """
    print("👷 Worker started! Waiting for APPROVED jobs... (Press Ctrl+C to stop)")
    
    while True:
        # اتصال به دیتابیس
        db = database.SessionLocal()
        try:
            # 1. پیدا کردن کارهایی که وضعیتشان APPROVED است
            job = db.query(models.Job).filter(models.Job.status == "APPROVED").first()

            if job:
                print(f"⚡ Found job #{job.id}: {job.command}")
                
                # 2. تغییر وضعیت به در حال اجرا (RUNNING)
                job.status = "RUNNING"
                job.started_at = datetime.now() # ثبت زمان شروع
                db.commit()
                print("   --> Status changed to: RUNNING")
                
                # 3. شبیه‌سازی پردازش (Wait)
                duration = job.estimated_duration or 10
                for i in range(duration):
                    time.sleep(1) # وقفه ۱ ثانیه‌ای
                    print(f"   ⏳ Processing... {i+1}/{duration}s")

                # 4. اتمام کار و تغییر وضعیت به COMPLETED
                job.status = "COMPLETED"
                job.completed_at = datetime.now() # ثبت زمان پایان
                db.commit()
                print("   --> Status changed to: COMPLETED ✅\n")
            
            else:
                # اگر کاری نبود، ۲ ثانیه صبر کن (برای کاهش فشار روی CPU)
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Error in worker: {e}")
        finally:
            # بستن اتصال دیتابیس در هر دور حلقه
            db.close()

if __name__ == "__main__":
    process_jobs()
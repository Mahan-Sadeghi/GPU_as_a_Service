import time
import sys
import os

# --- فیکس کردن مسیر برای پیدا کردن پوشه app ---
sys.path.append(os.getcwd())

from app import models, database

def process_jobs():
    print("👷 Worker started! Waiting for APPROVED jobs...")
    
    while True:
        db = database.SessionLocal()
        try:
            # فقط کارهایی که ادمین تایید کرده (APPROVED) رو پیدا کن
            # نکته: ورکر به کارهای PENDING (زرد) کاری نداره!
            job = db.query(models.Job).filter(models.Job.status == "APPROVED").first()

            if job:
                print(f"⚡ Found job {job.id}: {job.command}")
                
                # 1. تغییر وضعیت به آبی (در حال اجرا)
                job.status = "RUNNING"
                db.commit()
                print("   --> Status: RUNNING (Blue)")
                
                # شبیه‌سازی زمان اجرا
                duration = job.estimated_duration or 10
                for i in range(duration):
                    time.sleep(1)
                    print(f"   ⏳ Processing... {i+1}/{duration}")

                # 2. تغییر وضعیت به سبز (تمام شده)
                job.status = "COMPLETED"
                db.commit()
                print("   --> Status: COMPLETED (Green) ✅\n")
            
            else:
                # استراحت کوتاه وقتی کاری نیست
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    process_jobs()
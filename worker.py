# worker.py
import time
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
import models

# تابعی برای گرفتن ارتباط دیتابیس (مثل main.py)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_simulator():
    print("🤖 شبیه‌ساز GPU روشن شد و آماده کار است...")
    
    # حلقه بی‌نهایت برای چک کردن مداوم دیتابیس
    while True:
        # ساخت یک نشست (Session) جدید برای هر دور بررسی
        db: Session = SessionLocal()
        
        try:
            # ۱. پیدا کردن تسکی که وضعیتش APPROVED باشد (یعنی ادمین تایید کرده)
            # ما اولویت را به قدیمی‌ترین تسک می‌دهیم (First Come First Served)
            job = db.query(models.Job).filter(models.Job.status == "APPROVED").first()
            
            if job:
                print(f"✅ تسک جدید پیدا شد: ID={job.id} | {job.gpu_type} | مدت: {job.estimated_duration} ثانیه")
                
                # ۲. تغییر وضعیت به RUNNING
                job.status = "RUNNING"
                db.commit()
                print(f"⏳ تسک {job.id} در حال اجراست...")
                
                # ۳. شبیه‌سازی اجرا (Sleep)
                # نکته: ما اینجا ثانیه را به جای ساعت در نظر می‌گیریم تا دمو سریع باشد
                time.sleep(job.estimated_duration)
                
                # ۴. تغییر وضعیت به COMPLETED
                job.status = "COMPLETED"
                db.commit()
                print(f"🎉 تسک {job.id} با موفقیت تمام شد.\n")
                
            else:
                # اگر کاری نبود، ۵ ثانیه صبر کن و دوباره چک کن
                # print("💤 کاری برای انجام نیست...")
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ خطا در اجرا: {e}")
            
        finally:
            # حتما دیتابیس را ببندیم
            db.close()

if __name__ == "__main__":
    try:
        run_simulator()
    except KeyboardInterrupt:
        print("\n🛑 شبیه‌ساز خاموش شد.")
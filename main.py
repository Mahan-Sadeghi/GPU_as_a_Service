import os
from typing import List, Generator, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from app import models, schemas, database, security

# --- ساختار دیتابیس ---
# ایجاد جداول در صورت عدم وجود
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="GPU Service API",
    description="سیستم مدیریت منابع پردازشی با قابلیت سهمیه‌بندی",
    version="1.0.0"
)

# --- تنظیمات استاتیک و قالب‌ها ---
base_dir = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(base_dir, "static")
templates_path = os.path.join(base_dir, "templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# --- تنظیمات امنیتی CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db() -> Generator[Session, None, None]:
    """
    تولیدکننده نشست دیتابیس (Database Session Dependency).
    این تابع در هر درخواست اجرا شده و پس از پایان، ارتباط را می‌بندد.
    """
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
#              صفحات وب (Frontend)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    """نمایش صفحه ورود و ثبت‌نام."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    """نمایش داشبورد مدیریت درخواست‌ها."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ==========================================
#              مدیریت کاربران (Auth)
# ==========================================

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> dict:
    """
    احراز هویت کاربر و صدور توکن دسترسی (JWT).
    
    Args:
        form_data: شامل نام کاربری و رمز عبور.
    Returns:
        access_token: توکن رمزنگاری شده.
    """
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.UserResponse)
def register_user(
    user: schemas.UserCreate, 
    db: Session = Depends(get_db)
) -> models.User:
    """
    ثبت‌نام کاربر جدید در سیستم.
    
    - نام کاربری تکراری مجاز نیست.
    - نام کاربری 'admin' به صورت خودکار دسترسی مدیر می‌گیرد.
    - سهمیه اولیه: مدیر (1000 ثانیه)، کاربر عادی (120 ثانیه).
    """
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="این نام کاربری قبلا ثبت شده است.")
    
    hashed_password = security.get_password_hash(user.password)
    is_admin_role = (user.username == "admin")
    
    # تعیین سهمیه اولیه بر اساس نقش
    default_quota = 1000 if is_admin_role else 120
    
    new_user = models.User(
        username=user.username, 
        hashed_password=hashed_password, 
        is_admin=is_admin_role, 
        quota=default_quota
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)) -> models.User:
    """دریافت اطلاعات پروفایل کاربر لاگین شده."""
    return current_user

@app.post("/users/charge")
def charge_quota(
    amount: int = 100, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(security.get_current_user)
) -> dict:
    """
    API شارژ حساب (Placeholder).
    توجه: این بخش جهت اتصال آینده به درگاه پرداخت طراحی شده است.
    """
    # 🚧 TODO: پیاده‌سازی اتصال به درگاه پرداخت (Zarinpal/NextPay)
    # db_user = db.query(models.User).filter(models.User.id == current_user.id).first()
    # db_user.quota += amount
    # db.commit()
    
    return {
        "msg": "این قابلیت نیاز به درگاه پرداخت دارد (Future Feature)", 
        "current_quota": current_user.quota
    }

# ==========================================
#           مدیریت درخواست‌ها (Jobs)
# ==========================================

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(
    job: schemas.JobCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(security.get_current_user)
) -> models.Job:
    """
    ثبت درخواست پردازش جدید با کسر سهمیه.
    
    مراحل:
    1. اعتبارسنجی ورودی‌ها (تعداد گرافیک، امنیت دستور).
    2. بررسی محدودیت تعداد درخواست همزمان.
    3. بررسی و کسر سهمیه کاربر.
    """
    
    # 1. اعتبارسنجی ورودی
    if job.gpu_count <= 0:
        raise HTTPException(status_code=400, detail="تعداد کارت گرافیک باید حداقل ۱ باشد.")
    
    if job.gpu_count > 10:
        raise HTTPException(status_code=400, detail="حداکثر ۱۰ کارت گرافیک مجاز است.")

    dangerous_chars = [";", "&&", "|", "`", "$("]
    if any(char in job.command for char in dangerous_chars):
        raise HTTPException(status_code=400, detail="کاراکتر غیرمجاز در دستور.")

    # 2. محدودیت همزمانی (Rate Limiting)
    active_jobs = db.query(models.Job).filter(
        models.Job.owner_id == current_user.id,
        models.Job.status.in_(["PENDING", "RUNNING"])
    ).count()
    
    if active_jobs >= 2:
        raise HTTPException(status_code=400, detail="شما ۲ درخواست فعال دارید. لطفاً صبر کنید.")

    # دریافت مجدد آبجکت کاربر برای اعمال تغییرات اتمیک
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()

    # 3. بررسی و کسر سهمیه
    if db_user.quota < job.estimated_duration:
        raise HTTPException(
            status_code=400, 
            detail=f"سهمیه ناکافی! اعتبار: {db_user.quota}s | نیاز: {job.estimated_duration}s"
        )

    # کسر سهمیه
    db_user.quota -= job.estimated_duration
    
    # ثبت تسک
    new_job = models.Job(**job.dict(), owner_id=current_user.id)
    db.add(new_job)
    
    db.commit()
    db.refresh(new_job)
    
    return new_job

@app.get("/jobs/", response_model=List[schemas.JobResponse])
def read_jobs(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(security.get_current_user)
) -> List[models.Job]:
    """
    دریافت لیست درخواست‌ها.
    - ادمین: مشاهده تمام درخواست‌ها.
    - کاربر عادی: مشاهده درخواست‌های خود.
    """
    if current_user.is_admin:
        jobs = db.query(models.Job).all()
    else:
        jobs = db.query(models.Job).filter(models.Job.owner_id == current_user.id).all()
    return jobs

@app.put("/jobs/{job_id}", response_model=schemas.JobResponse)
def update_job_status(
    job_id: int, 
    status_update: str, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(security.get_current_user)
) -> models.Job:
    """
    تغییر وضعیت درخواست (مخصوص مدیر سیستم).
    مثال: تایید (APPROVED) یا رد (FAILED) درخواست.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
        
    job.status = status_update
    db.commit()
    db.refresh(job)
    return job

# این جایگزین تابع delete_job فعلی بشه
@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    
    if not current_user.is_admin and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="شما اجازه حذف این تسک را ندارید")

    # 👇 منطق جدید: بازگشت سهمیه (Refund)
    # فقط اگر وضعیت PENDING باشد، یعنی هنوز منابع مصرف نشده و باید برگردد
    if job.status == "PENDING":
        # صاحب تسک را پیدا می‌کنیم (شاید ادمین داره حذف می‌کنه، پس باید صاحب اصلی رو پیدا کنیم)
        owner = db.query(models.User).filter(models.User.id == job.owner_id).first()
        owner.quota += job.estimated_duration
        print(f"💰 Refunded {job.estimated_duration}s to user {owner.username}")

    db.delete(job)
    db.commit()
    return None
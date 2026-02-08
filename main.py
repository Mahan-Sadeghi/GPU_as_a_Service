"""
فایل اصلی برنامه (Main Application Entry Point)
---------------------------------------------
این فایل وظیفه راه‌اندازی سرور FastAPI و مدیریت تمام درخواست‌های HTTP را بر عهده دارد.
بخش‌های اصلی:
1. تنظیمات دیتابیس و CORS.
2. مدیریت صفحات وب (Frontend Rendering).
3. سیستم احراز هویت و ثبت‌نام (Authentication).
4. مدیریت درخواست‌های پردازشی (Jobs & Quota Management).
"""

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

# ==========================================
#              تنظیمات اولیه (Setup)
# ==========================================

# ایجاد جداول دیتابیس در صورتی که وجود نداشته باشند
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="GPU Service API",
    description="سیستم مدیریت منابع پردازشی با قابلیت سهمیه‌بندی و صف‌بندی درخواست‌ها",
    version="1.0.0"
)

# تنظیم مسیرهای فایل‌های استاتیک و قالب‌ها (Templates)
base_dir = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(base_dir, "static")
templates_path = os.path.join(base_dir, "templates")

# اتصال پوشه static برای فایل‌های CSS و JS
app.mount("/static", StaticFiles(directory=static_path), name="static")
# تنظیم موتور قالب‌ساز Jinja2
templates = Jinja2Templates(directory=templates_path)

# تنظیمات امنیتی CORS (برای اجازه دسترسی از دامنه‌های مختلف)
# در محیط توسعه همه دامنه‌ها (*) مجاز هستند.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db() -> Generator[Session, None, None]:
    """
    تزریق وابستگی دیتابیس (Dependency Injection).
    
    این تابع در شروع هر درخواست یک نشست (Session) جدید ایجاد می‌کند
    و پس از پایان درخواست، آن را می‌بندد تا منابع سرور آزاد شوند.
    """
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
#              صفحات وب (Frontend Routes)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    """رندر کردن صفحه ورود و ثبت‌نام (Landing Page)."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    """رندر کردن صفحه داشبورد مدیریت درخواست‌ها."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ==========================================
#              مدیریت کاربران (Authentication)
# ==========================================

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> dict:
    """
    دریافت توکن دسترسی (JWT Login).
    
    1. نام کاربری و رمز عبور بررسی می‌شود.
    2. در صورت صحت، یک توکن JWT با اعتبار محدود صادر می‌شود.
    """
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # ایجاد توکن با استفاده از نام کاربری
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.UserResponse)
def register_user(
    user: schemas.UserCreate, 
    db: Session = Depends(get_db)
) -> models.User:
    """
    ثبت‌نام کاربر جدید.
    
    قوانین بیزنس:
    - نام کاربری نباید تکراری باشد.
    - اگر نام کاربری 'admin' باشد، دسترسی ادمین و سهمیه ویژه (1000 ثانیه) می‌گیرد.
    - کاربران عادی سهمیه پیش‌فرض (120 ثانیه) دریافت می‌کنند.
    """
    # بررسی تکراری نبودن نام کاربری
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="این نام کاربری قبلا ثبت شده است.")
    
    # هش کردن رمز عبور قبل از ذخیره
    hashed_password = security.get_password_hash(user.password)
    
    # منطق تعیین ادمین به صورت خودکار
    is_admin_role = (user.username == "admin")
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
    """دریافت اطلاعات پروفایل کاربر فعلی (شامل سهمیه باقی‌مانده)."""
    return current_user

@app.post("/users/charge")
def charge_quota(
    amount: int = 100, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(security.get_current_user)
) -> dict:
    """
    شبیه‌سازی شارژ حساب (Placeholder API).
    
    نکته: در نسخه نهایی، این اندپوینت باید به درگاه پرداخت متصل شود
    و پس از تایید تراکنش، سهمیه را افزایش دهد.
    """
    return {
        "msg": "این قابلیت نیاز به درگاه پرداخت دارد (Future Feature)", 
        "current_quota": current_user.quota
    }

# ==========================================
#           مدیریت درخواست‌ها (Job Management)
# ==========================================

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(
    job: schemas.JobCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(security.get_current_user)
) -> models.Job:
    """
    ثبت درخواست پردازش جدید (Create Job).
    
    مراحل اعتبارسنجی و منطق تجاری:
    1. بررسی ورودی‌ها (تعداد گرافیک معتبر باشد).
    2. امنیت: جلوگیری از تزریق کد (Command Injection) با بررسی کاراکترهای خطرناک.
    3. محدودیت نرخ (Rate Limiting): کاربر نباید بیش از 2 درخواست فعال همزمان داشته باشد.
    4. بررسی سهمیه: اگر سهمیه کافی نباشد، درخواست رد می‌شود.
    5. کسر سهمیه و ثبت درخواست در صف.
    """
    
    # 1. اعتبارسنجی ورودی (Validation)
    if job.gpu_count <= 0:
        raise HTTPException(status_code=400, detail="تعداد کارت گرافیک باید حداقل ۱ باشد.")
    
    if job.gpu_count > 10:
        raise HTTPException(status_code=400, detail="حداکثر ۱۰ کارت گرافیک مجاز است.")

    # 2. بررسی امنیتی دستورات (Security Check)
    dangerous_chars = [";", "&&", "|", "`", "$("]
    if any(char in job.command for char in dangerous_chars):
        raise HTTPException(status_code=400, detail="کاراکتر غیرمجاز در دستور (Security Alert).")

    # 3. محدودیت همزمانی (Rate Limiting)
    active_jobs = db.query(models.Job).filter(
        models.Job.owner_id == current_user.id,
        models.Job.status.in_(["PENDING", "RUNNING"])
    ).count()
    
    if active_jobs >= 2:
        raise HTTPException(status_code=400, detail="شما ۲ درخواست فعال دارید. لطفاً تا پایان آنها صبر کنید.")

    # دریافت مجدد آبجکت کاربر برای اعمال تغییرات اتمیک روی سهمیه
    db_user = db.query(models.User).filter(models.User.id == current_user.id).first()

    # 4. بررسی موجودی سهمیه (Quota Check)
    if db_user.quota < job.estimated_duration:
        raise HTTPException(
            status_code=400, 
            detail=f"سهمیه ناکافی! اعتبار شما: {db_user.quota} ثانیه | مورد نیاز: {job.estimated_duration} ثانیه"
        )

    # 5. کسر سهمیه و ذخیره (Deduct & Save)
    db_user.quota -= job.estimated_duration
    
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
    
    - اگر کاربر **ادمین** باشد: تمام درخواست‌های سیستم را می‌بیند.
    - اگر کاربر **عادی** باشد: فقط درخواست‌های خودش را می‌بیند.
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
    کاربرد: تایید دستی (APPROVED) یا رد کردن (FAILED) درخواست‌ها توسط ادمین.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="فقط مدیر سیستم دسترسی دارد.")
    
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک مورد نظر یافت نشد.")
        
    job.status = status_update
    db.commit()
    db.refresh(job)
    return job

@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(security.get_current_user)
):
    """
    حذف درخواست و بازگشت سهمیه (Refund Logic).
    
    - کاربر فقط می‌تواند درخواست‌های خودش را حذف کند (مگر اینکه ادمین باشد).
    - **مهم:** اگر وضعیت درخواست PENDING باشد (یعنی هنوز اجرا نشده)،
      سهمیه کسر شده به حساب کاربر **برمی‌گردد**.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک یافت نشد.")
    
    # بررسی دسترسی حذف
    if not current_user.is_admin and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="شما اجازه حذف این تسک را ندارید.")

    # منطق بازگشت وجه (Refund Policy)
    # اگر هنوز منابع مصرف نشده‌اند (PENDING)، سهمیه را پس می‌دهیم.
    if job.status == "PENDING":
        owner = db.query(models.User).filter(models.User.id == job.owner_id).first()
        if owner:
            owner.quota += job.estimated_duration
            print(f"💰 بازگشت سهمیه: {job.estimated_duration} ثانیه به کاربر {owner.username} برگردانده شد.")

    db.delete(job)
    db.commit()
    return None
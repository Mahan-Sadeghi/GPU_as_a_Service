import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from app import models, schemas, database, security

# --- 1. ساخت جداول دیتابیس ---
# این خط چک می‌کند اگر دیتابیس نباشد، آن را می‌سازد
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# --- 2. تنظیم آدرس‌دهی فایل‌ها ---
# پیدا کردن مسیر دقیق پوشه‌های static و templates برای جلوگیری از ارور
base_dir = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(base_dir, "static")
templates_path = os.path.join(base_dir, "templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# تنظیمات CORS (برای امنیت مرورگر)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تابع اتصال به دیتابیس (هر بار باز و بسته می‌شود)
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
#              صفحات وب (HTML)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    """نمایش صفحه ورود و ثبت‌نام"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    """نمایش داشبورد مدیریت"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ==========================================
#              API های سیستم
# ==========================================

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """API برای ورود کاربر و دریافت توکن"""
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نام کاربری یا رمز عبور اشتباه است", headers={"WWW-Authenticate": "Bearer"})
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """API ثبت‌نام کاربر جدید"""
    # چک کردن تکراری نبودن
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="این نام کاربری قبلا ثبت شده است.")
    
    hashed_password = security.get_password_hash(user.password)
    
    # اگر نام کاربری admin بود، خودکار دسترسی مدیر می‌گیرد
    is_admin_role = (user.username == "admin")
    
    new_user = models.User(username=user.username, hashed_password=hashed_password, is_admin=is_admin_role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """دریافت اطلاعات کاربر لاگین شده"""
    return current_user

# --- مدیریت درخواست‌ها (Jobs) ---

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    """ثبت درخواست پردازش جدید با محدودیت‌های امنیتی"""
    
    # 1. جلوگیری از عدد منفی یا صفر
    if job.gpu_count <= 0:
        raise HTTPException(status_code=400, detail="تعداد کارت گرافیک باید حداقل ۱ باشد.")
    
    # 2. سقف تعداد گرافیک (Resource Limit)
    if job.gpu_count > 10:
        raise HTTPException(status_code=400, detail="حداکثر ۱۰ کارت گرافیک مجاز است.")

    # 3. امنیت دستورات (جلوگیری از هک)
    dangerous_chars = [";", "&&", "|", "`", "$("]
    if any(char in job.command for char in dangerous_chars):
        raise HTTPException(status_code=400, detail="کاراکتر غیرمجاز در دستور.")

    # 4. محدودیت تعداد درخواست همزمان (Rate Limiting)
    active_jobs = db.query(models.Job).filter(
        models.Job.owner_id == current_user.id,
        models.Job.status.in_(["PENDING", "RUNNING"])
    ).count()
    
    if active_jobs >= 2:
        raise HTTPException(status_code=400, detail="شما ۲ درخواست فعال دارید. لطفاً صبر کنید.")
        
    new_job = models.Job(**job.dict(), owner_id=current_user.id)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/", response_model=List[schemas.JobResponse])
def read_jobs(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    """دریافت لیست درخواست‌ها (ادمین همه را می‌بیند، کاربر فقط مال خودش را)"""
    if current_user.is_admin:
        jobs = db.query(models.Job).all()
    else:
        jobs = db.query(models.Job).filter(models.Job.owner_id == current_user.id).all()
    return jobs

@app.put("/jobs/{job_id}", response_model=schemas.JobResponse)
def update_job_status(job_id: int, status_update: str, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    """تغییر وضعیت درخواست (مخصوص ادمین)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
        
    job.status = status_update
    db.commit()
    db.refresh(job)
    return job

@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    """حذف درخواست (توسط ادمین یا صاحب درخواست)"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
    
    if not current_user.is_admin and job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="شما اجازه حذف این تسک را ندارید")
        
    db.delete(job)
    db.commit()
    return None
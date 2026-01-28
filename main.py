from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

# ایمپورت ماژول‌های خودمان (که در پوشه app هستند)
from app import models, schemas, security, database
from app.database import SessionLocal, engine

# ساخت جداول دیتابیس (اگر از قبل نباشند)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GPU Service Manager",
    description="سامانه مدیریت و اجاره کارت گرافیک ابری",
    version="0.3.0"
)

# تنظیمات پوشه قالب‌ها (HTML)
templates = Jinja2Templates(directory="templates")

# وابستگی دیتابیس (هر درخواست یک سشن می‌گیرد و می‌بندد)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 1. بخش احراز هویت (Auth) ---

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # بررسی اینکه نام کاربری تکراری نباشد
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="این نام کاربری قبلاً گرفته شده است.")

    # هش کردن رمز عبور (برای امنیت)
    hashed_pass = security.get_password_hash(user.password)

    # لاجیک تشخیص ادمین (پارتی‌بازی برای یوزر admin)
    is_admin_role = False
    if user.username == "admin":
        is_admin_role = True

    # ساخت آبجکت کاربر جدید
    new_user = models.User(
        username=user.username, 
        hashed_password=hashed_pass,
        is_admin=is_admin_role
    )
    
    # ذخیره در دیتابیس
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # بررسی صحت یوزرنیم و پسورد
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # تعیین زمان انقضای توکن
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # ساخت توکن نهایی (وضعیت ادمین بودن را هم داخلش می‌گذاریم)
    access_token = security.create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    # نمایش اطلاعات کاربر لاگین شده
    return current_user

# --- 2. بخش مدیریت تسک‌ها (Jobs) ---

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(
    job: schemas.JobCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # محدودیت: هر کاربر فقط ۵ تسک فعال همزمان داشته باشد
    active_jobs = db.query(models.Job).filter(models.Job.owner_id == current_user.id, models.Job.status == "PENDING").count()
    if active_jobs >= 5:
        raise HTTPException(status_code=400, detail="شما بیش از حد مجاز درخواست فعال دارید.")

    # ساخت تسک جدید و اتصال آن به کاربر فعلی
    new_job = models.Job(**job.dict(), owner_id=current_user.id)
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/", response_model=List[schemas.JobResponse])
def read_jobs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # ادمین همه درخواست‌ها را می‌بیند، کاربر عادی فقط مال خودش را
    if current_user.is_admin:
        jobs = db.query(models.Job).offset(skip).limit(limit).all()
    else:
        jobs = db.query(models.Job).filter(models.Job.owner_id == current_user.id).offset(skip).limit(limit).all()
    return jobs

@app.put("/jobs/{job_id}", response_model=schemas.JobResponse)
def update_job_status(
    job_id: int, 
    status_update: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # گارد امنیتی: فقط ادمین حق تایید دارد
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی ادمین ندارید."
        )

    # پیدا کردن تسک
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک پیدا نشد.")

    # جلوگیری از تغییر وضعیت تسکی که تمام شده
    if job.status in ["COMPLETED", "FAILED"] and status_update == "APPROVED":
         raise HTTPException(status_code=400, detail="این تسک قبلاً نهایی شده است.")

    # اعمال تغییر وضعیت
    job.status = status_update
    db.commit()
    db.refresh(job)
    return job

# --- 3. صفحات فرانت‌اند (HTML) ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # صفحه اصلی (لاگین/ثبت‌نام)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def view_dashboard(request: Request):
    # صفحه داشبورد مدیریت
    return templates.TemplateResponse("dashboard.html", {"request": request})
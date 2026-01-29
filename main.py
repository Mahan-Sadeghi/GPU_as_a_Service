import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# 👇 این خط جدید اضافه شد: وارد کردن فرم استاندارد لاگین
from fastapi.security import OAuth2PasswordRequestForm

# ماژول‌های دیتابیس از پوشه app
from app import models, schemas, database, security

# ساخت جداول
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# --- تنظیم آدرس‌دهی دقیق ---
base_dir = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(base_dir, "static")
templates_path = os.path.join(base_dir, "templates")

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)
# ---------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- صفحات ---
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# --- API ها ---

# 👇 اینجا اصلاح شد: security.OAuth... حذف شد و فقط OAuth... ماند
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نام کاربری یا رمز عبور اشتباه است", headers={"WWW-Authenticate": "Bearer"})
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="این نام کاربری قبلا ثبت شده است.")
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password, is_admin=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    if job.gpu_count <= 0:
        raise HTTPException(status_code=400, detail="تعداد کارت گرافیک باید حداقل ۱ باشد.")
    dangerous_chars = [";", "&&", "|", "`", "$("]
    if any(char in job.command for char in dangerous_chars):
        raise HTTPException(status_code=400, detail="کاراکتر غیرمجاز")
        
    new_job = models.Job(**job.dict(), owner_id=current_user.id)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/", response_model=List[schemas.JobResponse])
def read_jobs(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    if current_user.is_admin:
        jobs = db.query(models.Job).all()
    else:
        jobs = db.query(models.Job).filter(models.Job.owner_id == current_user.id).all()
    return jobs

@app.put("/jobs/{job_id}", response_model=schemas.JobResponse)
def update_job_status(job_id: int, status_update: str, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک یافت نشد")
        
    job.status = status_update
    db.commit()
    db.refresh(job)
    return job
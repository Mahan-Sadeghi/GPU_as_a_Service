# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

# ایمپورت کردن فایل‌هایی که خودمان ساختیم
from app import models, schemas, security, database

# ساخت اپلیکیشن اصلی
app = FastAPI(
    title="GPU Service Manager",
    description="سامانه مدیریت و تخصیص منابع پردازشی (پروژه پایانی)",
    version="0.1.0"
)

# ساخت جداول دیتابیس (اگر وجود نداشته باشند)
models.Base.metadata.create_all(bind=database.engine)

# آدرس اندپوینت توکن برای دکمه Authorize در Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# وابستگی (Dependency) برای گرفتن دیتابیس در هر درخواست
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- توابع کمکی (Dependencies) ---

# تابعی که توکن را چک می‌کند و کاربر فعلی را برمی‌گرداند
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="اعتبارنامه معتبر نیست (Token Invalid)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # رمزگشایی توکن
        payload = security.jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except security.JWTError:
        raise credentials_exception
    
    # پیدا کردن کاربر از دیتابیس
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- اندپوینت‌های احراز هویت (Auth Routes) ---

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # چک کنیم که یوزرنیم تکراری نباشد
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="این نام کاربری قبلا ثبت شده است")
    
    # ساخت کاربر جدید
    hashed_password = security.get_password_hash(user.password)
    # اولین کاربر را به عنوان Admin ثبت می‌کنیم (برای تست راحت‌تر)
    # اگر دیتابیس خالی بود -> ادمین، وگرنه -> یوزر معمولی
    is_first_user = db.query(models.User).count() == 0
    role = "admin" if is_first_user else "user"
    
    new_user = models.User(
        username=user.username, 
        hashed_password=hashed_password,
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # پیدا کردن کاربر
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    # چک کردن پسورد
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # ساخت توکن
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# یک روت تستی برای چک کردن اینکه توکن کار می‌کند یا نه
@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# --- اندپوینت‌های مدیریت تسک‌ها (Jobs) ---

@app.post("/jobs/", response_model=schemas.JobResponse)
def create_job(
    job: schemas.JobCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # محاسبه هزینه تسک (تعداد کارت گرافیک * زمان تخمینی)
    # طبق فایل پروژه، باید سهمیه کاربر چک شود
    task_cost = job.gpu_count * job.estimated_duration
    
    # محاسبه کل مصرف کاربر تا الان (فقط کارهایی که رد نشده‌اند)
    # یعنی Pending, Approved, Running, Completed
    current_usage = 0
    for j in current_user.jobs:
        if j.status != "FAILED": # فرض می‌کنیم کارهای رد شده سهمیه را برمی‌گردانند
            current_usage += (j.gpu_count * j.estimated_duration)
            
    # چک کردن اینکه آیا اعتبار کافی دارد؟
    if current_usage + task_cost > current_user.quota_limit:
        raise HTTPException(
            status_code=400, 
            detail=f"اعتبار کافی نیست! اعتبار شما: {current_user.quota_limit}، مصرف شده: {current_usage}، هزینه این تسک: {task_cost}"
        )

    # ساخت آبجکت تسک
    new_job = models.Job(
        **job.dict(), # کپی کردن همه فیلدها (gpu_type, count, ...)
        owner_id=current_user.id
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/", response_model=list[schemas.JobResponse])
def read_jobs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # اگر ادمین بود، همه تسک‌ها را ببیند
    if current_user.role == "admin":
        jobs = db.query(models.Job).offset(skip).limit(limit).all()
    else:
        # اگر کاربر عادی بود، فقط تسک‌های خودش
        jobs = db.query(models.Job).filter(models.Job.owner_id == current_user.id).all()
    return jobs

# این روت مخصوص ادمین است برای تایید یا رد تسک
@app.put("/jobs/{job_id}", response_model=schemas.JobResponse)
def update_job_status(
    job_id: int, 
    status_update: str, # مثلا "APPROVED" یا "FAILED"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # چک کنیم که حتما ادمین باشد
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط مدیر سیستم اجازه تغییر وضعیت دارد")
    
    # پیدا کردن تسک
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="تسک پیدا نشد")
        
    # تغییر وضعیت
    job.status = status_update
    db.commit()
    db.refresh(job)
    return job


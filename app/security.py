"""
ماژول امنیت و احراز هویت (Security & Auth)
------------------------------------------
وظایف:
1. هش کردن و بررسی رمز عبور (Hashing).
2. تولید و رمزگشایی توکن‌های JWT.
3. تزریق وابستگی (Dependency Injection) برای گرفتن کاربر فعلی.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models, database

# تنظیمات امنیتی JWT
SECRET_KEY = "mysecretkey"  # در محیط واقعی باید از Environment Variable خوانده شود
ALGORITHM = "HS256"         # الگوریتم رمزنگاری
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # مدت اعتبار توکن

# تنظیمات هش کردن پسورد (استفاده از الگوریتم bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# اسکیمای OAuth2 (برای دریافت توکن از هدر Authorization)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """بررسی صحت رمز عبور وارد شده با هش ذخیره شده در دیتابیس"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """تبدیل رمز عبور متنی به هش (Hash)"""
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """پیدا کردن کاربر در دیتابیس و بررسی رمز عبور"""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    تولید توکن JWT.
    شامل نام کاربری (sub) و زمان انقضا (exp).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    """
    تزریق وابستگی دیتابیس (Database Dependency).
    یک نشست (Session) باز می‌کند و پس از اتمام درخواست آن را می‌بندد.
    """
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    تزریق وابستگی کاربر فعلی (Authentication Dependency).
    1. توکن را از هدر می‌گیرد.
    2. آن را رمزگشایی می‌کند.
    3. کاربر مربوطه را از دیتابیس پیدا می‌کند.
    اگر هر مشکلی باشد، خطای 401 برمی‌گرداند.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="اعتبارنامه معتبر نیست (Could not validate credentials)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # رمزگشایی توکن
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # جستجوی کاربر در دیتابیس
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user
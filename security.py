# security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# کلید مخفی برای امضای توکن‌ها (در پروژه واقعی باید از env خوانده شود)
SECRET_KEY = "my_super_secret_key_for_project"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # مدت اعتبار توکن

# تنظیمات مربوط به هش کردن پسورد
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# تابع برای چک کردن اینکه آیا پسورد وارد شده با هش ذخیره شده یکی هست یا نه
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# تابع برای تبدیل پسورد متنی به هش (رمزنگاری شده)
def get_password_hash(password):
    return pwd_context.hash(password)

# تابع برای ساخت توکن JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # اگر زمانی داده نشد، پیش‌فرض ۱۵ دقیقه در نظر بگیر
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    # ساخت توکن نهایی
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
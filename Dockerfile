# استفاده از نسخه سبک پایتون
FROM python:3.9-slim

# تنظیم دایرکتوری کاری
WORKDIR /app

# جلوگیری از تولید فایل‌های اضافی پایتون
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# کپی کردن فایل نیازمندی‌ها و نصب آن‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن کل پروژه
COPY . .

# باز کردن پورت 8000
EXPOSE 8000

# دستور اجرا
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
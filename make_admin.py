import sqlite3

# اسم یوزری که الان باهاش لاگین میکنی رو اینجا بنویس
USERNAME_TO_PROMOTE = "mahan"  # <--- اینجا اسم خودت رو بنویس

try:
    # اتصال به دیتابیس
    conn = sqlite3.connect('gpu_service.db')
    cursor = conn.cursor()
    
    # آپدیت کردن کاربر
    cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (USERNAME_TO_PROMOTE,))
    
    if cursor.rowcount > 0:
        print(f"✅ موفقیت! کاربر '{USERNAME_TO_PROMOTE}' الان ادمین شد.")
        print("حالا برو توی سایت، لاگ اوت کن و دوباره لاگین کن.")
    else:
        print(f"❌ خطا: کاربری با اسم '{USERNAME_TO_PROMOTE}' پیدا نشد.")
        print("مطمئن شو که اسم رو درست نوشتی و قبلا ثبت‌نام کردی.")
        
    conn.commit()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
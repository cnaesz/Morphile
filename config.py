import os

BOT_TOKEN = "8106538116:AAG6sVrZnU-hZWyCfk0hG7kT8u9ezZYY0pA"
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "filebot"

# مسیر فایل‌ها
DOWNLOAD_DIR = "/var/www/files"
NGINX_URL = "https://yourdomain.com/files"  # یا http://IP/files

# محدودیت‌ها
FREE_DAILY_LIMIT = 1 * 1024 * 1024 * 1024        # 1 گیگ رایگان
PREMIUM_DAILY_LIMIT = 50 * 1024 * 1024 * 1024  # 50 گیگ در ماه

# قیمت‌ها (تومان)
PRICING = {
    "1_month": {"price": 50000, "duration_days": 30},
    "3_months": {"price": 135000, "duration_days": 90},  # 10% off
    "12_months": {"price": 480000, "duration_days": 365} # 20% off
}

# زرین‌پال
ZARINPAL_MERCHANT = "your-zarinpal-merchant-id"
ZARINPAL_CALLBACK = "https://yourdomain.com/verify"

# ادمین
ADMIN_IDS = [123456789]  # آیدی عددی ادمین

# Mini App
WEB_APP_URL = "https://yourdomain.com/app"  # صفحه خرید
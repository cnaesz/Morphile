import os

# --- Security Note ---
# For production, it's strongly recommended to use environment variables
# instead of hardcoding secrets like tokens and database URIs.
# Example: BOT_TOKEN = os.environ.get("BOT_TOKEN")

BOT_TOKEN = "####"
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "filebot"

# File paths
DOWNLOAD_DIR = "/var/www/files"
# --- Security Note ---
# If you configure NGINX_URL, ensure that your web server configuration
# does not allow directory listing for the DOWNLOAD_DIR.
# Files in this directory should only be accessible via the generated links,
# not by browsing the directory.
NGINX_URL = "https://yourdomain.com/files"

# Usage Limits
FREE_DAILY_LIMIT = 100 * 1024 * 1024  # 100 MB
PREMIUM_DAILY_LIMIT_50GB = 50 * 1024 * 1024 * 1024  # 50 GB
PREMIUM_DAILY_LIMIT_100GB = 100 * 1024 * 1024 * 1024 # 100 GB

# Pricing (Toman)
PRICING = {
    "1_month_50gb": {"price": 50000, "duration_days": 30, "limit": PREMIUM_DAILY_LIMIT_50GB},
    "1_month_100gb": {"price": 80000, "duration_days": 30, "limit": PREMIUM_DAILY_LIMIT_100GB},
    "3_months_50gb": {"price": 135000, "duration_days": 90, "limit": PREMIUM_DAILY_LIMIT_50GB},
    "3_months_100gb": {"price": 215000, "duration_days": 90, "limit": PREMIUM_DAILY_LIMIT_100GB},
}

# Zarinpal
ZARINPAL_MERCHANT = "your-zarinpal-merchant-id"
ZARINPAL_CALLBACK = "https://yourdomain.com/verify"

# Admin
ADMIN_IDS = [123456789]  # Numeric admin IDs

# Mini App
WEB_APP_URL = "https://yourdomain.com/app"  # Purchase page
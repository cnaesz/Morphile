import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Environment Settings ---
# The DEBUG flag enables more detailed logging.
# For production, it is strongly recommended to set DEBUG = False.
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# --- Security Note ---
# For production, it's strongly recommended to use environment variables
# instead of hardcoding secrets like tokens and database URIs.
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set! Please add it to your .env file or environment variables.")

# --- Database Configuration ---
# If MONGO_URI is in the environment, it will be used.
# Otherwise, it defaults to a local MongoDB instance.
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "filebot"

# --- File Paths ---
# DOWNLOAD_DIR: Temporary directory for files downloaded from Telegram.
# PUBLIC_FILES_DIR: Directory where final, processed files are stored to be served publicly.
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
PUBLIC_FILES_DIR = os.environ.get("PUBLIC_FILES_DIR", "public_files")
# Ensure directories exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PUBLIC_FILES_DIR, exist_ok=True)


# --- Public URL and Server Config ---
# BASE_URL: The public-facing base URL where your files will be accessible.
# For local testing, this will be your local server (e.g., http://localhost:8080).
# For production, this will be your domain (e.g., http://your-domain.com/files).
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip('/')

# LOCAL_SERVER_PORT: The port for the simple Python HTTP server for local testing.
LOCAL_SERVER_PORT = int(os.environ.get("LOCAL_SERVER_PORT", 8080))


# Usage Limits
FREE_DAILY_LIMIT = 2 * 1024 * 1024 * 1024  # 2 GB
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
ZARINPAL_MERCHANT = os.environ.get("ZARINPAL_MERCHANT")
ZARINPAL_CALLBACK = os.environ.get("ZARINPAL_CALLBACK", "http://localhost:5001/verify")


# --- File Size Limits ---
# The maximum size for a single file upload/download.
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024 # 2 GB


# Admin & Manual Premium Users
# ---------------------------
# ADMIN_IDS: A comma-separated list of user IDs that have access to the admin panel.
#            e.g., "12345,67890"
# MANUAL_PREMIUM_USERS: A comma-separated list of user IDs to be granted permanent
#                       premium status for testing or other purposes.
#                       e.g., "11111,22222"

admin_ids_str = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in admin_ids_str.split(',') if admin_id.strip()]

manual_premium_users_str = os.environ.get("MANUAL_PREMIUM_USERS", "")
MANUAL_PREMIUM_USERS = [int(user_id.strip()) for user_id in manual_premium_users_str.split(',') if user_id.strip()]


if not ADMIN_IDS:
    print("Warning: ADMIN_IDS is not set. Admin panel will not be available to anyone.")


# --- Local Testing ---
# When True, the bot will enable test commands like /test_upload.
# It is strongly recommended to keep this False in production.
LOCAL_TEST_MODE = os.environ.get('LOCAL_TEST_MODE', 'False').lower() == 'true'


# --- Job Queue (Redis) ---
# Connection settings for the Redis server used by Dramatiq for background tasks.
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
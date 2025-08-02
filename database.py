# database.py
from pymongo import MongoClient
from datetime import datetime, timedelta
import config

client = MongoClient(config.MONGO_URI)
db = client[config.DATABASE_NAME]
users = db.users
payments = db.payments

def get_user(user_id):
    user = users.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "is_premium": False,
            "premium_expires": None,
            "daily_usage": 0,
            "monthly_usage": 0,
            "last_reset_day": datetime.utcnow(),
            "last_reset_month": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        users.insert_one(user)
    return user

def update_daily_usage(user_id, added_bytes):
    user = get_user(user_id)
    now = datetime.utcnow()
    
    # ریست روزانه
    if now - user["last_reset_day"] > timedelta(days=1):
        users.update_one(
            {"user_id": user_id},
            {"$set": {"daily_usage": 0, "last_reset_day": now}}
        )
        user["daily_usage"] = 0

    new_usage = user["daily_usage"] + added_bytes
    users.update_one(
        {"user_id": user_id},
        {"$inc": {"daily_usage": added_bytes}}
    )
    return new_usage

def update_monthly_usage(user_id, added_bytes):
    user = get_user(user_id)
    now = datetime.utcnow()

    # ریست ماهانه اگر اشتراک فعال باشد
    if user["is_premium"] and now - user["last_reset_month"] > timedelta(days=30):
        users.update_one(
            {"user_id": user_id},
            {"$set": {"monthly_usage": 0, "last_reset_month": now}}
        )
        user["monthly_usage"] = 0

    new_usage = user["monthly_usage"] + added_bytes
    users.update_one(
        {"user_id": user_id},
        {"$inc": {"monthly_usage": added_bytes}}
    )
    return new_usage

def set_premium(user_id, duration_days):
    expires = datetime.utcnow() + timedelta(days=duration_days)
    users.update_one(
        {"user_id": user_id},
        {"$set": {
            "is_premium": True,
            "premium_expires": expires,
            "last_reset_month": datetime.utcnow()
        }}
    )

def check_premium(user_id):
    user = get_user(user_id)
    if user["is_premium"]:
        if user["premium_expires"] and datetime.utcnow() > user["premium_expires"]:
            users.update_one(
                {"user_id": user_id},
                {"$set": {"is_premium": False}}
            )
            return False
        return True
    return False
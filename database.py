# database.py
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timedelta
import config
import logging

# --- Database Connection ---
# The connection is established based on the MONGO_URI from the config.
# A log message indicates whether a local or remote (Atlas) DB is used.
logging.info("Initializing database connection...")
client = MongoClient(config.MONGO_URI)
db = client[config.DATABASE_NAME]
users = db.users

if "localhost" in config.MONGO_URI:
    logging.info(f"Connected to LOCAL MongoDB at {config.MONGO_URI}")
else:
    logging.info(f"Connected to REMOTE MongoDB Atlas instance.")

# --- Test Connection ---
try:
    client.admin.command('ping')
    logging.info("MongoDB connection successful.")
except Exception as e:
    logging.error(f"MongoDB connection failed: {e}")
payments = db.payments
pending_payments = db.pending_payments

# --- Database Indexing ---
# Create an index on user_id for faster lookups.
users.create_index([("user_id", ASCENDING)], unique=True)
pending_payments.create_index([("authority", ASCENDING)], unique=True)

def get_user(user_id):
    """Fetches a user from the database, creating them if they don't exist."""
    user = users.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "is_premium": False,
            "premium_expires": None,
            "daily_usage": 0,
            "daily_limit_bytes": config.FREE_DAILY_LIMIT,
            "last_reset_day": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        users.insert_one(user)
    return user

def update_usage(user_id, added_bytes):
    """Updates a user's daily usage and returns their new total usage."""
    # The daily reset is now handled by the cleanup.py script.
    # This function now only increments the usage.
    result = users.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"daily_usage": added_bytes}},
        return_document=True
    )
    return result['daily_usage'] if result else 0

def set_premium(user_id, duration_days, limit_bytes):
    """Grants premium status to a user with a specified duration and daily limit."""
    expires = datetime.utcnow() + timedelta(days=duration_days)
    users.update_one(
        {"user_id": user_id},
        {"$set": {
            "is_premium": True,
            "premium_expires": expires,
            "daily_limit_bytes": limit_bytes,
            "daily_usage": 0,  # Reset usage on upgrade
            "last_reset_day": datetime.utcnow()
        }}
    )

def check_premium_status():
    """
    Scans for expired premium users and reverts them to free users.
    This is intended to be run periodically by a cleanup script.
    """
    now = datetime.utcnow()
    expired_users = users.find({
        "is_premium": True,
        "premium_expires": {"$lt": now}
    })

    count = 0
    for user in expired_users:
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "is_premium": False,
                "premium_expires": None,
                "daily_limit_bytes": config.FREE_DAILY_LIMIT
            }}
        )
        count += 1
    return count

def get_all_users():
    """Returns a cursor for all users in the database."""
    return users.find()

def reset_all_daily_usage():
    """Resets the daily_usage for all users to 0."""
    result = users.update_many({}, {"$set": {"daily_usage": 0, "last_reset_day": datetime.utcnow()}})
    return result.modified_count

def revoke_premium(user_id):
    """Revokes premium status from a user, reverting them to the free plan."""
    users.update_one(
        {"user_id": user_id},
        {"$set": {
            "is_premium": False,
            "premium_expires": None,
            "daily_limit_bytes": config.FREE_DAILY_LIMIT
        }}
    )

def get_db_statistics():
    """Returns a dictionary with database statistics."""
    total_users = users.count_documents({})
    premium_users = users.count_documents({"is_premium": True})

    # To get total usage, we need to aggregate the daily_usage field
    pipeline = [
        {"$group": {"_id": None, "total_usage": {"$sum": "$daily_usage"}}}
    ]
    result = list(users.aggregate(pipeline))
    total_daily_usage = result[0]['total_usage'] if result else 0

    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "total_daily_usage_bytes": total_daily_usage,
    }

def create_pending_payment(authority: str, user_id: int, plan: str, amount: int):
    """Stores a pending payment authority from Zarinpal."""
    pending_payments.insert_one({
        "authority": authority,
        "user_id": user_id,
        "plan": plan,
        "amount": amount,
        "created_at": datetime.utcnow()
    })

def get_and_delete_pending_payment(authority: str):
    """Retrieves and deletes a pending payment, ensuring it's used only once."""
    return pending_payments.find_one_and_delete({"authority": authority})
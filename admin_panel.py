# admin_panel.py
from telegram import Update
from telegram.ext import ContextTypes
import config
from database import users

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    total_users = users.count_documents({})
    premium_users = users.count_documents({"is_premium": True})
    active_subs = users.count_documents({
        "is_premium": True,
        "premium_expires": {"$gt": datetime.utcnow()}
    })
    await update.message.reply_text(
        f"📊 آمار سیستم:\n"
        f"همه کاربران: {total_users}\n"
        f"کاربران پریمیوم: {premium_users}\n"
        f"اشتراک‌های فعال: {active_subs}"
    )
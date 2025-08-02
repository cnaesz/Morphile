# bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
import os
import logging
from database import get_user, update_daily_usage, set_premium
from downloader import download_file
from uploader import upload_and_get_link
import config

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("💎 ارتقا اکانت", web_app=WebAppInfo(url=config.WEB_APP_URL))]]
    await update.message.reply_text(
        f"سلام {user.first_name}!\n"
        "📌 لینک بفرست تا فایل بگیری.\n"
        "📎 فایل بفرست تا لینک بگیری.\n\n"
        "🔹 رایگان: 1 گیگ در روز\n"
        "💎 پریمیوم: 50 گیگ در ماه",
        reply_markup=keyboard
    )
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    text = update.message.text
    if text and text.startswith("http"):
        await handle_link(update, context, user)
    elif update.message.document or update.message.audio or update.message.video:
        await handle_file(update, context, user)
    else:
        await update.message.reply_text("لطفاً یک لینک یا فایل بفرستید.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    url = update.message.text.strip()
    await update.message.reply_text("📥 در حال دانلود فایل...")

    filepath, error = download_file(url)
    if error:
        await update.message.reply_text(f"❌ خطا: {error}")
        return

    file_size = os.path.getsize(filepath)
    new_usage = update_daily_usage(user_id, file_size)

    if not user["is_premium"] and new_usage > config.FREE_DAILY_LIMIT:
        await update.message.reply_text(
            "⚠️ به 1 گیگ رسیدی! برای استفاده بیشتر، ارتقا بده:\n/upgrade"
        )

    await update.message.reply_text("📤 در حال ارسال فایل به تلگرام...")
    try:
        with open(filepath, 'rb') as f:
            if filepath.lower().endswith(('.mp3', '.wav', '.flac')):
                await update.message.reply_audio(f)
            elif filepath.lower().endswith(('.mp4', '.mov', '.avi')):
                await update.message.reply_video(f)
            else:
                await update.message.reply_document(f)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال: {e}")
    finally:
        os.remove(filepath)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    file_obj = None
    if update.message.document:
        file_obj = update.message.document
    elif update.message.audio:
        file_obj = update.message.audio
    elif update.message.video:
        file_obj = update.message.video

    if not file_obj:
        return

    file_size = file_obj.file_size
    if file_size > 2 * 1024 * 1024 * 1024:
        await update.message.reply_text("❌ فایل بیش از 2 گیگ نیست!")
        return

    new_usage = update_usage(user_id, file_size)
    if not user["is_premium"] and new_usage > config.PREMIUM_THRESHOLD:
        await update.message.reply_text(
            "⚠️ به 1 گیگ رسیدی! برای استفاده بیشتر، ارتقا بده:\n/upgrade"
        )

    await update.message.reply_text("📤 در حال آپلود...")
    file = await context.bot.get_file(file_obj.file_id)
    filename = file_obj.file_name or "uploaded_file"
    filepath = os.path.join(config.DOWNLOAD_DIR, filename)
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    await file.download_to_drive(filepath)

    link, error = upload_and_get_link(filepath)
    if error:
        await update.message.reply_text(f"❌ خطا: {error}")
    else:
        await update.message.reply_text(f"✅ لینک فایل:\n{link}")

    os.remove(filepath)

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💳 خرید اشتراک", url="https://your-payment-page.com")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "💎 ارتقای اشتراک:\n"
        "- دسترسی نامحدود\n"
        "- بدون محدودیت حجمی\n"
        "- پشتیبانی ویژه\n",
        reply_markup=reply_markup
    )

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.AUDIO | filters.VIDEO, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
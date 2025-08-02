# bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
import os
import logging
from database import get_user, update_usage
from downloader import download_file
from uploader import upload_and_get_link
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id)

    # Check for expired premium
    if db_user['is_premium'] and db_user['premium_expires'] and datetime.utcnow() > db_user['premium_expires']:
        # This is a fallback check. The main check should be in a cron job.
        from database import check_premium_status
        check_premium_status()
        db_user = get_user(user.id) # Re-fetch user

    keyboard = [[InlineKeyboardButton("💎 Upgrade Account", web_app=WebAppInfo(url=config.WEB_APP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    usage_gb = db_user['daily_usage'] / (1024**3)
    limit_gb = db_user['daily_limit_bytes'] / (1024**3)

    status = "Premium ✨" if db_user['is_premium'] else "Free"

    await update.message.reply_text(
        f"Hey {user.first_name}!\n\n"
        f"Status: {status}\n"
        f"Daily Usage: {usage_gb:.2f} GB / {limit_gb:.1f} GB\n\n"
        "➡️ Send a link to download a file.\n"
        "➡️ Send a file to get a direct link.",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if update.message.web_app_data:
        # Handle data from the Mini App (e.g., after a purchase)
        # This part needs to be implemented based on how the web app sends data.
        await update.message.reply_text("Thank you for your purchase!")
        return

    text = update.message.text
    if text and (text.startswith("http://") or text.startswith("https://")):
        await handle_link(update, context, user)
    elif update.message.document or update.message.audio or update.message.video:
        await handle_file(update, context, user)
    else:
        await update.message.reply_text("Please send a valid link or a file.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    user_id = user['user_id']
    url = update.message.text.strip()

    # Check usage before downloading
    if user['daily_usage'] >= user['daily_limit_bytes']:
        await update.message.reply_text(
            "⚠️ You have reached your daily usage limit. Upgrade to get more."
        )
        return

    await update.message.reply_text("📥 Downloading file...")
    filepath, error = download_file(url, max_size=user['daily_limit_bytes'])
    if error:
        await update.message.reply_text(f"❌ Error: {error}")
        return

    file_size = os.path.getsize(filepath)
    new_usage = update_usage(user_id, file_size)

    if new_usage > user['daily_limit_bytes']:
        os.remove(filepath) # Clean up the oversized file
        await update.message.reply_text(
            "⚠️ This download would exceed your daily limit. Please upgrade for more capacity."
        )
        # Revert usage update
        update_usage(user_id, -file_size)
        return

    await update.message.reply_text("📤 Uploading to Telegram...")
    try:
        with open(filepath, 'rb') as f:
            if filepath.lower().endswith(('.mp3', '.wav', '.flac')):
                await update.message.reply_audio(f)
            elif filepath.lower().endswith(('.mp4', '.mov', '.avi')):
                await update.message.reply_video(f)
            else:
                await update.message.reply_document(f)
    except Exception as e:
        await update.message.reply_text(f"❌ Upload Error: {e}")
    finally:
        os.remove(filepath)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    user_id = user['user_id']
    file_obj = update.message.document or update.message.audio or update.message.video
    if not file_obj:
        return

    if user['daily_usage'] + file_obj.file_size > user['daily_limit_bytes']:
        await update.message.reply_text(
            "⚠️ This upload would exceed your daily limit. Please upgrade for more capacity."
        )
        return

    if file_obj.file_size > 2 * 1024 * 1024 * 1024:
        await update.message.reply_text("❌ File size cannot exceed 2 GB.")
        return

    await update.message.reply_text("📤 Uploading to server...")
    try:
        file = await context.bot.get_file(file_obj.file_id)
        filename = file_obj.file_name or "uploaded_file"
        filepath = os.path.join(config.DOWNLOAD_DIR, f"{user_id}_{filename}")
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        await file.download_to_drive(filepath)

        # Update usage after successful download to server
        update_usage(user_id, file_obj.file_size)

        link, error = upload_and_get_link(filepath)
        if error:
            await update.message.reply_text(f"❌ Error creating link: {error}")
        else:
            await update.message.reply_text(f"✅ Your file link:\n{link}")

    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {e}")
    finally:
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.AUDIO | filters.VIDEO, handle_message))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
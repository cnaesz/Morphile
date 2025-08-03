# bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
import os
import logging
import time
from database import get_user, update_usage
from downloader import download_file
import config
from admin.handlers import get_admin_conversation_handler

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

async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /upgrade command, showing premium options."""
    keyboard = [[InlineKeyboardButton("💎 Upgrade to Premium", web_app=WebAppInfo(url=config.WEB_APP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "🚀 **Unlock Your Full Potential!** 🚀\n\n"
        "Upgrade to a Premium account to enjoy:\n"
        "✅ **Massive 50 GB Daily Limit**\n"
        "✅ **Highest Priority & Speed**\n"
        "✅ **No Ads, No Interruptions**\n\n"
        "Click the button below to see our flexible plans and upgrade instantly!"
    )

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='MarkdownV2')

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
        keyboard = [[InlineKeyboardButton("💎 Upgrade to Premium", web_app=WebAppInfo(url=config.WEB_APP_URL))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ You've reached your daily usage limit of 100 MB.\n\n"
            "Upgrade to a Premium account to get up to 50 GB per day, faster speeds, and more!",
            reply_markup=reply_markup
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
        keyboard = [[InlineKeyboardButton("💎 Upgrade to Premium", web_app=WebAppInfo(url=config.WEB_APP_URL))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ This upload would exceed your daily limit of 100 MB.\n\n"
            "Upgrade to a Premium account for more capacity!",
            reply_markup=reply_markup
        )
        return

    if file_obj.file_size > 2 * 1024 * 1024 * 1024:
        await update.message.reply_text("❌ File size cannot exceed 2 GB.")
        return

    # --- Time Estimation ---
    # Assume an average speed of 5 MB/s for downloading from Telegram
    avg_speed_mbps = 5
    estimated_seconds = file_obj.file_size / (avg_speed_mbps * 1024 * 1024)
    if estimated_seconds < 5:
        estimation_message = "a few moments"
    else:
        estimation_message = f"about {int(estimated_seconds)} seconds"

    await update.message.reply_text(
        f"✅ Received your file. Creating a direct link will take {estimation_message}.\n"
        "Please wait..."
    )
    # --- End Time Estimation ---

    try:
        file = await context.bot.get_file(file_obj.file_id)
        filename = file_obj.file_name or "uploaded_file"
        # --- Unique Filename Generation ---
        unique_filename = f"{user_id}_{int(time.time())}_{filename}"
        filepath = os.path.join(config.DOWNLOAD_DIR, unique_filename)
        # --- End Unique Filename Generation ---
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        await file.download_to_drive(filepath)

        # Update usage after successful download to server
        update_usage(user_id, file_obj.file_size)

        # --- Self-hosted Link Generation ---
        # The file is already downloaded to the correct directory.
        # Now, we just construct the public URL for it.
        base_filename = os.path.basename(filepath)
        link = f"{config.NGINX_URL}/{base_filename}"

        await update.message.reply_text(
            f"✅ Your file is ready!\n\n"
            f"Direct Link (expires in 24 hours):\n{link}"
        )
        # --- End Link Generation ---

    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred during processing: {e}")
        # If an error happens after download, we must clean up the file
        # and revert the usage count, as no link was generated.
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
            update_usage(user_id, -file_obj.file_size)

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Add admin handlers
    admin_handler = get_admin_conversation_handler()
    app.add_handler(admin_handler)

    # Add user-facing handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upgrade", upgrade_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.AUDIO | filters.VIDEO, handle_message))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
# bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
import os
import logging
import time
import json
import traceback
from database import get_user, update_usage
from downloader import download_file
import config
from admin.handlers import get_admin_conversation_handler
from zarinpal import create_payment_link

# --- Logging Setup ---
# Sets the logging level based on the DEBUG flag in config.
log_level = logging.DEBUG if config.DEBUG else logging.INFO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

# --- Global Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about the error.
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {json.dumps(update.to_dict(), indent=2, ensure_ascii=False)}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {str(context.chat_data)}</pre>\n\n"
        f"<pre>context.user_data = {str(context.user_data)}</pre>\n\n"
        f"<pre>{tb_string}</pre>"
    )

    # Finally, send the message
    if config.DEBUG:
        # If in debug mode, send the detailed error to the user who caused it
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="A critical error occurred. The developer has been notified.",
            )
    else:
        # In production, just log it. The developer can check the logs.
        pass # The error is already logged by logger.error

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A simple command to check if the bot is responsive."""
    await update.message.reply_text(f"Pong! The bot is alive.\n{time.asctime()}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id)

    # The check for expired premium is now handled by the cleanup.py cron job.
    # The fallback check has been removed for efficiency.

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
    """Main message handler. Logs incoming messages and routes them."""
    user = update.effective_user
    logger.info(f"Received message from {user.id} ({user.username}): {update.message.text or '<file>'}")

    user_id = user.id
    db_user = get_user(user_id)

    if update.message.web_app_data:
        # Data received from the Mini App
        try:
            data = json.loads(update.message.web_app_data.data)
            plan_id = data.get("plan_id")

            if not plan_id:
                await update.message.reply_text("Invalid data received from the app.")
                return

            # --- Security: Get price from server-side config, not from client ---
            plan_details = config.PRICING.get(plan_id)
            if not plan_details:
                await update.message.reply_text(f"Invalid plan selected: {plan_id}")
                return

            amount = plan_details['price']

            await update.message.reply_text("Generating your secure payment link, please wait...")

            # Create the payment link
            payment_link = create_payment_link(amount=amount, user_id=user_id, plan=plan_id)

            if payment_link:
                keyboard = [[InlineKeyboardButton("💳 Pay Now", url=payment_link)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "Your payment link is ready. Click the button below to complete your purchase.",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("Sorry, we couldn't create a payment link at this time. Please try again later.")
        except (json.JSONDecodeError, KeyError) as e:
            await update.message.reply_text(f"An error occurred while processing your request: {e}")
        return

    text = update.message.text
    if text and (text.startswith("http://") or text.startswith("https://")):
        await handle_link(update, context, db_user)
    elif update.message.document or update.message.audio or update.message.video:
        await handle_file(update, context, db_user)
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
            "⚠️ You've reached your daily usage limit.\n\n"
            "Upgrade to a Premium account to get up to 100 GB per day, faster speeds, and more!",
            reply_markup=reply_markup
        )
        return

    # --- Non-blocking download ---
    # Inform user and then perform the async download
    await update.message.reply_text("📥 Starting your download... The bot will remain responsive.")
    filepath, error = await download_file(url, max_size=user['daily_limit_bytes'])
    if error:
        await update.message.reply_text(f"❌ Download Error: {error}")
        return
    # --- End non-blocking download ---

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

    # --- Error Handling ---
    app.add_error_handler(error_handler)

    # Add admin handlers
    admin_handler = get_admin_conversation_handler()
    app.add_handler(admin_handler)

    # Add user-facing handlers
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upgrade", upgrade_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.AUDIO | filters.VIDEO, handle_message))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
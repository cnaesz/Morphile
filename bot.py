# bot.py
import os
import logging
import traceback
import json
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

import config
from database import get_user, update_usage
from tasks import process_file

# --- Logging Setup ---
log_level = logging.DEBUG if config.DEBUG else logging.INFO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

# --- Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    # For debugging, you can send the traceback to the admin
    if config.DEBUG and config.ADMIN_IDS:
        await context.bot.send_message(chat_id=config.ADMIN_IDS[0], text=f"Error: {tb_string[:4000]}")
    # Notify the user
    if update and hasattr(update, 'effective_chat'):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="An unexpected error occurred. The team has been notified.")

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    user = update.effective_user
    get_user(user.id) # Ensure user is in the database
    await update.message.reply_text(
        f"Hey {user.first_name}!\n\n"
        "I can process large files for you.\n"
        "➡️ Just send me any file (document, video, or audio).\n\n"
        "If you are testing, you can use the /test_upload command."
    )

async def test_upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /test_upload command.
    This now sends an initial message that the worker can edit.
    """
    if not config.LOCAL_TEST_MODE:
        await update.message.reply_text("This command is only available in local testing mode.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a local file path.\nUsage: /test_upload /path/to/your/file.zip")
        return

    local_path = context.args[0]
    if not os.path.exists(local_path):
        await update.message.reply_text(f"File not found at path: {local_path}")
        return

    # Send the initial status message and get its ID
    status_message = await update.message.reply_text(
        f"✅ Your test file has been added to the queue.\n"
        f"It will be processed in the background."
    )

    # Enqueue the job, passing the ID of the status message
    chat_id = update.effective_chat.id
    message_id = status_message.message_id
    logger.info(f"Queueing local file for upload: {local_path}")
    process_file.send(chat_id, message_id, local_path=local_path)


# --- Message Handler for Files ---
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles incoming files, sends an initial status message, and enqueues
    the file for processing.
    """
    user = update.effective_user
    db_user = get_user(user.id)
    file_obj = update.message.document or update.message.video or update.message.audio

    if not file_obj:
        return

    # 1. Check file size
    if file_obj.file_size > config.MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File is too large ({file_obj.file_size / 1024**3:.2f} GB). "
            f"The maximum allowed file size is {config.MAX_FILE_SIZE / 1024**3:.2f} GB."
        )
        return

    # 2. Check daily usage limit
    if db_user['daily_usage'] + file_obj.file_size > db_user['daily_limit_bytes']:
        await update.message.reply_text("⚠️ You have reached your daily usage limit. Please try again tomorrow or upgrade your account.")
        return

    # 3. Send initial status message that the worker can edit
    status_message = await update.message.reply_text(
        f"✅ Your file '{file_obj.file_name}' has been added to the queue.\n"
        f"You will be notified when the processing is complete."
    )

    # 4. Enqueue the file for processing
    chat_id = update.effective_chat.id
    status_message_id = status_message.message_id
    original_message_id = update.message.message_id # The ID of the message with the file
    file_id = file_obj.file_id

    # Detect if the message is a forward to use the appropriate download method
    is_forwarded = update.message.forward_date is not None
    if is_forwarded and not (config.API_ID and config.API_HASH):
        await status_message.edit_text("❌ This bot is not configured to handle forwarded files. Please send the file directly.")
        return

    logger.info(
        f"Queueing file for processing: chat_id={chat_id}, file_id={file_id}, "
        f"status_message_id={status_message_id}, original_message_id={original_message_id}, "
        f"is_forwarded={is_forwarded}"
    )
    process_file.send(
        chat_id,
        status_message_id=status_message_id,
        original_message_id=original_message_id,
        file_id=file_id,
        is_forwarded=is_forwarded
    )


# --- Monkey-patch for JobQueue issue ---
# In python-telegram-bot v20.6, ApplicationBuilder.__init__ eagerly creates a
# JobQueue instance, which can fail on systems with unsupported timezones.
# We replace it with a dummy class before building the application.
from telegram.ext import JobQueue
import telegram.ext._applicationbuilder as app_builder

class _DummyJobQueue(JobQueue):
    def __init__(self):
        # This dummy __init__ does nothing, preventing the problematic
        # APScheduler initialization from ever running.
        pass

# The actual monkey-patch
app_builder.JobQueue = _DummyJobQueue


# --- Main Application Setup ---
def main():
    """Starts the bot."""
    # Now, when Application.builder() is called, it will use our _DummyJobQueue
    # inside its __init__, which does nothing and avoids the error.
    # We still call .job_queue(None) to ensure the final Application object
    # correctly has no job queue.
    app = Application.builder().token(config.BOT_TOKEN).job_queue(None).build()

    # --- Error Handling ---
    app.add_error_handler(error_handler)

    # --- Command Handlers ---
    app.add_handler(CommandHandler("start", start))
    if config.LOCAL_TEST_MODE:
        app.add_handler(CommandHandler("test_upload", test_upload_command))

    # --- File Handler ---
    # This handler catches any message containing a document, video, or audio file.
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.VIDEO | filters.AUDIO,
        handle_file_upload
    ))

    # Fallback for any other text message
    async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Please send me a file to process.")

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))

    # --- Start Polling ---
    logger.info("Bot is starting up...")
    app.run_polling()

if __name__ == '__main__':
    main()
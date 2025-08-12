import dramatiq
from dramatiq.brokers.redis import RedisBroker
import telegram
import asyncio
import os
import logging
import time

import config

# --- Logging Setup ---
# Ensure logs from tasks are visible
log_level = logging.DEBUG if config.DEBUG else logging.INFO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)


# --- Dramatiq Setup ---
redis_broker = RedisBroker(host=config.REDIS_HOST, port=config.REDIS_PORT)
dramatiq.set_broker(redis_broker)


# --- Uploader Logic ---
def placeholder_uploader(filepath, chat_id):
    """
    Placeholder for the actual file upload logic to your hosting service.
    """
    logger.info(f"[{chat_id}] Starting upload of {filepath}...")
    # Simulate a long upload process
    time.sleep(10)
    filename = os.path.basename(filepath)
    # In a real scenario, this link would come from your hosting provider
    link = f"http://your-hosting-service.com/{filename}"
    logger.info(f"[{chat_id}] Finished upload. Link: {link}")
    return link


# --- Asynchronous Helper for Telegram Operations ---
async def download_and_notify(bot, chat_id, file_id, message_id):
    """
    Handles the asynchronous download from Telegram and notifications.
    """
    filepath = None
    try:
        # 1. Initial "processing" message
        await bot.send_message(chat_id, "File is now being processed...", reply_to_message_id=message_id)

        # 2. Download the file
        logger.info(f"[{chat_id}] Getting file info for file_id: {file_id}")
        file = await bot.get_file(file_id)

        # Generate a unique path for the download
        unique_filename = f"{chat_id}_{os.path.basename(file.file_path or 'unknown_file')}"
        filepath = os.path.join(config.DOWNLOAD_DIR, unique_filename)

        logger.info(f"[{chat_id}] Starting download to: {filepath}")
        await file.download_to_drive(filepath)
        logger.info(f"[{chat_id}] Download finished.")

        # 3. Upload to final destination
        direct_link = placeholder_uploader(filepath, chat_id)

        # 4. Notify user of success
        await bot.send_message(chat_id, f"✅ File processed successfully!\n\nYour direct link is: {direct_link}")

    except telegram.error.NetworkError as e:
        logger.warning(f"[{chat_id}] A network error occurred: {e}. This might be retried.")
        await bot.send_message(chat_id, f"⚠️ A network issue occurred: {e}. The bot will retry automatically.")
        # Re-raise the exception to trigger dramatiq's retry mechanism
        raise
    except Exception as e:
        logger.error(f"[{chat_id}] A critical error occurred in download_and_notify: {e}", exc_info=True)
        await bot.send_message(chat_id, f"❌ A critical error occurred while processing your file. The operation has been cancelled. Error: {e}")

    finally:
        # 5. Cleanup the downloaded file
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"[{chat_id}] Cleaned up temporary file: {filepath}")


@dramatiq.actor(max_retries=3, time_limit=3600_000) # 1 hour time limit
def process_file(chat_id, message_id, file_id=None, local_path=None):
    """
    Dramatiq actor that orchestrates file processing.
    """
    bot = telegram.Bot(token=config.BOT_TOKEN)
    logger.info(f"[{chat_id}] Worker picked up job. file_id={file_id}, local_path={local_path}")

    if file_id:
        # --- Production Mode ---
        # Run the async helper function to handle the Telegram download and notifications
        asyncio.run(download_and_notify(bot, chat_id, file_id, message_id))

    elif local_path and config.LOCAL_TEST_MODE:
        # --- Local Test Mode ---
        try:
            logger.info(f"[{chat_id}] Processing local file: {local_path}")
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local file not found: {local_path}")

            # Upload the local file
            direct_link = placeholder_uploader(local_path, chat_id)

            # Notify user of success
            asyncio.run(bot.send_message(chat_id, f"✅ LOCAL TEST: File processed successfully!\n\nLink: {direct_link}"))

        except Exception as e:
            logger.error(f"[{chat_id}] Error processing local file: {e}", exc_info=True)
            asyncio.run(bot.send_message(chat_id, f"❌ LOCAL TEST: An error occurred: {e}"))

    else:
        logger.warning(f"[{chat_id}] Job was called with invalid parameters.")

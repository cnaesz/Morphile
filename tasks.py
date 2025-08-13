import dramatiq
from dramatiq.brokers.redis import RedisBroker
import telegram
import asyncio
import os
import logging
import time
import shutil

import config

# --- Logging Setup ---
log_level = logging.DEBUG if config.DEBUG else logging.INFO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)


# --- Dramatiq Broker Setup ---
redis_broker = RedisBroker(host=config.REDIS_HOST, port=config.REDIS_PORT)
dramatiq.set_broker(redis_broker)


# --- File Handling Logic ---
def _move_and_get_link(source_path, chat_id, is_local_test=False):
    """
    Moves or copies the file to the public directory and returns the public link.
    """
    filename = os.path.basename(source_path)
    # Sanitize filename to prevent path traversal issues, though os.path.basename helps.
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ('.', '_', '-'))

    destination_path = os.path.join(config.PUBLIC_FILES_DIR, safe_filename)

    # To avoid deleting user's original file in local testing, we copy it.
    # In production (download from Telegram), we move it.
    if is_local_test:
        shutil.copy(source_path, destination_path)
        logger.info(f"[{chat_id}] Copied test file to public dir: {destination_path}")
    else:
        shutil.move(source_path, destination_path)
        logger.info(f"[{chat_id}] Moved file to public dir: {destination_path}")

    # Construct the final public URL
    public_link = f"{config.BASE_URL}/{safe_filename}"
    return public_link


# --- Asynchronous Telegram Operations ---
async def _run_processing_logic(bot_token, chat_id, message_id, file_id=None, local_path=None):
    """
    This async function contains all the logic that interacts with the Telegram API.
    """
    bot = telegram.Bot(token=bot_token)
    temp_filepath = None
    is_local_test = bool(local_path)

    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text="⏳ File processing started..."
        )

        if file_id:
            # Production Mode: Download from Telegram
            logger.info(f"[{chat_id}] Getting file info for file_id: {file_id}")
            tg_file = await bot.get_file(file_id)

            unique_filename = f"{chat_id}_{int(time.time())}_{os.path.basename(tg_file.file_path or 'unknown_file')}"
            temp_filepath = os.path.join(config.DOWNLOAD_DIR, unique_filename)

            logger.info(f"[{chat_id}] Downloading to: {temp_filepath}")
            await tg_file.download_to_drive(temp_filepath)
            logger.info(f"[{chat_id}] Download finished.")

            filepath_to_process = temp_filepath

        elif local_path and config.LOCAL_TEST_MODE:
            # Local Test Mode: Use local file path
            logger.info(f"[{chat_id}] Using local file: {local_path}")
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local test file not found: {local_path}")
            filepath_to_process = local_path

        else:
            raise ValueError("Task called without file_id or a valid local_path.")

        # Move file to public dir and get the link
        direct_link = _move_and_get_link(filepath_to_process, chat_id, is_local_test)

        # Notify User of Success
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"✅ File processed successfully!\n\nYour direct link is:\n{direct_link}",
            disable_web_page_preview=True
        )

    except telegram.error.NetworkError as e:
        logger.warning(f"[{chat_id}] A network error occurred: {e}. Dramatiq will retry.")
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"⚠️ A network issue occurred: {e}. The bot will retry automatically."
        )
        raise

    except Exception as e:
        logger.error(f"[{chat_id}] A critical error occurred in processing task: {e}", exc_info=True)
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=f"❌ A critical error occurred.\n\n`Error: {e}`"
            )
        except Exception as notify_error:
            logger.error(f"[{chat_id}] Failed to notify user of the error: {notify_error}")

    finally:
        # Cleanup the temporary downloaded file (if it exists)
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            logger.info(f"[{chat_id}] Cleaned up temporary file: {temp_filepath}")


# --- Dramatiq Actor Definition ---
@dramatiq.actor(max_retries=3, time_limit=3600_000)
def process_file(chat_id, message_id, file_id=None, local_path=None):
    """
    Synchronous Dramatiq actor that runs the async processing logic.
    """
    logger.info(f"Worker picked up job for chat_id={chat_id}, file_id={file_id}")

    asyncio.run(_run_processing_logic(
        bot_token=config.BOT_TOKEN,
        chat_id=chat_id, message_id=message_id,
        file_id=file_id, local_path=local_path
    ))

    logger.info(f"Worker finished job for chat_id={chat_id}")

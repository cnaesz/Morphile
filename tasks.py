import dramatiq
from dramatiq.brokers.redis import RedisBroker
from telethon import TelegramClient
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
    """Moves or copies the file to the public directory and returns the public link."""
    filename = os.path.basename(source_path)
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ('.', '_', '-'))
    destination_path = os.path.join(config.PUBLIC_FILES_DIR, safe_filename)

    if is_local_test:
        shutil.copy(source_path, destination_path)
        logger.info(f"[{chat_id}] Copied test file to public dir: {destination_path}")
    else:
        # For Telethon downloads, the file is already in its final-named temp location.
        # For Bot API, it's a generic name. In both cases, we move it.
        shutil.move(source_path, destination_path)
        logger.info(f"[{chat_id}] Moved file to public dir: {destination_path}")

    public_link = f"{config.BASE_URL}/{safe_filename}"
    return public_link


# --- Asynchronous Download Logic ---
async def _download_with_bot_api(bot, file_id, chat_id):
    """Downloads a file using the python-telegram-bot library (for direct uploads)."""
    logger.info(f"[{chat_id}] Downloading via Bot API for file_id: {file_id}")
    tg_file = await bot.get_file(file_id)

    unique_filename = f"{chat_id}_{int(time.time())}_{os.path.basename(tg_file.file_path or 'unknown_file')}"
    temp_filepath = os.path.join(config.DOWNLOAD_DIR, unique_filename)

    logger.info(f"[{chat_id}] Bot API downloading to: {temp_filepath}")
    await tg_file.download_to_drive(temp_filepath)
    logger.info(f"[{chat_id}] Bot API download finished.")
    return temp_filepath

async def _download_with_telethon(chat_id, original_message_id):
    """Downloads a forwarded file using the Telethon (userbot) library."""
    logger.info(f"[{chat_id}] Downloading via Telethon for message_id: {original_message_id}")

    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    temp_filepath = None
    try:
        await client.connect()
        logger.info(f"[{chat_id}] Telethon client connected.")

        # Get the message object using its ID in the bot's chat
        message = await client.get_messages(chat_id, ids=original_message_id)
        if not message or not message.media:
            raise ValueError("Could not find a message with media to download.")

        # Define a path for the downloaded file in the temp directory
        # The filename from Telethon is usually reliable.
        filename = message.file.name if message.file and message.file.name else f"telethon_{chat_id}_{original_message_id}.dat"
        temp_filepath = os.path.join(config.DOWNLOAD_DIR, filename)

        # Download the media from the message
        logger.info(f"[{chat_id}] Telethon downloading to: {temp_filepath}")
        await client.download_media(message, file=temp_filepath)
        logger.info(f"[{chat_id}] Telethon download finished.")
        return temp_filepath
    finally:
        if client.is_connected():
            await client.disconnect()
            logger.info(f"[{chat_id}] Telethon client disconnected.")


# --- Main Processing Logic ---
async def _run_processing_logic(bot_token, chat_id, status_message_id, original_message_id, file_id=None, local_path=None, is_forwarded=False):
    """This async function contains all the logic that interacts with the Telegram API."""
    bot = telegram.Bot(token=bot_token)
    temp_filepath = None
    is_local_test = bool(local_path)

    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=status_message_id, text="⏳ File processing started...")

        if is_forwarded:
            temp_filepath = await _download_with_telethon(chat_id, original_message_id)
        elif file_id:
            temp_filepath = await _download_with_bot_api(bot, file_id, chat_id)
        elif local_path and config.LOCAL_TEST_MODE:
            logger.info(f"[{chat_id}] Using local file: {local_path}")
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local test file not found: {local_path}")
            temp_filepath = local_path
        else:
            raise ValueError("Task called with invalid parameters.")

        direct_link = _move_and_get_link(temp_filepath, chat_id, is_local_test)

        await bot.edit_message_text(
            chat_id=chat_id, message_id=status_message_id,
            text=f"✅ File processed successfully!\n\nYour direct link is:\n{direct_link}",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"[{chat_id}] A critical error occurred in processing task: {e}", exc_info=True)
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=status_message_id,
                text=f"❌ An error occurred: {e}"
            )
        except Exception as notify_error:
            logger.error(f"[{chat_id}] Failed to notify user of the error: {notify_error}")

    finally:
        # Cleanup temp file if it's not a local test file and was actually downloaded
        if not is_local_test and temp_filepath and os.path.exists(temp_filepath):
            if file_id or is_forwarded:
                 os.remove(temp_filepath)
                 logger.info(f"[{chat_id}] Cleaned up temporary file: {temp_filepath}")

# --- Dramatiq Actor Definition ---
@dramatiq.actor(max_retries=3, time_limit=7200_000) # 2-hour time limit
def process_file(chat_id, status_message_id, original_message_id, file_id=None, local_path=None, is_forwarded=False):
    """Synchronous Dramatiq actor that runs the async processing logic."""
    logger.info(f"Worker picked up job for chat_id={chat_id}, is_forwarded={is_forwarded}")

    asyncio.run(_run_processing_logic(
        bot_token=config.BOT_TOKEN,
        chat_id=chat_id, status_message_id=status_message_id,
        original_message_id=original_message_id,
        file_id=file_id, local_path=local_path, is_forwarded=is_forwarded
    ))

    logger.info(f"Worker finished job for chat_id={chat_id}")

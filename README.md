# Morphile - High-Performance File Hosting Bot

This project provides a Telegram bot designed to handle large file uploads (up to 2GB) from users, process them, and return a direct download link.

It uses a robust, scalable architecture with a background job queue (Dramatiq and Redis) to handle high concurrency and ensure the main bot remains responsive at all times.

## Architecture Overview

1.  **The Bot (`bot.py`)**: The main process that interacts with the Telegram API. It handles user messages, performs initial checks, and enqueues jobs for processing.
2.  **The Job Queue (Redis + Dramatiq)**: A message broker that holds a queue of file processing jobs, allowing the bot to instantly offload heavy tasks.
3.  **The Worker (`tasks.py`)**: One or more separate processes that listen for jobs. Each worker downloads the file from Telegram, moves it to a public directory, and notifies the user with a download link.
4.  **The File Server (`local_server.py` / Nginx)**: A web server that makes the files in the public directory accessible via a URL.

## Local Development Setup

This guide provides step-by-step instructions for running the bot on your local machine.

### Prerequisites

- Python 3.10+
- Redis
- MongoDB

You can run Redis and MongoDB easily using Docker:
```bash
docker run --name some-redis -d -p 6379:6379 redis
docker run --name some-mongo -d -p 27017:27017 mongo
```

### Step 1: Get the Code & Install Dependencies

```bash
git clone https://github.com/cnaesz/Morphile.git
cd Morphile
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Your Environment

1.  Rename `.env.example` to `.env`.
2.  Open the `.env` file and fill in your `BOT_TOKEN` and `ADMIN_IDS`.
3.  For local testing, the default `BASE_URL="http://localhost:8080"` is recommended. Ensure the `LOCAL_SERVER_PORT` matches.

### Step 3: Run the Full System

To run the bot locally, you need to start **three separate processes** in three different terminal tabs (with the virtual environment activated in each).

**Terminal 1: Start the Dramatiq Workers**
```bash
# Start the background workers
dramatiq tasks
```
This process executes the long-running file download and move operations.

**Terminal 2: Start the Local File Server**
```bash
# Serve files from the public directory
python3 local_server.py
```
This process makes the final files available at `http://localhost:8080`.

**Terminal 3: Start the Bot**
```bash
# Run the main bot process
python3 bot.py
```
This process listens for new messages from users.

Your bot is now fully operational for local testing!

## Testing the Full Flow

1.  Start the three processes as described above.
2.  Open Telegram and send a file to your bot.
3.  The bot will reply, and the message will be updated as the file is processed by the worker.
4.  The final message will contain a direct download link (e.g., `http://localhost:8080/your_file.mp3`).
5.  Click the link in your browser to download the file, which is being served by your `local_server.py`.

### Using Local Test Mode

For even faster testing without needing to upload files to Telegram:
1.  In your `.env` file, set `LOCAL_TEST_MODE="true"`.
2.  Restart the bot process (`python3 bot.py`).
3.  Use the command `/test_upload /path/to/a/large/file.zip` in your chat with the bot. The worker will copy this file to the public directory and return a link.

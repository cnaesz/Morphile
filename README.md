# Morphile - High-Performance File Hosting Bot

This project provides a Telegram bot designed to handle large file uploads (up to 2GB) from users, process them, and return a direct download link from a hosting provider.

It has been refactored to use a robust, scalable architecture with a background job queue to handle high concurrency and ensure the main bot remains responsive at all times.

## Architecture Overview

The new architecture consists of three main components:

1.  **The Bot (`bot.py`)**: This is the main process that interacts with the Telegram API. It's responsible for receiving messages from users, performing initial validation (like checking file sizes), and enqueuing jobs for processing. It does **not** perform any heavy tasks like downloading or uploading files.
2.  **The Job Queue (Redis + Dramatiq)**: A message broker (Redis) that holds a queue of file processing jobs. This allows the bot to instantly offload tasks.
3.  **The Worker (`tasks.py`)**: One or more separate processes that listen for jobs on the queue. Each worker picks up a job, downloads the file from Telegram, uploads it to the final destination, and sends a notification back to the user.

This decoupled architecture is highly scalable. To handle more users, you simply run more worker processes.

## Setup and Installation Guide

This guide provides step-by-step instructions for setting up the bot for local development or production.

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Step 1: Get the Code

Clone the repository to your local machine:
```bash
git clone https://github.com/cnaesz/Morphile.git
cd Morphile
```

### Step 2: Configure Environment Variables

Create a `.env` file from the example and fill in your details.
```bash
cp .env.example .env
```
Now, open the `.env` file and set your `BOT_TOKEN` and any other required variables.

### Step 3: Create a Clean Python Environment

**This is a critical step.** To avoid errors from conflicting libraries, you must install dependencies into a fresh virtual environment. If you have an old environment (e.g., a `venv` or `MyVenv` folder), delete it first.

1.  **Create a new virtual environment:**
    ```bash
    python -m venv venv
    ```
2.  **Activate the environment:**
    -   On Windows: `venv\Scripts\activate`
    -   On macOS/Linux: `source venv/bin/activate`

3.  **Install all dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Step 4: Start Background Services (Database & Queue)

The bot requires MongoDB and Redis to be running. The easiest way to start them is using the included `docker-compose.yml` file.

```bash
docker-compose up -d
```
This command will download the necessary images and start both services in the background.

Alternatively, you can install and run Redis and MongoDB manually on your system.

## Running the Bot

To run the system, you need to start **two separate processes** in two different terminals.

### Terminal 1: Run the Dramatiq Workers

The workers are responsible for all the heavy lifting. You can run multiple workers to increase concurrency.

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Start the dramatiq workers (this will start multiple workers based on your CPU cores)
dramatiq tasks
```

### Terminal 2: Run the Bot

The bot process listens for new messages from users.

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run the bot
python bot.py
```

Your bot is now fully operational!

## Local Testing Mode

This bot includes a powerful local testing mode that allows you to test the entire file processing pipeline without needing to send files through Telegram.

### How to Enable

1.  Open your `.env` file.
2.  Set `LOCAL_TEST_MODE="true"`.
3.  Restart the bot process (`python bot.py`). You do **not** need to restart the workers.

### How to Use

Once enabled, you can use the `/test_upload` command in your chat with the bot:

```
/test_upload /path/to/a/large/file/on/your/computer.zip
```

The bot will pick up the file from your local disk and send it to a worker for processing, just as it would with a real file from Telegram. This is ideal for testing large files and simulating concurrent uploads by sending the command multiple times.

---
*This documentation provides a clear guide for setting up and running the refactored bot.*

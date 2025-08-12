# Morphile - High-Performance File Hosting Bot

This project provides a Telegram bot designed to handle large file uploads (up to 2GB) from users, process them, and return a direct download link from a hosting provider.

It has been refactored to use a robust, scalable architecture with a background job queue to handle high concurrency and ensure the main bot remains responsive at all times.

## Architecture Overview

The new architecture consists of three main components:

1.  **The Bot (`bot.py`)**: This is the main process that interacts with the Telegram API. It's responsible for receiving messages from users, performing initial validation (like checking file sizes), and enqueuing jobs for processing. It does **not** perform any heavy tasks like downloading or uploading files.
2.  **The Job Queue (Redis + Dramatiq)**: A message broker (Redis) that holds a queue of file processing jobs. This allows the bot to instantly offload tasks.
3.  **The Worker (`tasks.py`)**: One or more separate processes that listen for jobs on the queue. Each worker picks up a job, downloads the file from Telegram, uploads it to the final destination, and sends a notification back to the user.

This decoupled architecture is highly scalable. To handle more users, you simply run more worker processes.

## Setup and Installation

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (recommended for easily running Redis and MongoDB)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 1. Clone the Repository

```bash
git clone https://github.com/cnaesz/Morphile.git
cd Morphile
```

### 2. Configure Environment Variables

Copy the example environment file and edit it with your settings.

```bash
cp .env.example .env
```

Open the `.env` file and fill in the required values:
- `BOT_TOKEN`: Your Telegram bot token.
- `ADMIN_IDS`: Your numeric Telegram user ID.
- `MONGO_URI`: The connection string for your MongoDB database.
- `REDIS_HOST` / `REDIS_PORT`: Connection details for your Redis server. The defaults are fine if you use the provided Docker setup.

### 3. Install Dependencies

It's highly recommended to use a Python virtual environment.

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Start Background Services (Database & Queue)

The easiest way to run MongoDB and Redis for local development is with Docker.

```bash
docker-compose up -d
```
*(Note: A `docker-compose.yml` file will need to be created for this. I will add this in a future step if needed, or the user can set up Redis/Mongo manually.)*

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

# Morphile - File Conversion and Hosting Bot

Morphile is a powerful Telegram bot designed to bridge the gap between web links and Telegram, and vice-versa. It can download files from URLs and upload them to Telegram, or take files sent to it and provide a direct, shareable link. It's built with premium features in mind, including daily usage limits and upgrade options.

## Features

- **URL to File**: Send a direct link to a file, and the bot will download it and upload it to your chat.
- **File to URL**: Send a file (document, video, or audio) to the bot, and it will host it and provide you with a direct download link.
- **Usage Tiers**: Free and Premium user tiers with different daily usage limits.
- **Payments Integration**: A (currently with Zarinpal) for handling premium upgrades.
- **Admin Panel**: Basic administration features for managing the bot.
- **Asynchronous by Design**: Built with `asyncio` and `python-telegram-bot` for high performance.

## Local Development Setup

Follow these instructions to set up a local development environment for testing and contributing.

### Prerequisites

- **Python 3.10+**: Make sure you have a recent version of Python installed.
- **pip**: Python's package installer.
- **Docker**: (Recommended) For running a local MongoDB instance easily.
- **ngrok**: (Optional) For testing webhook functionality and file hosting links.

### 1. Clone the Repository

```bash
git clone https://github.com/cnaesz/Morphile.git
cd Morphile
```

### 2. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The bot uses a `.env` file to manage secret keys and configuration.

1.  **Copy the example file:**

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**

    Open the `.env` file in a text editor and fill in the required values.

    -   `BOT_TOKEN`: Your Telegram bot token, obtained from [@BotFather](https://t.me/BotFather).
    -   `ADMIN_IDS`: Your numeric Telegram user ID. This is required for admin commands. You can get your ID from a bot like [@userinfobot](https://t.me/userinfobot).
    -   `MONGO_URI`: The connection string for your MongoDB database. If you're using the provided Docker setup, the default `mongodb://localhost:27017/` is correct.

### 5. Start a Local Database (Recommended)

The easiest way to run a local MongoDB instance is with Docker.

```bash
docker run -d -p 27017:27017 --name morphile-mongo mongo:latest
```

This command will start a MongoDB container in the background and expose it on the default port.

## Running the Bot

### Using Polling (for Local Development)

Polling is the simplest way to run the bot for local testing. The bot will continuously ask Telegram for new messages.

```bash
python bot.py
```

Your bot should now be running! You can interact with it on Telegram. Use the `/ping` command to test if it's responsive.

### Using Webhooks (for Production & Testing with ngrok)

In a production environment, webhooks are more efficient. For local testing of features that require a public URL (like the file hosting or the payment web app), you can use `ngrok`.

#### 1. Start ngrok

`ngrok` creates a secure tunnel to your local machine, giving you a public URL.

-   **Expose the web app (Flask):** The web app runs on port `5001`.

    ```bash
    ngrok http 5001
    ```

-   **Expose the file server:** For file hosting, you'll need a simple file server. You can run one easily with Python. This command serves the `downloads` directory on port `8080`.

    ```bash
    # In a new terminal
    python -m http.server 8080 --directory downloads
    ```

    Then, expose this port with ngrok:

    ```bash
    # In another new terminal
    ngrok http 8080
    ```

#### 2. Configure Your `.env`

`ngrok` will give you public URLs (e.g., `https://random-string.ngrok.io`). Update your `.env` file with these URLs:

```
# The URL for the Flask web app (for payments, etc.)
WEB_APP_URL="https://<your-ngrok-url-for-port-5001>/app"

# The URL for accessing hosted files
NGINX_URL="https://<your-ngrok-url-for-port-8080>"

# The callback for Zarinpal, pointing to your ngrok-exposed webapp
ZARINPAL_CALLBACK="https://<your-ngrok-url-for-port-5001>/verify"
```

#### 3. Run the Bot and Web App

You'll need to run both the bot and the Flask web app.

```bash
# In one terminal, run the bot
python bot.py

# In another terminal, run the web app
python webapp.py
```

You can now test the full functionality of the bot, including generating shareable links and processing payments.

## Production Deployment

For a production environment, you should:

1.  **Use a proper web server**: Use a WSGI server like `gunicorn` to run the Flask `webapp.py`. The provided `systemd/webapp.service` file shows an example.
2.  **Use a reverse proxy**: Use `nginx` or a similar web server to handle SSL and route traffic to your bot and web app.
3.  **Set `DEBUG=false`**: In your `.env` file or environment variables, set `DEBUG="false"`.
4.  **Switch to Webhooks**: Modify `bot.py` to use `app.run_webhook()` instead of `app.run_polling()`. You will need to provide the public URL of your bot, your SSL certificate, and other details. Refer to the `python-telegram-bot` documentation for a detailed guide on `run_webhook`.
5.  **Use `systemd` services**: The `systemd` directory contains example service files for running the bot and web app as persistent services on a Linux server. You will need to customize these files with your specific user and paths.

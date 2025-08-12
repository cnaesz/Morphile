#!/bin/bash

# This script provides a convenient way to run the bot for local development.
# It sets the DEBUG environment variable to "true" so that you get
# detailed error messages and other debugging information.

# Make sure you have a .env file with your BOT_TOKEN.
if [ ! -f .env ]; then
    echo "Error: .env file not found."
    echo "Please create one based on .env.example and add your BOT_TOKEN."
    exit 1
fi

echo "Starting bot in local development mode (DEBUG=true)..."

# Set the DEBUG variable and run the bot
export DEBUG="true"
python3 bot.py

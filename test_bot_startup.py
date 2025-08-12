import os
import logging
from telegram.ext import Application
import config

# --- Logging Setup ---
# This is just to prevent warnings from the library
logging.basicConfig()

print("Attempting to build the Telegram Application object...")

try:
    # This is the line that was causing the crash for the user.
    app = Application.builder().token(config.BOT_TOKEN).build()
    print("\n✅ SUCCESS: Application object built successfully!")
    print("The dependency issue appears to be resolved.")

except Exception as e:
    print(f"\n❌ FAILURE: An error occurred while building the Application object.")
    print(f"Error: {e}")
    # Print the full traceback
    import traceback
    traceback.print_exc()

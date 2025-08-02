# cleanup.py
import os
import time
from datetime import datetime
import config
from database import check_premium_status, reset_all_daily_usage

def cleanup_old_files():
    """Removes files from the download directory that are older than 24 hours."""
    now = time.time()
    cutoff = now - (24 * 3600)  # 24 hours in seconds
    cleaned_count = 0
    folder = config.DOWNLOAD_DIR

    if not os.path.exists(folder):
        print(f"📁 Download directory not found at {folder}. Skipping file cleanup.")
        return

    print("--- Starting File Cleanup ---")
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            try:
                if os.path.getctime(filepath) < cutoff:
                    os.remove(filepath)
                    print(f"🧹 Deleted old file: {filename}")
                    cleaned_count += 1
            except Exception as e:
                print(f"❌ Error deleting {filename}: {e}")
    print(f"✅ Cleaned {cleaned_count} old files.")

def perform_database_cleanup():
    """Deactivates expired premium accounts and resets daily usage for all users."""
    print("\n--- Starting Database Cleanup ---")

    # Deactivate expired premium users
    expired_count = check_premium_status()
    print(f"🔄 Deactivated {expired_count} expired premium accounts.")

    # Reset daily usage for all users
    reset_count = reset_all_daily_usage()
    print(f"📊 Reset daily usage for {reset_count} users.")

    print("✅ Database cleanup complete.")

def main():
    """Main function to run all cleanup tasks."""
    print(f"🚀 Starting cleanup job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    cleanup_old_files()
    perform_database_cleanup()
    print(f"🏁 Cleanup job finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
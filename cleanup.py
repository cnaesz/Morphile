# cleanup.py
import sys
import os
from datetime import datetime

# Add the project root to the Python path to allow running this script standalone
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import reset_all_daily_usage, check_premium_status
except ImportError:
    print("Error: Could not import database module. Make sure this script is in the project root.")
    sys.exit(1)

def perform_cleanup():
    """
    Runs the daily cleanup tasks for the database.
    1. Resets daily usage for all users.
    2. Checks for and revokes expired premium subscriptions.
    """
    print(f"--- Starting daily cleanup at {datetime.utcnow()} UTC ---")

    # Reset daily usage for all users
    try:
        modified_count = reset_all_daily_usage()
        print(f"✅ Successfully reset daily usage for {modified_count} users.")
    except Exception as e:
        print(f"❌ Error resetting daily usage: {e}")

    # Check for expired premium plans
    try:
        expired_count = check_premium_status()
        if expired_count > 0:
            print(f"✅ Successfully revoked {expired_count} expired premium subscriptions.")
        else:
            print("✅ No expired premium subscriptions found.")
    except Exception as e:
        print(f"❌ Error checking premium status: {e}")

    print("--- Daily cleanup finished ---")

if __name__ == "__main__":
    perform_cleanup()

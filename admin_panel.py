import argparse
import asyncio
from telegram import Bot
from database import get_user, set_premium, get_all_users
import config

def list_users():
    """Prints a list of all users."""
    print("--- User List ---")
    users = get_all_users()
    for user in users:
        status = "Premium" if user.get('is_premium') else "Free"
        print(
            f"ID: {user['user_id']} | Status: {status} | "
            f"Usage: {user.get('daily_usage', 0) / (1024**3):.2f} GB | "
            f"Expires: {user.get('premium_expires', 'N/A')}"
        )
    print("-----------------")

def user_info(user_id):
    """Prints detailed information for a specific user."""
    user = get_user(user_id)
    if not user:
        print(f"User with ID {user_id} not found.")
        return

    print(f"--- Info for User ID: {user_id} ---")
    for key, value in user.items():
        if key == 'daily_limit_bytes':
            print(f"  {key}: {value} ({value / (1024**3):.1f} GB)")
        elif key == 'daily_usage':
            print(f"  {key}: {value} ({value / (1024**3):.2f} GB)")
        else:
            print(f"  {key}: {value}")
    print("-----------------------------")

def grant_premium(user_id, plan_name):
    """Grants a premium plan to a user."""
    if plan_name not in config.PRICING:
        print(f"Error: Plan '{plan_name}' not found in config.py.")
        print(f"Available plans: {', '.join(config.PRICING.keys())}")
        return

    plan = config.PRICING[plan_name]
    duration = plan['duration_days']
    limit = plan['limit']

    set_premium(user_id, duration, limit)
    print(f"✅ Successfully granted premium plan '{plan_name}' to user {user_id} for {duration} days.")
    user_info(user_id)

def revoke_premium(user_id):
    """Revokes premium status from a user."""
    # Setting premium with 0 duration and free limit effectively revokes it.
    set_premium(user_id, 0, config.FREE_DAILY_LIMIT)
    # We also need to manually set is_premium to False
    from database import users
    users.update_one({"user_id": user_id}, {"$set": {"is_premium": False, "premium_expires": None}})

    print(f"✅ Successfully revoked premium status from user {user_id}.")
    user_info(user_id)

async def broadcast_message(message):
    """Sends a message to all users of the bot."""
    print(f"--- Broadcasting Message ---")
    print(f"Message: {message}")

    users = get_all_users()
    user_ids = [user['user_id'] for user in users]

    if not user_ids:
        print("No users found to broadcast to.")
        return

    confirm = input(f"This will send a message to {len(user_ids)} users. Are you sure? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Broadcast cancelled.")
        return

    bot = Bot(token=config.BOT_TOKEN)
    sent_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
            sent_count += 1
            print(f"Sent to {user_id}")
        except Exception as e:
            failed_count += 1
            print(f"Failed to send to {user_id}: {e}")

    print("--------------------------")
    print(f"✅ Broadcast complete. Sent: {sent_count}, Failed: {failed_count}.")


def main():
    parser = argparse.ArgumentParser(description="Admin Panel for the Telegram Bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List users
    subparsers.add_parser("list-users", help="List all users.")

    # User info
    info_parser = subparsers.add_parser("user-info", help="Get detailed info for a user.")
    info_parser.add_argument("user_id", type=int, help="The user's Telegram ID.")

    # Grant premium
    grant_parser = subparsers.add_parser("grant-premium", help="Grant a premium plan to a user.")
    grant_parser.add_argument("user_id", type=int, help="The user's Telegram ID.")
    grant_parser.add_argument("plan_name", type=str, help=f"The plan name from config.py (e.g., '1_month_50gb').")

    # Revoke premium
    revoke_parser = subparsers.add_parser("revoke-premium", help="Revoke premium status from a user.")
    revoke_parser.add_argument("user_id", type=int, help="The user's Telegram ID.")

    # Broadcast message
    broadcast_parser = subparsers.add_parser("broadcast", help="Send a message to all users.")
    broadcast_parser.add_argument("message", type=str, help="The message to send.")

    args = parser.parse_args()

    if args.command == "list-users":
        list_users()
    elif args.command == "user-info":
        user_info(args.user_id)
    elif args.command == "grant-premium":
        grant_premium(args.user_id, args.plan_name)
    elif args.command == "revoke-premium":
        revoke_premium(args.user_id)
    elif args.command == "broadcast":
        asyncio.run(broadcast_message(args.message))

if __name__ == "__main__":
    main()
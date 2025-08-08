# admin/handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from datetime import datetime
import config
from database import get_db_statistics, get_user, set_premium, revoke_premium

# --- States for Conversation ---
MAIN_MENU, USER_LOOKUP, MANAGE_PREMIUM_USER_ID, MANAGE_PREMIUM_ACTION = range(4)

def is_admin(user_id: int) -> bool:
    """Checks if a user is an admin."""
    return user_id in config.ADMIN_IDS

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the /admin command."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        # Silently ignore non-admins
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("🔍 User Lookup", callback_data="admin_user_lookup")],
        [InlineKeyboardButton("🎁 Grant/Revoke Premium", callback_data="admin_manage_premium")],
        [InlineKeyboardButton("Exit", callback_data="admin_exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("👑 *Admin Panel*\n\nWelcome! Please choose an option:", reply_markup=reply_markup, parse_mode='MarkdownV2')

    return MAIN_MENU

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shows bot statistics."""
    query = update.callback_query
    await query.answer()

    stats = get_db_statistics()
    usage_gb = stats['total_daily_usage_bytes'] / (1024**3)

    message = (
        "📊 *Bot Statistics*\n\n"
        f"Total Users: `{stats['total_users']}`\n"
        f"Premium Users: `{stats['premium_users']}`\n"
        f"Total Usage Today: `{usage_gb:.2f} GB`\n"
    )

    keyboard = [[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="admin_back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='MarkdownV2')
    return MAIN_MENU

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns to the main admin menu."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("🔍 User Lookup", callback_data="admin_user_lookup")],
        [InlineKeyboardButton("🎁 Grant/Revoke Premium", callback_data="admin_manage_premium")],
        [InlineKeyboardButton("Exit", callback_data="admin_exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("👑 *Admin Panel*\n\nWelcome! Please choose an option:", reply_markup=reply_markup, parse_mode='MarkdownV2')
    return MAIN_MENU


async def exit_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exits the admin panel."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ You have exited the admin panel.")
    return ConversationHandler.END

async def start_user_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the user lookup process."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔍 *User Lookup*\n\nPlease send me the Telegram User ID of the user you want to look up.",
        parse_mode='MarkdownV2'
    )
    return USER_LOOKUP

async def perform_user_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Performs the user lookup and shows the user's details."""
    try:
        user_id = int(update.message.text)
    except (ValueError, TypeError):
        await update.message.reply_text("Invalid ID. Please send a valid Telegram User ID (which is a number).")
        return USER_LOOKUP

    user_data = get_user(user_id)

    if not user_data or not user_data.get('created_at'): # Check if it's a real user vs a placeholder
        message = f"❌ No user found with the ID `{user_id}`."
    else:
        status = "Premium ✨" if user_data.get('is_premium') else "Free"
        usage_gb = user_data.get('daily_usage', 0) / (1024**3)
        limit_gb = user_data.get('daily_limit_bytes', 0) / (1024**3)
        expires = user_data.get('premium_expires', 'N/A')
        if isinstance(expires, datetime):
            expires = expires.strftime('%Y-%m-%d')

        message = (
            f"👤 *User Details for ID:* `{user_id}`\n\n"
            f"**Status:** {status}\n"
            f"**Daily Usage:** {usage_gb:.3f} GB / {limit_gb:.1f} GB\n"
            f"**Premium Expires:** {expires}\n"
            f"**Joined:** {user_data['created_at'].strftime('%Y-%m-%d')}"
        )

    keyboard = [[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="admin_back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='MarkdownV2')
    return MAIN_MENU

async def start_manage_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the process of managing a user's premium status."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎁 *Manage Premium*\n\nPlease send me the Telegram User ID to manage.",
        parse_mode='MarkdownV2'
    )
    return MANAGE_PREMIUM_USER_ID

async def prompt_premium_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shows the user's status and asks whether to grant or revoke premium."""
    try:
        user_id = int(update.message.text)
    except (ValueError, TypeError):
        await update.message.reply_text("Invalid ID. Please send a valid Telegram User ID.")
        return MANAGE_PREMIUM_USER_ID

    user_data = get_user(user_id)
    if not user_data or not user_data.get('created_at'):
        await update.message.reply_text(f"❌ No user found with the ID `{user_id}`.")
        return MANAGE_PREMIUM_USER_ID

    context.user_data['target_user_id'] = user_id
    status = "Premium ✨" if user_data.get('is_premium') else "Free"

    # --- Create a dynamic keyboard for all available plans ---
    keyboard = []
    for plan_id, details in config.PRICING.items():
        limit_gb = details['limit'] / (1024**3)
        text = f"✅ Grant {details['duration_days']}d, {limit_gb}GB"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"admin_grant_{plan_id}")])

    keyboard.append([InlineKeyboardButton("❌ Revoke Premium", callback_data="admin_revoke_premium")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="admin_back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Managing user `{user_id}`.\n"
        f"Current status: **{status}**.\n\n"
        "Choose an action:",
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )
    return MANAGE_PREMIUM_ACTION

async def perform_premium_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Grants or revokes premium based on the button pressed."""
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = context.user_data.get('target_user_id')

    if not user_id:
        await query.edit_message_text("Error: Target user ID not found. Please start over.")
        return await back_to_main_menu(update, context)

    if action.startswith("admin_grant_"):
        plan_name = action.replace("admin_grant_", "")
        plan = config.PRICING.get(plan_name)
        if plan:
            set_premium(user_id, plan['duration_days'], plan['limit'])
            await query.edit_message_text(f"✅ Successfully granted premium plan '{plan_name}' to user `{user_id}`.")
        else:
            await query.edit_message_text(f"❌ Error: Plan '{plan_name}' not found.")

    elif action == "admin_revoke_premium":
        revoke_premium(user_id)
        await query.edit_message_text(f"✅ Successfully revoked premium status from user `{user_id}`.")

    context.user_data.pop('target_user_id', None)
    return await back_to_main_menu(update, context)


# --- Conversation Handler Setup ---
def get_admin_conversation_handler() -> ConversationHandler:
    """Creates the conversation handler for the admin panel."""

    handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_command)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(show_statistics, pattern="^admin_stats$"),
                CallbackQueryHandler(start_user_lookup, pattern="^admin_user_lookup$"),
                CallbackQueryHandler(start_manage_premium, pattern="^admin_manage_premium$"),
                CallbackQueryHandler(back_to_main_menu, pattern="^admin_back_to_main$"),
                CallbackQueryHandler(exit_admin_panel, pattern="^admin_exit$"),
            ],
            USER_LOOKUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, perform_user_lookup)
            ],
            MANAGE_PREMIUM_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, prompt_premium_action)
            ],
            MANAGE_PREMIUM_ACTION: [
                CallbackQueryHandler(perform_premium_action, pattern="^admin_(grant_.+|revoke_premium)$"),
                CallbackQueryHandler(back_to_main_menu, pattern="^admin_back_to_main$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", exit_admin_panel)],
    )
    return handler

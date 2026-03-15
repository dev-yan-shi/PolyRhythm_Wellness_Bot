"""
Life Coach Telegram Bot — Entry point
"""
import logging

from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler,
)

from config import TELEGRAM_BOT_TOKEN
from database import init_db
from scheduler import setup_jobs

from handlers.commands import (
    start_command, help_command, weight_command,
    mealplan_command, dashboard_command, today_command,
    profile_command,
    # Onboarding conversation states + handlers
    ASK_NAME, ASK_FOOD_PREFS, ASK_ALLERGIES,
    handle_name, handle_food_prefs, handle_allergies,
)
from handlers.photo_handler import handle_photo
from handlers.message_handler import handle_message
from handlers.weekly_review import (
    review_command, handle_what_went_well,
    handle_what_was_hard, handle_additional, cancel_review,
    WHAT_WENT_WELL, WHAT_WAS_HARD, ADDITIONAL,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    # Validate config
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

    # Init DB
    init_db()
    logger.info("Database initialised.")

    # Build application (job-queue enabled by default)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Onboarding conversation (/start for new users) ────────────────────────
    onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_NAME:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ASK_FOOD_PREFS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food_prefs)],
            ASK_ALLERGIES:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_allergies)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    # ── Weekly review conversation ────────────────────────────────────────────
    weekly_review = ConversationHandler(
        entry_points=[CommandHandler("review", review_command)],
        states={
            WHAT_WENT_WELL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_what_went_well)],
            WHAT_WAS_HARD:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_what_was_hard)],
            ADDITIONAL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_additional)],
        },
        fallbacks=[CommandHandler("cancel", cancel_review)],
    )

    # ── Register handlers (order matters) ────────────────────────────────────
    app.add_handler(onboarding)
    app.add_handler(weekly_review)
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(CommandHandler("weight",    weight_command))
    app.add_handler(CommandHandler("mealplan",  mealplan_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("today",     today_command))
    app.add_handler(CommandHandler("profile",   profile_command))

    # Photo handler (food logging)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # General text (corrections, weight, AI chat) — must be last
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ── Scheduled jobs ────────────────────────────────────────────────────────
    setup_jobs(app.job_queue)

    # ── Start ─────────────────────────────────────────────────────────────────
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

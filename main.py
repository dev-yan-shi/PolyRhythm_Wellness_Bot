"""
PolyRhythm Wellness Bot — Entry point

Runs in two modes automatically:
  • WEBHOOK mode  — when HF_SPACE_URL env var is set (HuggingFace / cloud)
                    Telegram pushes updates to us via HTTP POST.
                    aiohttp serves both the webhook and a /health endpoint.
  • POLLING mode  — when HF_SPACE_URL is not set (local development)
                    Bot polls Telegram for updates the usual way.
"""
import asyncio
import logging
import os

from aiohttp import web
from telegram import Update
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


# ── Build & configure the PTB Application ────────────────────────────────────

def build_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_NAME:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ASK_FOOD_PREFS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food_prefs)],
            ASK_ALLERGIES:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_allergies)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    weekly_review = ConversationHandler(
        entry_points=[CommandHandler("review", review_command)],
        states={
            WHAT_WENT_WELL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_what_went_well)],
            WHAT_WAS_HARD:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_what_was_hard)],
            ADDITIONAL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_additional)],
        },
        fallbacks=[CommandHandler("cancel", cancel_review)],
    )

    app.add_handler(onboarding)
    app.add_handler(weekly_review)
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(CommandHandler("weight",    weight_command))
    app.add_handler(CommandHandler("mealplan",  mealplan_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("today",     today_command))
    app.add_handler(CommandHandler("profile",   profile_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    setup_jobs(app.job_queue)
    return app


# ── Webhook mode (HuggingFace / cloud) ───────────────────────────────────────

async def run_webhook(hf_space_url: str):
    """
    Starts an aiohttp server on port 7860 that:
      POST /webhook  → receives Telegram updates
      GET  /          → health check for UptimeRobot
      GET  /health    → same
    """
    ptb = build_app()
    webhook_url = f"{hf_space_url.rstrip('/')}/webhook"

    await ptb.initialize()
    await ptb.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    await ptb.start()
    logger.info(f"Webhook registered: {webhook_url}")

    # ── aiohttp handlers ─────────────────────────────────────────────────────
    async def telegram_webhook(request: web.Request) -> web.Response:
        try:
            data   = await request.json()
            update = Update.de_json(data, ptb.bot)
            await ptb.update_queue.put(update)
        except Exception as exc:
            logger.error(f"Webhook processing error: {exc}")
        return web.Response(text="OK")

    async def health(request: web.Request) -> web.Response:
        return web.Response(text="PolyRhythm bot is alive and healthy 🥁")

    aio_app = web.Application()
    aio_app.router.add_post("/webhook", telegram_webhook)
    aio_app.router.add_get("/",         health)
    aio_app.router.add_get("/health",   health)

    port = int(os.getenv("PORT", 7860))
    runner = web.AppRunner(aio_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"aiohttp server listening on port {port}")

    # Run until cancelled
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await ptb.bot.delete_webhook()
        await ptb.stop()
        await ptb.shutdown()


# ── Polling mode (local dev) ──────────────────────────────────────────────────

def run_polling():
    ptb = build_app()
    logger.info("Starting in POLLING mode (local dev).")
    ptb.run_polling(drop_pending_updates=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

    init_db()
    logger.info("Database initialised.")

    # Support both HuggingFace (HF_SPACE_URL) and Render (RENDER_EXTERNAL_URL)
    cloud_url = (
        os.getenv("HF_SPACE_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    )
    if cloud_url:
        logger.info(f"Cloud deployment detected ({cloud_url}) — starting in WEBHOOK mode.")
        asyncio.run(run_webhook(cloud_url))
    else:
        run_polling()


if __name__ == "__main__":
    main()

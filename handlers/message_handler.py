"""
Handles all plain-text messages:
  - Calorie corrections after photo analysis
  - General chat with the AI coach
"""
import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from llm import coach_reply

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # ── 1. Calorie correction after a photo ──────────────────────────────────
    meal_id = context.user_data.get("pending_correction_meal_id")
    if meal_id:
        # Check if this is a numeric correction
        match = re.fullmatch(r"\d{2,4}", text.replace(" ", ""))
        if match:
            corrected = int(match.group())
            original = context.user_data.get("pending_correction_calories", 0)
            db.update_meal_calories(meal_id, corrected)
            context.user_data.pop("pending_correction_meal_id", None)
            context.user_data.pop("pending_correction_calories", None)

            diff = corrected - original
            sign = "+" if diff >= 0 else ""
            await update.message.reply_text(
                f"✅ Updated! Logged as *{corrected} kcal* (was {original}, {sign}{diff})\n\n"
                "Your food log has been corrected. Keep going! 💪",
                parse_mode="Markdown"
            )
            return

        # User said "ok" or similar
        if text.lower() in {"ok", "okay", "correct", "yes", "good", "fine", "looks good", "👍"}:
            context.user_data.pop("pending_correction_meal_id", None)
            context.user_data.pop("pending_correction_calories", None)
            await update.message.reply_text("✅ Logged! Keep it up 🌟")
            return

    # ── 2. Weight logging from natural language ───────────────────────────────
    weight_match = re.search(
        r"\b(?:i (?:weigh|am|weight)|my weight(?: is)?|weighed?)(?: about)?\s*(\d{2,3}(?:\.\d)?)\s*kg?\b",
        text.lower()
    )
    if weight_match:
        weight_kg = float(weight_match.group(1))
        previous = db.get_last_weight(chat_id)
        db.log_weight(chat_id, weight_kg)
        from llm import generate_weight_feedback
        feedback = generate_weight_feedback(weight_kg, previous)
        await update.message.reply_text(feedback, parse_mode="Markdown")
        return

    # ── 3. General AI coach conversation ─────────────────────────────────────
    user = db.get_user(chat_id)
    if not user:
        await update.message.reply_text(
            "Hi! Please run /start first so I can get to know you. 😊"
        )
        return

    today_meals = db.get_today_meals(chat_id)
    reply = coach_reply(text, today_meals, user.get("food_prefs"))
    await update.message.reply_text(reply)

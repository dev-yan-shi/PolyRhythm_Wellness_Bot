"""
Handles food photo messages: download → Groq Vision analysis → log → respond.
"""
import logging
import os
import tempfile
from datetime import date, time as dtime

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from llm import analyze_food_image
from config import CALORIE_GOAL_TARGET, MEAL_TIMES

logger = logging.getLogger(__name__)


def _current_meal_type() -> str:
    """Guess meal type based on current IST time."""
    from datetime import datetime
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()

    if dtime(5, 0) <= now < dtime(11, 30):
        return "breakfast"
    elif dtime(11, 30) <= now < dtime(15, 30):
        return "lunch"
    elif dtime(15, 30) <= now < dtime(19, 0):
        return "snack"
    else:
        return "dinner"


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.message

    # Ensure user exists
    if not db.get_user(chat_id):
        await msg.reply_text(
            "Please run /start first to set up your profile before logging meals."
        )
        return

    await msg.reply_text("🔍 Analyzing your meal...")

    # Download the highest-resolution photo
    photo = msg.photo[-1]
    tg_file = await context.bot.get_file(photo.file_id)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        await tg_file.download_to_drive(tmp_path)

    try:
        meal_type = _current_meal_type()
        today_meals = db.get_today_meals(chat_id)
        calories_so_far = sum(m["calories"] or 0 for m in today_meals)

        # Read caption the user typed alongside the photo
        user_caption = msg.caption or ""

        result = analyze_food_image(tmp_path, meal_type, calories_so_far, user_caption)

        # Save to DB
        meal_id = db.log_meal(
            chat_id=chat_id,
            meal_type=meal_type,
            description=result.get("description", ""),
            calories_estimated=result.get("calories", 0),
            protein_g=result.get("protein_g"),
            carbs_g=result.get("carbs_g"),
            fat_g=result.get("fat_g"),
            photo_file_id=photo.file_id,
        )

        # Store meal_id in user_data for potential correction
        context.user_data["pending_correction_meal_id"] = meal_id
        context.user_data["pending_correction_calories"] = result.get("calories", 0)

        # Build response
        items_str = "\n".join(f"  • {item}" for item in result.get("items", []))
        cal = result.get("calories", 0)
        new_total = calories_so_far + cal
        remaining = CALORIE_GOAL_TARGET - new_total

        emoji = {"breakfast": "🌅", "lunch": "☀️", "snack": "🍎", "dinner": "🌙"}.get(meal_type, "🍽")

        caption_line = f"📝 *Your description:* _{user_caption.strip()}_\n\n" if user_caption.strip() else ""

        response = (
            f"{emoji} *{meal_type.capitalize()} logged!*\n\n"
            f"{caption_line}"
            f"📋 *What I identified:*\n{items_str}\n\n"
            f"🔥 *Estimated calories: {cal} kcal*\n"
            f"  └ Protein: {result.get('protein_g', 0):.0f}g  |  "
            f"Carbs: {result.get('carbs_g', 0):.0f}g  |  "
            f"Fat: {result.get('fat_g', 0):.0f}g\n\n"
            f"📊 *Today's total: {new_total} kcal*\n"
        )

        if remaining > 0:
            response += f"✅ {remaining} kcal remaining today\n"
        else:
            response += f"⚠️ {abs(remaining)} kcal over today's target\n"

        response += f"\n💬 {result.get('encouragement', '')}\n\n"
        response += f"_If the calorie count looks wrong, reply with the correct number (e.g. `420`). Otherwise type 'ok'._"

        await msg.reply_text(response, parse_mode="Markdown")

    finally:
        os.unlink(tmp_path)

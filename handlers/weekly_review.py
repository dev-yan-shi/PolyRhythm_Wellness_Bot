"""
Weekly review conversation: bot guides user through Sunday check-in,
then generates personalised feedback and customises the next week's plan.
"""
import logging
from datetime import date, timedelta

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from llm import generate_weekly_feedback, generate_meal_plan

logger = logging.getLogger(__name__)

# Conversation states
WHAT_WENT_WELL = 0
WHAT_WAS_HARD  = 1
ADDITIONAL     = 2


# ── Entry ─────────────────────────────────────────────────────────────────────

async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)
    name = user["name"] if user else "there"

    # Gather this week's data for context
    cal_data = db.get_daily_calories(chat_id, days=7)
    total_days_logged = len(cal_data)
    avg_cal = round(sum(c for _, c in cal_data) / max(total_days_logged, 1))

    context.user_data["review_cal_data"] = cal_data

    await update.message.reply_text(
        f"🔄 *Weekly Check-in — {date.today().strftime('%d %b %Y')}*\n\n"
        f"Hey {name}! Time for your weekly review. This will take just 2 minutes.\n\n"
        f"📊 *This week's snapshot:*\n"
        f"• Days with meals logged: {total_days_logged}/7\n"
        f"• Average daily intake: {avg_cal} kcal\n\n"
        f"Let's start — *what went well this week with your diet?* "
        f"(meals you're proud of, habits you kept, anything positive!)",
        parse_mode="Markdown"
    )
    return WHAT_WENT_WELL


# ── Step 1 ────────────────────────────────────────────────────────────────────

async def handle_what_went_well(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["went_well"] = update.message.text.strip()

    await update.message.reply_text(
        "That's great! 🙌\n\n"
        "Now, *what was challenging this week?* "
        "Any foods you struggled to avoid, meals you skipped, or habits that were hard to keep?",
        parse_mode="Markdown"
    )
    return WHAT_WAS_HARD


# ── Step 2 ────────────────────────────────────────────────────────────────────

async def handle_what_was_hard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["went_hard"] = update.message.text.strip()

    await update.message.reply_text(
        "Thanks for being honest — that's how we improve! 💪\n\n"
        "Anything else you'd like me to know before I write your feedback? "
        "_(e.g. you were travelling, stressed at work, had a social dinner, etc.)_\n\n"
        "Or type *skip* to go straight to your feedback.",
        parse_mode="Markdown"
    )
    return ADDITIONAL


# ── Step 3 + Generate Feedback ────────────────────────────────────────────────

async def handle_additional(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    extra = update.message.text.strip()
    if extra.lower() == "skip":
        extra = None

    await update.message.reply_text("✍️ Writing your personalised feedback...")

    user = db.get_user(chat_id) or {}
    weight_data = db.get_weight_history(chat_id, weeks=4)
    cal_data = context.user_data.get("review_cal_data", [])
    went_well = context.user_data.get("went_well", "")
    went_hard = context.user_data.get("went_hard", "")

    feedback = generate_weekly_feedback(
        weight_history=weight_data,
        daily_calories=cal_data,
        went_well=went_well,
        went_hard=went_hard,
        extra_notes=extra,
        food_prefs=user.get("food_prefs"),
    )

    await update.message.reply_text(feedback)

    # Save to DB
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    db.save_weekly_review(
        chat_id=chat_id,
        week_start=week_start,
        went_well=went_well,
        went_hard=went_hard,
        extra_notes=extra,
        bot_feedback=feedback,
    )

    # Generate next week's meal plan
    await update.message.reply_text(
        "📋 Now generating your *next week's meal plan* based on your feedback...",
        parse_mode="Markdown"
    )

    next_monday = (date.today() + timedelta(days=(7 - date.today().weekday()))).isoformat()
    last_week_meals = db.get_meals_for_range(chat_id, days=7)
    plan = generate_meal_plan(
        food_prefs=user.get("food_prefs"),
        allergies=user.get("allergies"),
        last_week_meals=last_week_meals,
        week_start=next_monday,
    )
    db.save_weekly_plan(chat_id, next_monday, plan)
    await update.message.reply_text(plan)

    # Clean up
    for key in ["went_well", "went_hard", "review_cal_data"]:
        context.user_data.pop(key, None)

    return ConversationHandler.END


# ── Cancel ────────────────────────────────────────────────────────────────────

async def cancel_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ["went_well", "went_hard", "review_cal_data"]:
        context.user_data.pop(key, None)
    await update.message.reply_text("Review cancelled. You can start again anytime with /review. 👍")
    return ConversationHandler.END

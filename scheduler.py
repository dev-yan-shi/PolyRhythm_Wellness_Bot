"""
All scheduled jobs using python-telegram-bot's built-in JobQueue.
Runs in IST timezone.
"""
import logging
from datetime import date, timedelta

from config import (
    TIMEZONE,
    MEAL_TIMES, MEAL_EMOJIS, SUNDAY,
    WEIGHT_CHECKIN_TIME, WEEKLY_REVIEW_TIME, MEAL_PLAN_GEN_TIME,
)

logger = logging.getLogger(__name__)


def _get_chat_ids() -> list[int]:
    """Return all registered chat_ids from the database."""
    import database as db
    return db.get_all_chat_ids()


# ── Meal Reminder Jobs ────────────────────────────────────────────────────────

async def _send_meal_reminder(context, meal_type: str):
    import database as db
    from llm import generate_meal_reminder

    for chat_id in _get_chat_ids():
        today_meals = db.get_today_meals(chat_id)
        today_calories = sum(m["calories"] or 0 for m in today_meals)
        message = generate_meal_reminder(meal_type, today_calories)
        emoji = MEAL_EMOJIS.get(meal_type, "🍽")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{emoji} *{meal_type.capitalize()} time!*\n\n{message}\n\n"
                 f"📸 _Send me a photo of your {meal_type} to log it!_",
            parse_mode="Markdown"
        )


async def breakfast_reminder(context):
    await _send_meal_reminder(context, "breakfast")

async def lunch_reminder(context):
    await _send_meal_reminder(context, "lunch")

async def snack_reminder(context):
    await _send_meal_reminder(context, "snack")

async def dinner_reminder(context):
    await _send_meal_reminder(context, "dinner")


# ── Weekly Jobs ───────────────────────────────────────────────────────────────

async def weekly_weight_checkin(context):
    for chat_id in _get_chat_ids():
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚖️ *Sunday Weigh-In Time!*\n\n"
                "How much do you weigh this morning?\n\n"
                "Reply with: `/weight 65.5` (use your actual kg)\n\n"
                "_Tip: Weigh yourself first thing in the morning, after using the bathroom, for the most consistent reading._"
            ),
            parse_mode="Markdown"
        )


async def weekly_review_prompt(context):
    for chat_id in _get_chat_ids():
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🔄 *Time for your Weekly Review!*\n\n"
                "Let's reflect on this week, celebrate your wins, and plan for an even better next week.\n\n"
                "Type /review to start your 2-minute check-in. 💪"
            ),
            parse_mode="Markdown"
        )


async def auto_generate_meal_plan(context):
    """Generate next week's meal plan automatically on Sunday night if not done via review."""
    import database as db
    from llm import generate_meal_plan

    next_monday = (date.today() + timedelta(days=(7 - date.today().weekday()))).isoformat()

    for chat_id in _get_chat_ids():
        # Don't regenerate if already done in the weekly review
        if db.get_current_plan(chat_id):
            continue
        user = db.get_user(chat_id) or {}
        last_week_meals = db.get_meals_for_range(chat_id, days=7)
        plan = generate_meal_plan(
            food_prefs=user.get("food_prefs"),
            allergies=user.get("allergies"),
            last_week_meals=last_week_meals,
            week_start=next_monday,
        )
        db.save_weekly_plan(chat_id, next_monday, plan)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📋 *Your meal plan for next week is ready!*\n\n{plan}",
            parse_mode="Markdown"
        )


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_jobs(job_queue):
    """Register all scheduled jobs with the bot's JobQueue."""
    from datetime import time

    def _ist(t: time):
        """Make a time object timezone-aware in IST."""
        return t.replace(tzinfo=TIMEZONE)

    # Daily meal reminders (every day)
    ALL_DAYS = tuple(range(7))  # 0=Sun through 6=Sat in PTB
    job_queue.run_daily(breakfast_reminder, time=_ist(MEAL_TIMES["breakfast"]), days=ALL_DAYS, name="breakfast")
    job_queue.run_daily(lunch_reminder,     time=_ist(MEAL_TIMES["lunch"]),     days=ALL_DAYS, name="lunch")
    job_queue.run_daily(snack_reminder,     time=_ist(MEAL_TIMES["snack"]),     days=ALL_DAYS, name="snack")
    job_queue.run_daily(dinner_reminder,    time=_ist(MEAL_TIMES["dinner"]),    days=ALL_DAYS, name="dinner")

    # Weekly Sunday jobs  (0 = Sunday in PTB JobQueue)
    SUNDAY_ONLY = (0,)
    job_queue.run_daily(weekly_weight_checkin,  time=_ist(WEIGHT_CHECKIN_TIME),  days=SUNDAY_ONLY, name="weight_checkin")
    job_queue.run_daily(weekly_review_prompt,   time=_ist(WEEKLY_REVIEW_TIME),   days=SUNDAY_ONLY, name="review_prompt")
    job_queue.run_daily(auto_generate_meal_plan, time=_ist(MEAL_PLAN_GEN_TIME),  days=SUNDAY_ONLY, name="meal_plan")

    logger.info("All scheduled jobs registered.")

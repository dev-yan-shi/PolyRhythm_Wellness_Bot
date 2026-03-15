"""
Command handlers: /start, /help, /weight, /today, /mealplan, /dashboard, /summary
"""
import json
import logging
import io
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from llm import generate_meal_plan, generate_weight_feedback
from config import CALORIE_GOAL_MIN, CALORIE_GOAL_MAX, CALORIE_GOAL_TARGET

logger = logging.getLogger(__name__)

# Onboarding conversation states
ASK_NAME, ASK_FOOD_PREFS, ASK_ALLERGIES = range(3)


# ── /start ────────────────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)

    # Save chat_id for scheduler
    _save_chat_id(chat_id)

    if user:
        await update.message.reply_text(
            f"Welcome back, {user['name'] or 'friend'}! 👋\n\n"
            "I'm your personal life coach. Here's what you can do:\n\n"
            "📸 Send me a *food photo* anytime to log it\n"
            "⚖️ /weight `65.5` — log your weight\n"
            "📋 /mealplan — get this week's meal plan\n"
            "📊 /today — see today's calorie summary\n"
            "📈 /dashboard — charts & stats\n"
            "🔄 /review — weekly check-in\n"
            "❓ /help — full command list",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Hi there! 👋 I'm your AI Personal Life Coach.\n\n"
        "I'll help you track nutrition, log meals from photos, plan your week, "
        "and keep you on track toward your health goals.\n\n"
        "Let's get you set up in just 2 quick steps!\n\n"
        "*What's your name?*",
        parse_mode="Markdown"
    )
    return ASK_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["name"] = name
    await update.message.reply_text(
        f"Great to meet you, {name}! 🌟\n\n"
        "Tell me about your *food preferences*.\n"
        "For example: _I love South Indian food, I'm vegetarian, I enjoy paneer dishes, I don't like overly spicy food._\n\n"
        "The more you tell me, the better I can personalise your meal plans!",
        parse_mode="Markdown"
    )
    return ASK_FOOD_PREFS


async def handle_food_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["food_prefs"] = update.message.text.strip()
    await update.message.reply_text(
        "Got it! 🥗\n\n"
        "Any *food allergies or things you want to avoid?*\n"
        "(Type 'none' if none)",
        parse_mode="Markdown"
    )
    return ASK_ALLERGIES


async def handle_allergies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    allergies = update.message.text.strip()
    if allergies.lower() == "none":
        allergies = None

    db.upsert_user(
        chat_id,
        name=context.user_data.get("name"),
        food_prefs=context.user_data.get("food_prefs"),
        allergies=allergies
    )
    _save_chat_id(chat_id)

    await update.message.reply_text(
        f"You're all set, {context.user_data.get('name')}! 🎉\n\n"
        "Here's what I'll do for you:\n"
        "• 📸 Analyze your meal photos and count calories\n"
        "• ⏰ Remind you to log meals at breakfast, lunch, snack & dinner\n"
        "• 📋 Generate a personalised weekly meal plan every Sunday\n"
        "• ⚖️ Track your weekly weight and progress\n"
        "• 📊 Give you weekly feedback and adjust your plan\n\n"
        "Your daily calorie goal: *1100–1200 kcal*\n\n"
        "Start by sending me a photo of your next meal! 📷",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ── /help ─────────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Your Life Coach — Commands*\n\n"
        "📸 *Send a photo* → Log any meal (auto-analyzes)\n\n"
        "⚖️ /weight `65.5` → Log your weight in kg\n"
        "📋 /mealplan → Get this week's meal plan\n"
        "📊 /today → Today's calorie summary\n"
        "📈 /dashboard → Charts: weight, calories, consistency\n"
        "🔄 /review → Start weekly review chat\n"
        "👤 /profile → View your saved preferences\n"
        "✏️ /updateprefs → Update food preferences\n\n"
        "💬 Or just *chat with me* — ask anything about nutrition!",
        parse_mode="Markdown"
    )


# ── /weight ───────────────────────────────────────────────────────────────────

async def weight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "Please provide your weight in kg.\nExample: `/weight 65.5`",
            parse_mode="Markdown"
        )
        return

    try:
        weight_kg = float(args[0])
        if weight_kg < 20 or weight_kg > 300:
            raise ValueError("Out of range")
    except ValueError:
        await update.message.reply_text("Please enter a valid weight, e.g., `/weight 65.5`", parse_mode="Markdown")
        return

    previous = db.get_last_weight(chat_id)
    db.log_weight(chat_id, weight_kg)

    from llm import generate_weight_feedback
    feedback = generate_weight_feedback(weight_kg, previous)
    await update.message.reply_text(feedback, parse_mode="Markdown")


# ── /today ────────────────────────────────────────────────────────────────────

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    meals = db.get_today_meals(chat_id)

    if not meals:
        await update.message.reply_text(
            "Nothing logged today yet! 📭\n\nSend me a photo of your meal to get started.",
        )
        return

    total_cal = sum(m["calories"] or 0 for m in meals)
    remaining = CALORIE_GOAL_TARGET - total_cal
    pct = min(100, round((total_cal / CALORIE_GOAL_TARGET) * 100))

    bar_filled = round(pct / 10)
    progress_bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)

    lines = [f"📊 *Today — {date.today().strftime('%d %b')}*\n"]
    for m in meals:
        emoji = {"breakfast": "🌅", "lunch": "☀️", "snack": "🍎", "dinner": "🌙"}.get(m["meal_type"], "🍽")
        lines.append(f"{emoji} {m['meal_type'].capitalize()}: {m['description']} — *{m['calories']} kcal*")

    lines.append(f"\n{progress_bar}")
    lines.append(f"*{total_cal} / {CALORIE_GOAL_TARGET} kcal* ({pct}%)")

    if remaining > 0:
        lines.append(f"\n✅ {remaining} kcal remaining — you're on track!")
    else:
        over = abs(remaining)
        lines.append(f"\n⚠️ {over} kcal over target today. Tomorrow is a fresh start! 💪")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /mealplan ─────────────────────────────────────────────────────────────────

async def mealplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("⏳ Generating your personalised meal plan...")

    plan = db.get_current_plan(chat_id)
    if plan:
        await update.message.reply_text(plan)
        return

    user = db.get_user(chat_id) or {}
    last_week = db.get_meals_for_range(chat_id, days=7)
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    plan = generate_meal_plan(
        food_prefs=user.get("food_prefs"),
        allergies=user.get("allergies"),
        last_week_meals=last_week,
        week_start=monday
    )
    db.save_weekly_plan(chat_id, monday, plan)
    await update.message.reply_text(plan)


# ── /dashboard ────────────────────────────────────────────────────────────────

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("📊 Building your dashboard...")

    weight_data = db.get_weight_history(chat_id, weeks=8)
    cal_data = db.get_daily_calories(chat_id, days=14)
    consistency = db.get_consistency(chat_id, days=7)
    meals_today = db.get_today_meals(chat_id)
    total_today = sum(m["calories"] or 0 for m in meals_today)

    # ── Summary text ──
    last_weight = db.get_last_weight(chat_id)
    weight_str = f"{last_weight[1]} kg (as of {last_weight[0]})" if last_weight else "not logged yet"

    summary = (
        f"📈 *Your Health Dashboard*\n\n"
        f"⚖️ Last weight: *{weight_str}*\n"
        f"🔥 Today's intake: *{total_today} kcal* / {CALORIE_GOAL_TARGET} kcal\n"
        f"✅ This week's consistency: *{consistency}%*\n\n"
    )
    await update.message.reply_text(summary, parse_mode="Markdown")

    # ── Charts ──
    if weight_data or cal_data:
        img = _build_dashboard_chart(weight_data, cal_data)
        await update.message.reply_photo(photo=img, caption="Your progress charts 📉📊")
    else:
        await update.message.reply_text(
            "No data to chart yet — keep logging meals and weight to see your trends here! 🌱"
        )


def _build_dashboard_chart(weight_data, cal_data):
    fig, axes = plt.subplots(2, 1, figsize=(8, 8), facecolor="#1a1a2e")
    fig.subplots_adjust(hspace=0.4)

    for ax in axes:
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

    # Weight chart
    if weight_data:
        dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in weight_data]
        weights = [w for _, w in weight_data]
        axes[0].plot(dates, weights, color="#00d4aa", linewidth=2, marker="o", markersize=5)
        axes[0].fill_between(dates, weights, alpha=0.15, color="#00d4aa")
        axes[0].set_title("⚖️ Weight History (kg)", fontsize=13, pad=10)
        axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        axes[0].xaxis.set_major_locator(mdates.WeekdayLocator())
        fig.autofmt_xdate()
    else:
        axes[0].text(0.5, 0.5, "No weight data yet\nUse /weight to log", ha="center", va="center",
                     color="white", fontsize=12, transform=axes[0].transAxes)
        axes[0].set_title("⚖️ Weight History", fontsize=13)

    # Calorie chart
    if cal_data:
        dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in cal_data]
        cals = [c or 0 for _, c in cal_data]
        bar_colors = ["#00d4aa" if c <= CALORIE_GOAL_MAX else "#ff6b6b" for c in cals]
        axes[1].bar(dates, cals, color=bar_colors, width=0.6)
        axes[1].axhline(CALORIE_GOAL_MIN, color="#ffd700", linestyle="--", linewidth=1, label=f"Min {CALORIE_GOAL_MIN}")
        axes[1].axhline(CALORIE_GOAL_MAX, color="#ff6b6b", linestyle="--", linewidth=1, label=f"Max {CALORIE_GOAL_MAX}")
        axes[1].legend(facecolor="#1a1a2e", labelcolor="white", fontsize=9)
        axes[1].set_title("🔥 Daily Calorie Intake (last 14 days)", fontsize=13, pad=10)
        axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        fig.autofmt_xdate()
    else:
        axes[1].text(0.5, 0.5, "No meal data yet\nSend food photos to log", ha="center", va="center",
                     color="white", fontsize=12, transform=axes[1].transAxes)
        axes[1].set_title("🔥 Daily Calorie Intake", fontsize=13)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    buf.seek(0)
    plt.close(fig)
    return buf


# ── /profile ──────────────────────────────────────────────────────────────────

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)
    if not user:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return
    await update.message.reply_text(
        f"👤 *Your Profile*\n\n"
        f"Name: {user['name'] or 'Not set'}\n"
        f"Food preferences: {user['food_prefs'] or 'Not set'}\n"
        f"Allergies: {user['allergies'] or 'None'}\n"
        f"Daily calorie goal: 1100–1200 kcal",
        parse_mode="Markdown"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_chat_id(chat_id: int):
    import json, os
    from config import SETTINGS_PATH
    settings = {}
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            settings = json.load(f)
    settings["chat_id"] = chat_id
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f)

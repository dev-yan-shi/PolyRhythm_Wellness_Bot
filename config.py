import os
from datetime import time
import pytz
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ── User Profile ──────────────────────────────────────────────────────────────
CALORIE_GOAL_MIN = 1100
CALORIE_GOAL_MAX = 1200
CALORIE_GOAL_TARGET = 1150  # midpoint used for meal planning

TIMEZONE = pytz.timezone("Asia/Kolkata")

# ── Meal Reminder Times (IST) ─────────────────────────────────────────────────
MEAL_TIMES = {
    "breakfast": time(9, 30),
    "lunch":     time(13, 0),
    "snack":     time(17, 0),
    "dinner":    time(21, 0),
}

MEAL_EMOJIS = {
    "breakfast": "🌅",
    "lunch":     "☀️",
    "snack":     "🍎",
    "dinner":    "🌙",
}

# ── Weekly Schedule (all times IST, day 0 = Sunday in PTB JobQueue) ───────────
SUNDAY = 0
WEIGHT_CHECKIN_TIME  = time(8, 0)   # Sunday 8:00 AM
WEEKLY_REVIEW_TIME   = time(20, 0)  # Sunday 8:00 PM
MEAL_PLAN_GEN_TIME   = time(21, 30) # Sunday 9:30 PM

# ── LLM Models ────────────────────────────────────────────────────────────────
GROQ_TEXT_MODEL   = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ── Paths ─────────────────────────────────────────────────────────────────────
# DATA_DIR is set to /data on Fly.io and Render (persistent volume).
# Falls back to current directory when running locally.
_DATA_DIR = os.getenv("DATA_DIR", ".")
DB_PATH   = os.path.join(_DATA_DIR, "life_coach.db")
SETTINGS_PATH = "settings.json"  # legacy — no longer used for scheduler

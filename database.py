import sqlite3
from datetime import date, datetime, timedelta
from config import DB_PATH


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    with _conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id              INTEGER PRIMARY KEY,
            chat_id         INTEGER UNIQUE NOT NULL,
            name            TEXT,
            food_prefs      TEXT,
            allergies       TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS meal_log (
            id                  INTEGER PRIMARY KEY,
            chat_id             INTEGER NOT NULL,
            date                TEXT NOT NULL,
            meal_type           TEXT NOT NULL,
            description         TEXT,
            calories_estimated  INTEGER,
            calories_final      INTEGER,
            protein_g           REAL,
            carbs_g             REAL,
            fat_g               REAL,
            photo_file_id       TEXT,
            created_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weight_log (
            id         INTEGER PRIMARY KEY,
            chat_id    INTEGER NOT NULL,
            date       TEXT NOT NULL,
            weight_kg  REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weekly_plan (
            id          INTEGER PRIMARY KEY,
            chat_id     INTEGER NOT NULL,
            week_start  TEXT NOT NULL,
            plan_text   TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weekly_review (
            id            INTEGER PRIMARY KEY,
            chat_id       INTEGER NOT NULL,
            week_start    TEXT NOT NULL,
            went_well     TEXT,
            went_hard     TEXT,
            extra_notes   TEXT,
            bot_feedback  TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS conversation_state (
            chat_id  INTEGER PRIMARY KEY,
            state    TEXT,
            context  TEXT,
            updated  TEXT DEFAULT (datetime('now'))
        );
        """)


def _conn():
    return sqlite3.connect(DB_PATH)


# ── User Profile ──────────────────────────────────────────────────────────────

def upsert_user(chat_id: int, name: str = None, food_prefs: str = None, allergies: str = None):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO user_profile (chat_id, name, food_prefs, allergies)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                name       = COALESCE(excluded.name, name),
                food_prefs = COALESCE(excluded.food_prefs, food_prefs),
                allergies  = COALESCE(excluded.allergies, allergies)
        """, (chat_id, name, food_prefs, allergies))


def get_user(chat_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_profile WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    if not row:
        return None
    cols = ["id", "chat_id", "name", "food_prefs", "allergies", "created_at"]
    return dict(zip(cols, row))


# ── Meal Log ──────────────────────────────────────────────────────────────────

def log_meal(chat_id, meal_type, description, calories_estimated,
             protein_g=None, carbs_g=None, fat_g=None, photo_file_id=None):
    today = date.today().isoformat()
    with _conn() as conn:
        cur = conn.execute("""
            INSERT INTO meal_log
              (chat_id, date, meal_type, description, calories_estimated,
               calories_final, protein_g, carbs_g, fat_g, photo_file_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (chat_id, today, meal_type, description, calories_estimated,
              calories_estimated, protein_g, carbs_g, fat_g, photo_file_id))
    return cur.lastrowid


def update_meal_calories(meal_id: int, corrected_calories: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE meal_log SET calories_final = ? WHERE id = ?",
            (corrected_calories, meal_id)
        )


def get_today_meals(chat_id: int):
    today = date.today().isoformat()
    with _conn() as conn:
        rows = conn.execute("""
            SELECT meal_type, description, calories_final, protein_g, carbs_g, fat_g
            FROM meal_log WHERE chat_id = ? AND date = ?
            ORDER BY created_at
        """, (chat_id, today)).fetchall()
    cols = ["meal_type", "description", "calories", "protein_g", "carbs_g", "fat_g"]
    return [dict(zip(cols, r)) for r in rows]


def get_meals_for_range(chat_id: int, days: int = 7):
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    with _conn() as conn:
        rows = conn.execute("""
            SELECT date, meal_type, description, calories_final
            FROM meal_log WHERE chat_id = ? AND date >= ?
            ORDER BY date, created_at
        """, (chat_id, start)).fetchall()
    cols = ["date", "meal_type", "description", "calories"]
    return [dict(zip(cols, r)) for r in rows]


def get_daily_calories(chat_id: int, days: int = 7):
    """Returns list of (date, total_calories) for the last N days."""
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    with _conn() as conn:
        rows = conn.execute("""
            SELECT date, SUM(calories_final)
            FROM meal_log WHERE chat_id = ? AND date >= ?
            GROUP BY date ORDER BY date
        """, (chat_id, start)).fetchall()
    return rows  # list of (date_str, total_cal)


# ── Weight Log ────────────────────────────────────────────────────────────────

def log_weight(chat_id: int, weight_kg: float):
    today = date.today().isoformat()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO weight_log (chat_id, date, weight_kg) VALUES (?, ?, ?)
            ON CONFLICT DO NOTHING
        """, (chat_id, today, weight_kg))


def get_weight_history(chat_id: int, weeks: int = 8):
    start = (date.today() - timedelta(weeks=weeks)).isoformat()
    with _conn() as conn:
        rows = conn.execute("""
            SELECT date, weight_kg FROM weight_log
            WHERE chat_id = ? AND date >= ?
            ORDER BY date
        """, (chat_id, start)).fetchall()
    return rows  # list of (date_str, weight_kg)


def get_last_weight(chat_id: int):
    with _conn() as conn:
        row = conn.execute("""
            SELECT date, weight_kg FROM weight_log
            WHERE chat_id = ? ORDER BY date DESC LIMIT 1
        """, (chat_id,)).fetchone()
    return row  # (date_str, weight_kg) or None


# ── Weekly Plan ───────────────────────────────────────────────────────────────

def save_weekly_plan(chat_id: int, week_start: str, plan_text: str):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO weekly_plan (chat_id, week_start, plan_text)
            VALUES (?, ?, ?)
            ON CONFLICT DO NOTHING
        """, (chat_id, week_start, plan_text))


def get_current_plan(chat_id: int):
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    with _conn() as conn:
        row = conn.execute("""
            SELECT plan_text FROM weekly_plan
            WHERE chat_id = ? AND week_start = ?
        """, (chat_id, monday)).fetchone()
    return row[0] if row else None


# ── Weekly Review ─────────────────────────────────────────────────────────────

def save_weekly_review(chat_id: int, week_start: str, went_well: str,
                       went_hard: str, extra_notes: str, bot_feedback: str):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO weekly_review
              (chat_id, week_start, went_well, went_hard, extra_notes, bot_feedback)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chat_id, week_start, went_well, went_hard, extra_notes, bot_feedback))


# ── Conversation State ────────────────────────────────────────────────────────

def set_state(chat_id: int, state: str, context: str = None):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO conversation_state (chat_id, state, context, updated)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(chat_id) DO UPDATE SET state = excluded.state,
                context = excluded.context, updated = excluded.updated
        """, (chat_id, state, context))


def get_state(chat_id: int):
    with _conn() as conn:
        row = conn.execute(
            "SELECT state, context FROM conversation_state WHERE chat_id = ?",
            (chat_id,)
        ).fetchone()
    return row if row else (None, None)


def clear_state(chat_id: int):
    with _conn() as conn:
        conn.execute(
            "DELETE FROM conversation_state WHERE chat_id = ?", (chat_id,)
        )


# ── Multi-user helpers ────────────────────────────────────────────────────────

def get_all_chat_ids() -> list[int]:
    """Return all registered user chat_ids — used by the scheduler."""
    with _conn() as conn:
        rows = conn.execute("SELECT chat_id FROM user_profile").fetchall()
    return [r[0] for r in rows]


# ── Stats helpers ─────────────────────────────────────────────────────────────

def get_consistency(chat_id: int, days: int = 7) -> float:
    """Percentage of last N days that had at least one meal logged."""
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    with _conn() as conn:
        row = conn.execute("""
            SELECT COUNT(DISTINCT date) FROM meal_log
            WHERE chat_id = ? AND date >= ?
        """, (chat_id, start)).fetchone()
    logged_days = row[0] if row else 0
    return round((logged_days / days) * 100, 1)

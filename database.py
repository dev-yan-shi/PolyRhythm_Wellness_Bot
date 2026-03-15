import os
import sqlite3
from datetime import date, datetime, timedelta
from config import DB_PATH

# ── Backend selection ─────────────────────────────────────────────────────────
# Set DATABASE_URL env var to a PostgreSQL URL to use Supabase/Postgres.
# Falls back to local SQLite when DATABASE_URL is not set (local dev).

DATABASE_URL = os.getenv("DATABASE_URL")
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    import psycopg2.extras


def _conn():
    if USE_PG:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)


def _q(sql: str) -> str:
    """Swap SQLite ? placeholders → PostgreSQL %s placeholders."""
    if USE_PG:
        return sql.replace("?", "%s")
    return sql


def _exec(sql: str, params: tuple = (), fetch: str = None):
    """
    Run a single statement. fetch=None|'one'|'all'.
    Returns cursor.lastrowid (INSERT) or fetched rows.
    """
    conn = _conn()
    try:
        if USE_PG:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
        cur.execute(_q(sql), params)
        conn.commit()
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "all":
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        return cur.lastrowid
    finally:
        conn.close()


def _execscript(sql: str):
    """Run a multi-statement DDL script (schema creation)."""
    conn = _conn()
    try:
        if USE_PG:
            cur = conn.cursor()
            cur.execute(sql)
        else:
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS user_profile (
    id         INTEGER PRIMARY KEY,
    chat_id    INTEGER UNIQUE NOT NULL,
    name       TEXT,
    food_prefs TEXT,
    allergies  TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS meal_log (
    id                 INTEGER PRIMARY KEY,
    chat_id            INTEGER NOT NULL,
    date               TEXT NOT NULL,
    meal_type          TEXT NOT NULL,
    description        TEXT,
    calories_estimated INTEGER,
    calories_final     INTEGER,
    protein_g          REAL,
    carbs_g            REAL,
    fat_g              REAL,
    photo_file_id      TEXT,
    created_at         TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS weight_log (
    id         INTEGER PRIMARY KEY,
    chat_id    INTEGER NOT NULL,
    date       TEXT NOT NULL,
    weight_kg  REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(chat_id, date)
);
CREATE TABLE IF NOT EXISTS weekly_plan (
    id         INTEGER PRIMARY KEY,
    chat_id    INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    plan_text  TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(chat_id, week_start)
);
CREATE TABLE IF NOT EXISTS weekly_review (
    id           INTEGER PRIMARY KEY,
    chat_id      INTEGER NOT NULL,
    week_start   TEXT NOT NULL,
    went_well    TEXT,
    went_hard    TEXT,
    extra_notes  TEXT,
    bot_feedback TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS conversation_state (
    chat_id INTEGER PRIMARY KEY,
    state   TEXT,
    context TEXT,
    updated TEXT DEFAULT (datetime('now'))
);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS user_profile (
    id         SERIAL PRIMARY KEY,
    chat_id    BIGINT UNIQUE NOT NULL,
    name       TEXT,
    food_prefs TEXT,
    allergies  TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS meal_log (
    id                 SERIAL PRIMARY KEY,
    chat_id            BIGINT NOT NULL,
    date               DATE NOT NULL,
    meal_type          TEXT NOT NULL,
    description        TEXT,
    calories_estimated INTEGER,
    calories_final     INTEGER,
    protein_g          REAL,
    carbs_g            REAL,
    fat_g              REAL,
    photo_file_id      TEXT,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS weight_log (
    id         SERIAL PRIMARY KEY,
    chat_id    BIGINT NOT NULL,
    date       DATE NOT NULL,
    weight_kg  REAL NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chat_id, date)
);
CREATE TABLE IF NOT EXISTS weekly_plan (
    id         SERIAL PRIMARY KEY,
    chat_id    BIGINT NOT NULL,
    week_start DATE NOT NULL,
    plan_text  TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chat_id, week_start)
);
CREATE TABLE IF NOT EXISTS weekly_review (
    id           SERIAL PRIMARY KEY,
    chat_id      BIGINT NOT NULL,
    week_start   DATE NOT NULL,
    went_well    TEXT,
    went_hard    TEXT,
    extra_notes  TEXT,
    bot_feedback TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS conversation_state (
    chat_id BIGINT PRIMARY KEY,
    state   TEXT,
    context TEXT,
    updated TIMESTAMPTZ DEFAULT NOW()
);
"""


def init_db():
    _execscript(_SCHEMA_PG if USE_PG else _SCHEMA_SQLITE)


# ── User Profile ──────────────────────────────────────────────────────────────

def upsert_user(chat_id: int, name: str = None, food_prefs: str = None, allergies: str = None):
    _exec("""
        INSERT INTO user_profile (chat_id, name, food_prefs, allergies)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            name       = COALESCE(EXCLUDED.name, user_profile.name),
            food_prefs = COALESCE(EXCLUDED.food_prefs, user_profile.food_prefs),
            allergies  = COALESCE(EXCLUDED.allergies, user_profile.allergies)
    """, (chat_id, name, food_prefs, allergies))


def get_user(chat_id: int):
    return _exec(
        "SELECT * FROM user_profile WHERE chat_id = ?",
        (chat_id,), fetch="one"
    )


# ── Meal Log ──────────────────────────────────────────────────────────────────

def log_meal(chat_id, meal_type, description, calories_estimated,
             protein_g=None, carbs_g=None, fat_g=None, photo_file_id=None):
    today = date.today().isoformat()
    return _exec("""
        INSERT INTO meal_log
          (chat_id, date, meal_type, description, calories_estimated,
           calories_final, protein_g, carbs_g, fat_g, photo_file_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (chat_id, today, meal_type, description, calories_estimated,
          calories_estimated, protein_g, carbs_g, fat_g, photo_file_id))


def update_meal_calories(meal_id: int, corrected_calories: int):
    _exec(
        "UPDATE meal_log SET calories_final = ? WHERE id = ?",
        (corrected_calories, meal_id)
    )


def get_today_meals(chat_id: int):
    today = date.today().isoformat()
    return _exec("""
        SELECT meal_type, description, calories_final, protein_g, carbs_g, fat_g
        FROM meal_log WHERE chat_id = ? AND date = ?
        ORDER BY created_at
    """, (chat_id, today), fetch="all")


def get_meals_for_range(chat_id: int, days: int = 7):
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    return _exec("""
        SELECT date, meal_type, description, calories_final
        FROM meal_log WHERE chat_id = ? AND date >= ?
        ORDER BY date, created_at
    """, (chat_id, start), fetch="all")


def get_daily_calories(chat_id: int, days: int = 7):
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = _exec("""
        SELECT date, SUM(calories_final) as total
        FROM meal_log WHERE chat_id = ? AND date >= ?
        GROUP BY date ORDER BY date
    """, (chat_id, start), fetch="all")
    return [(r["date"], r["total"]) for r in rows] if rows else []


# ── Weight Log ────────────────────────────────────────────────────────────────

def log_weight(chat_id: int, weight_kg: float):
    today = date.today().isoformat()
    _exec("""
        INSERT INTO weight_log (chat_id, date, weight_kg) VALUES (?, ?, ?)
        ON CONFLICT (chat_id, date) DO UPDATE SET weight_kg = EXCLUDED.weight_kg
    """, (chat_id, today, weight_kg))


def get_weight_history(chat_id: int, weeks: int = 8):
    start = (date.today() - timedelta(weeks=weeks)).isoformat()
    rows = _exec("""
        SELECT date, weight_kg FROM weight_log
        WHERE chat_id = ? AND date >= ?
        ORDER BY date
    """, (chat_id, start), fetch="all")
    return [(r["date"], r["weight_kg"]) for r in rows] if rows else []


def get_last_weight(chat_id: int):
    row = _exec("""
        SELECT date, weight_kg FROM weight_log
        WHERE chat_id = ? ORDER BY date DESC LIMIT 1
    """, (chat_id,), fetch="one")
    return (row["date"], row["weight_kg"]) if row else None


# ── Weekly Plan ───────────────────────────────────────────────────────────────

def save_weekly_plan(chat_id: int, week_start: str, plan_text: str):
    _exec("""
        INSERT INTO weekly_plan (chat_id, week_start, plan_text)
        VALUES (?, ?, ?)
        ON CONFLICT (chat_id, week_start) DO UPDATE SET plan_text = EXCLUDED.plan_text
    """, (chat_id, week_start, plan_text))


def get_current_plan(chat_id: int):
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    row = _exec("""
        SELECT plan_text FROM weekly_plan
        WHERE chat_id = ? AND week_start = ?
    """, (chat_id, monday), fetch="one")
    return row["plan_text"] if row else None


# ── Weekly Review ─────────────────────────────────────────────────────────────

def save_weekly_review(chat_id: int, week_start: str, went_well: str,
                       went_hard: str, extra_notes: str, bot_feedback: str):
    _exec("""
        INSERT INTO weekly_review
          (chat_id, week_start, went_well, went_hard, extra_notes, bot_feedback)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (chat_id, week_start, went_well, went_hard, extra_notes, bot_feedback))


# ── Conversation State ────────────────────────────────────────────────────────

def set_state(chat_id: int, state: str, context: str = None):
    now_fn = "NOW()" if USE_PG else "datetime('now')"
    _exec(f"""
        INSERT INTO conversation_state (chat_id, state, context, updated)
        VALUES (?, ?, ?, {now_fn})
        ON CONFLICT(chat_id) DO UPDATE SET
            state = EXCLUDED.state,
            context = EXCLUDED.context,
            updated = EXCLUDED.updated
    """, (chat_id, state, context))


def get_state(chat_id: int):
    row = _exec(
        "SELECT state, context FROM conversation_state WHERE chat_id = ?",
        (chat_id,), fetch="one"
    )
    return (row["state"], row["context"]) if row else (None, None)


def clear_state(chat_id: int):
    _exec("DELETE FROM conversation_state WHERE chat_id = ?", (chat_id,))


# ── Multi-user helpers ────────────────────────────────────────────────────────

def get_all_chat_ids() -> list[int]:
    rows = _exec("SELECT chat_id FROM user_profile", fetch="all")
    return [r["chat_id"] for r in rows] if rows else []


# ── Stats helpers ─────────────────────────────────────────────────────────────

def get_consistency(chat_id: int, days: int = 7) -> float:
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    row = _exec("""
        SELECT COUNT(DISTINCT date) as cnt FROM meal_log
        WHERE chat_id = ? AND date >= ?
    """, (chat_id, start), fetch="one")
    logged_days = row["cnt"] if row else 0
    return round((logged_days / days) * 100, 1)

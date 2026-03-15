# PolyRhythm Wellness Bot — Project Brief for Claude

## What is this?
An AI-powered personal life coach Telegram bot named **PolyRhythm**.
Named by the owner who plays drums — "managing different rhythms of life."
Built for personal use by Devyanshi Singh, based in Bangalore, India (IST timezone).

## GitHub Repo
https://github.com/dev-yan-shi/PolyRhythm_Wellness_Bot

## Deployment
- **Platform**: Render.com (free web service, Docker)
- **Live URL**: https://polyrhythm-wellness-bot.onrender.com
- **Mode**: Webhook (Telegram pushes updates to Render)
- **Database**: Supabase PostgreSQL (free tier, connection pooler for IPv4)
- **Auto-deploy**: Every `git push` to `main` triggers a Render redeploy

## Local Development
- Path: `/Users/devyanshi/Projects/life-coach-bot`
- Run locally: `cd /Users/devyanshi/Projects/life-coach-bot && venv/bin/python3 main.py`
- Uses polling mode when `HF_SPACE_URL` and `RENDER_EXTERNAL_URL` are not set
- Secrets stored in `.env` (never committed to GitHub)

## Tech Stack
- **Language**: Python 3.12
- **Bot framework**: python-telegram-bot v21
- **LLM (text)**: Groq — `llama-3.3-70b-versatile`
- **LLM (vision/food photos)**: Groq — `meta-llama/llama-4-scout-17b-16e-instruct`
- **Scheduler**: APScheduler (meal reminders, weekly review, weight check-in)
- **Database**: Supabase PostgreSQL (cloud) / SQLite (local fallback)
- **Dashboard**: Streamlit + Plotly (in `/dashboard/app.py`)

## Environment Variables (set on Render + local .env)
- `GROQ_API_KEY` — from console.groq.com
- `TELEGRAM_BOT_TOKEN` — from @BotFather on Telegram
- `DATABASE_URL` — Supabase connection pooler URI (port 6543, IPv4)
- `RENDER_EXTERNAL_URL` — auto-set by Render, triggers webhook mode
- `HF_SPACE_URL` — only if deploying to HuggingFace (NOT recommended, blocks Telegram)

## User Preferences (hardcoded defaults)
- Daily calorie goal: 1100–1200 kcal
- Timezone: Asia/Kolkata (IST)
- Meal times: Breakfast 9:30AM, Lunch 1PM, Snack 5PM, Dinner 9PM
- Weekly weigh-in: Sunday 8AM
- Weekly review: Sunday 8PM
- New meal plan: Sunday 9:30PM
- Food: Indian cuisine, Bangalore-based diet

## Phase 1 Features (implemented)
- [x] Food photo analysis with calorie estimation (Groq Vision)
- [x] Caption context used alongside photo for better accuracy
- [x] Manual calorie correction after bot estimates
- [x] Daily meal reminders at meal times
- [x] Weekly weight tracking (Sunday weigh-in)
- [x] Weekly review conversation (what went well / what was hard)
- [x] Personalized weekly meal plan generation
- [x] In-Telegram dashboard (/dashboard) with matplotlib charts
- [x] Onboarding flow (/start) captures name, food preferences, allergies
- [x] Commands: /start /help /weight /mealplan /dashboard /today /profile /review

## Planned Future Phases
- Phase 2: Workout & gym tracking
- Phase 3: Mental health / mood journaling
- Phase 4: Habit tracking
- Phase 5: Sleep tracking

## Key Files
- `main.py` — entry point, webhook/polling mode switching
- `config.py` — all constants, meal times, calorie goals
- `database.py` — all DB operations (Supabase PostgreSQL + SQLite)
- `llm.py` — all Groq API calls (text + vision)
- `scheduler.py` — APScheduler jobs for reminders
- `handlers/commands.py` — all slash commands
- `handlers/photo_handler.py` — food photo → calorie analysis
- `handlers/message_handler.py` — text message routing
- `handlers/weekly_review.py` — ConversationHandler for weekly review
- `dashboard/app.py` — Streamlit dashboard

## Deployment Workflow (how to make changes)
1. Edit code locally
2. `git add . && git commit -m "description" && git push`
3. Render auto-deploys within ~2 minutes
4. No manual steps on Render needed

## Known Platform Limitations
- HuggingFace Spaces FREE tier blocks outbound connections to Telegram API — DO NOT use HF Spaces for this bot
- Fly.io requires $9 unlock for Indian accounts — not used
- Koyeb/Render background workers require paid plan — using Render Web Service (free) instead

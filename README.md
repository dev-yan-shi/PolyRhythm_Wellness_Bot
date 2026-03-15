---
title: PolyRhythm Wellness Bot
emoji: 🥁
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# 🥁 PolyRhythm — AI Wellness Coach

> *"Managing the different rhythms of your life — physical, mental, nutritional, and beyond."*

PolyRhythm is a fully free, self-hosted AI wellness coach that lives in your Telegram.
Built for people who want a personalised, always-on health companion — without subscriptions or data sharing.

Powered by **Groq (Llama 4 Scout)** for food image analysis and **Llama 3.3 70B** for coaching.

---

## ✨ Phase 1 Features — Health & Nutrition Coach

| Feature | Description |
|---|---|
| 📸 Food photo logging | Send a meal photo (with optional caption) → instant calorie + macro breakdown |
| 📝 Caption-aware analysis | Describe a custom dish (e.g. *"chickpea flour vegetable waffle"*) → nutrition based on your exact ingredients |
| 🔥 Calorie tracking | Daily totals tracked against your personal goal |
| ⚖️ Weekly weigh-in | Sunday morning reminder + full weight history |
| 📋 Weekly meal plans | Auto-generated every Sunday based on your preferences & history |
| 🔄 Weekly review | Guided Sunday reflection → personalised feedback + adjusted next week's plan |
| 📊 In-chat dashboard | `/dashboard` sends weight trend + calorie history charts directly in Telegram |
| ⏰ Smart reminders | Proactive meal-time messages with calorie-remaining context |

---

## 🚀 Quick Setup (15 minutes)

### 1. Fork this repo
Click **Fork** on GitHub — you get your own fully independent copy.

### 2. Get your free API keys

**Groq API key** (for the AI brain)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up → **API Keys** → **Create API Key**
3. Copy the key

**Telegram Bot Token** (for the chat interface)
1. Open Telegram, search **@BotFather**
2. Send `/newbot` → choose a name and username (must end in `bot`)
3. Copy the token BotFather sends you

### 3. Deploy to Render (free, 24/7)

1. Go to [render.com](https://render.com) → sign up with GitHub
2. Click **New → Background Worker**
3. Connect your forked `PolyRhythm_Wellness_Bot` repo
4. Render auto-detects `render.yaml` → click **Apply**
5. Go to **Environment** tab → add:

   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | your Groq key |
   | `TELEGRAM_BOT_TOKEN` | your Telegram bot token |

6. Click **Deploy** — PolyRhythm is live 24/7 🎉

### 4. Start the bot
Open Telegram, find your bot, send `/start` and follow the onboarding.

---

## 💻 Local Development

```bash
git clone https://github.com/YOUR_USERNAME/PolyRhythm_Wellness_Bot
cd PolyRhythm_Wellness_Bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # edit .env and add your keys
python main.py
```

---

## ⚙️ Personalisation (config.py)

| Setting | Default | Description |
|---|---|---|
| `CALORIE_GOAL_TARGET` | 1150 kcal | Your daily calorie target |
| `TIMEZONE` | Asia/Kolkata (IST) | Your timezone |
| `MEAL_TIMES` | 9:30 / 13:00 / 17:00 / 21:00 | Reminder times (IST) |
| `WEIGHT_CHECKIN_TIME` | Sunday 8:00 AM | Weekly weigh-in reminder |
| `WEEKLY_REVIEW_TIME` | Sunday 8:00 PM | Weekly reflection prompt |

---

## 📱 Commands

| Command | What it does |
|---|---|
| `/start` | Onboarding — set your name, food preferences, allergies |
| `/today` | Today's calorie summary |
| `/weight 65.5` | Log your weight in kg |
| `/mealplan` | Get this week's meal plan |
| `/dashboard` | View charts: weight trend + calorie history |
| `/summary` | Weekly stats |
| `/review` | Start the weekly reflection chat |
| `/help` | Show all commands |

---

## 🏗️ Tech Stack

| Component | Technology | Cost |
|---|---|---|
| Bot platform | Telegram Bot API | Free |
| Text LLM | Groq — Llama 3.3 70B | Free tier |
| Vision LLM | Groq — Llama 4 Scout 17B | Free tier |
| Database | SQLite (persistent disk) | Free |
| Hosting | Render Background Worker | Free |
| Language | Python 3.12 | Free |

**Total running cost: $0**

---

## 🔒 Security & Privacy

- Your `.env` file is **gitignored** — never committed to the repo
- On Render, secrets are stored as **environment variables** in their secure dashboard — never in code
- The bot only responds to users who have run `/start` (all data scoped to your chat ID)
- Fork this repo to get a completely independent deployment — your data never touches anyone else's server

---

## 📁 Project Structure

```
PolyRhythm_Wellness_Bot/
├── main.py                 # Entry point
├── config.py               # All settings — edit to personalise
├── database.py             # SQLite operations
├── llm.py                  # Groq API calls (text + vision)
├── scheduler.py            # Meal reminders & weekly jobs
├── handlers/
│   ├── commands.py         # /start, /weight, /dashboard etc.
│   ├── photo_handler.py    # Food photo → calorie analysis
│   ├── message_handler.py  # Text messages & calorie corrections
│   └── weekly_review.py    # Sunday reflection flow
├── dashboard/
│   └── app.py              # Streamlit dashboard (optional web view)
├── render.yaml             # One-click Render deployment config
├── requirements.txt
└── .env.example            # Copy to .env and fill in your keys
```

---

## 🗺️ Roadmap

- [x] Phase 1 — Health & Nutrition Coach
- [ ] Phase 2 — Workout & Gym Tracker
- [ ] Phase 3 — Habit Tracking & Streaks
- [ ] Phase 4 — Mental Wellness & Journaling
- [ ] Phase 5 — Unified PolyRhythm Dashboard

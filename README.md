# 🥗 AI Personal Life Coach — Telegram Bot

A fully free, self-hosted AI health & nutrition coach that lives in your Telegram.
Powered by **Groq (Llama 4 Scout)** for food image analysis and **Llama 3.3 70B** for coaching.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📸 Food photo logging | Send a meal photo (with optional caption) → get instant calorie + macro breakdown |
| 🔥 Calorie tracking | Daily totals tracked against your personal goal |
| ⚖️ Weekly weigh-in | Sunday morning reminder + weight history |
| 📋 Weekly meal plans | Auto-generated every Sunday based on your preferences & history |
| 🔄 Weekly review | Guided Sunday reflection → personalised feedback + adjusted plan |
| 📊 Dashboard | `/dashboard` sends weight + calorie charts directly in Telegram |
| ⏰ Smart reminders | Proactive meal-time messages with calorie-remaining context |

---

## 🚀 Quick Setup (15 minutes)

### 1. Fork this repo
Click **Fork** on GitHub so you have your own copy.

### 2. Get your API keys (both free)

**Groq API key**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up → **API Keys** → **Create API Key**
3. Copy the key

**Telegram Bot Token**
1. Open Telegram, search **@BotFather**
2. Send `/newbot` → follow prompts
3. Copy the token BotFather gives you

### 3. Deploy to Render (free, 24/7)

1. Go to [render.com](https://render.com) → sign up with GitHub
2. Click **New → Background Worker**
3. Connect your forked GitHub repo
4. Render auto-detects `render.yaml` — click **Apply**
5. Go to **Environment** tab → add two variables:

   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | your Groq key |
   | `TELEGRAM_BOT_TOKEN` | your Telegram bot token |

6. Click **Deploy** — your bot is live 24/7 🎉

### 4. Start the bot
Open Telegram, find your bot, send `/start` and follow the onboarding.

---

## 💻 Local Development

```bash
git clone https://github.com/YOUR_USERNAME/life-coach-bot
cd life-coach-bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # then edit .env with your keys
python main.py
```

---

## ⚙️ Personalisation (config.py)

| Setting | Default | Description |
|---|---|---|
| `CALORIE_GOAL_TARGET` | 1150 kcal | Your daily calorie target |
| `TIMEZONE` | Asia/Kolkata (IST) | Your timezone |
| `MEAL_TIMES` | 9:30 / 13:00 / 17:00 / 21:00 | Reminder times |
| `WEIGHT_CHECKIN_TIME` | Sunday 8:00 AM | Weekly weigh-in reminder |
| `WEEKLY_REVIEW_TIME` | Sunday 8:00 PM | Weekly reflection prompt |

---

## 📱 Commands

| Command | What it does |
|---|---|
| `/start` | Onboarding — set your name, food preferences, allergies |
| `/today` | Today's calorie summary |
| `/weight 65.5` | Log your weight |
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

---

## 🔒 Security

- Your `.env` file is **gitignored** — never committed
- On Render, secrets are stored as **environment variables** in their dashboard
- The bot only responds to users who have run `/start` (stored in DB)
- Fork this repo to get your own completely independent deployment

---

## 📁 Project Structure

```
life-coach-bot/
├── main.py                 # Entry point
├── config.py               # All settings (edit this to personalise)
├── database.py             # SQLite operations
├── llm.py                  # Groq API calls (text + vision)
├── scheduler.py            # Meal reminders & weekly jobs
├── handlers/
│   ├── commands.py         # /start, /weight, /dashboard etc.
│   ├── photo_handler.py    # Food photo → calorie analysis
│   ├── message_handler.py  # Text messages & calorie corrections
│   └── weekly_review.py    # Sunday reflection flow
├── dashboard/
│   └── app.py              # Streamlit dashboard (optional)
├── render.yaml             # Render deployment config
├── requirements.txt
└── .env.example            # Copy to .env and fill in your keys
```

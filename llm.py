"""
All Groq LLM interactions — text generation and vision (food analysis).
"""
import base64
import json
import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_TEXT_MODEL, GROQ_VISION_MODEL, CALORIE_GOAL_TARGET

logger = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chat(messages: list, model: str = None, temperature: float = 0.7) -> str:
    model = model or GROQ_TEXT_MODEL
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "I'm having trouble connecting right now. Please try again in a moment."


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ── Food Image Analysis ───────────────────────────────────────────────────────

def analyze_food_image(image_path: str, meal_type: str,
                       today_calories_so_far: int = 0,
                       user_caption: str = "") -> dict:
    """
    Analyze a food photo. Returns dict:
        description, calories, protein_g, carbs_g, fat_g,
        encouragement, items (list)
    user_caption: text the user typed alongside the photo — treated as ground truth.
    """
    remaining = CALORIE_GOAL_TARGET - today_calories_so_far
    b64 = _encode_image(image_path)

    # If the user described their food, make that the primary source of truth
    caption_block = ""
    if user_caption.strip():
        caption_block = f"""
⚠️ IMPORTANT — The user has described their meal in their own words:
\"{user_caption.strip()}\"
This description is ground truth. Trust it completely over what you visually infer.
Use the image only to estimate portion sizes and confirm ingredients.
If the user describes a custom or improvised dish (e.g. "chickpea flour vegetable waffle"),
calculate nutrition based on that specific description, not a generic visual guess.
"""

    prompt = f"""You are a professional nutritionist. Your ONLY job right now is to output a single JSON object — nothing else.
Do NOT write any explanation, headings, markdown, or prose. Output raw JSON only.

Context:
- User's daily calorie target: {CALORIE_GOAL_TARGET} kcal
- Consumed so far today: {today_calories_so_far} kcal ({remaining} kcal remaining)
- Meal type: {meal_type}
{caption_block}
Required JSON format (fill in all values, no placeholders):
{{"items": ["item1 with portion size", "item2 with portion size"], "description": "short meal description", "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "encouragement": "short warm message"}}

Rules:
- Be precise with Indian foods (dal, roti, rice, sabzi, besan, etc.)
- If the user described a custom dish, base nutrition on their exact description
- Lean slightly conservative on calories
- Output ONLY the JSON object. No text before or after it."""

    try:
        resp = client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }],
            temperature=0.3,
            max_tokens=512,
        )
        raw = resp.choices[0].message.content.strip()
        logger.info(f"Vision raw response: {raw[:200]}")

        # Strip markdown code fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        # Extract JSON object even if surrounded by text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.warning(f"Vision model returned non-JSON: {e}\nRaw: {raw[:300]}")
        return {
            "items": ["Could not parse food items"],
            "description": "Meal (manual entry needed)",
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "encouragement": "I had trouble reading the response. Please reply with the calorie count manually.",
            "_error": f"JSON parse error: {e}"
        }
    except Exception as e:
        logger.error(f"Vision API error ({type(e).__name__}): {e}")
        return {
            "items": [],
            "description": "Analysis failed",
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "encouragement": f"Vision API error: {type(e).__name__}: {str(e)[:100]}",
            "_error": str(e)
        }


# ── Meal Plan Generation ──────────────────────────────────────────────────────

def generate_meal_plan(food_prefs: str, allergies: str,
                       last_week_meals: list, week_start: str) -> str:
    meal_history = "\n".join(
        [f"- {m['date']} {m['meal_type']}: {m['description']} ({m['calories']} kcal)"
         for m in (last_week_meals or [])[-20:]]
    ) or "No history yet"

    prompt = f"""You are a professional Indian nutritionist creating a weekly meal plan.

USER PROFILE:
- Daily calorie target: {CALORIE_GOAL_TARGET} kcal (range: 1100–1200 kcal)
- Food preferences: {food_prefs or 'Indian cuisine, Bangalore-based'}
- Allergies/restrictions: {allergies or 'None mentioned'}
- Last week's meals (for variety): {meal_history}

Create a 7-day meal plan for the week starting {week_start}.
Each day should have: Breakfast (~200-250 kcal), Lunch (~350-400 kcal), Evening Snack (~100-150 kcal), Dinner (~350-400 kcal).
Total per day: 1100-1200 kcal.

Format EXACTLY like this (use emojis, keep it readable on mobile):
━━━━━━━━━━━━━━━━━━━━━━
📅 WEEK PLAN: {week_start}
Target: 1100-1200 kcal/day
━━━━━━━━━━━━━━━━━━━━━━

🗓 MONDAY
🌅 Breakfast (X kcal): [meal]
☀️ Lunch (X kcal): [meal]
🍎 Snack (X kcal): [meal]
🌙 Dinner (X kcal): [meal]
📊 Daily Total: X kcal

[repeat for each day]

💡 Tips for the week:
• [tip 1]
• [tip 2]
• [tip 3]

Keep meals practical, Indian, and delicious. Use commonly available ingredients in Bangalore."""

    return _chat([{"role": "user", "content": prompt}], temperature=0.8)


# ── Weekly Feedback ───────────────────────────────────────────────────────────

def generate_weekly_feedback(weight_history: list, daily_calories: list,
                              went_well: str, went_hard: str,
                              extra_notes: str, food_prefs: str) -> str:
    weight_str = "\n".join([f"- {d}: {w} kg" for d, w in (weight_history or [])])
    cal_str = "\n".join([f"- {d}: {c} kcal" for d, c in (daily_calories or [])])

    prompt = f"""You are a warm, encouraging personal health coach giving a weekly review.

WEEK'S DATA:
Weight history:
{weight_str or 'No weight data this week'}

Daily calorie intake:
{cal_str or 'No calorie data this week'}

User's self-reflection:
- What went well: "{went_well}"
- What was challenging: "{went_hard}"
- Additional notes: "{extra_notes or 'None'}"

User profile: {food_prefs or 'Indian cuisine, 1100-1200 kcal/day goal'}

Write a warm, motivating weekly review message. Include:
1. 🏆 What they did great this week (specific)
2. 📈 Progress observation (weight trend, calorie consistency)
3. 💪 One key area to focus on next week
4. 🎯 Personalized tip for their challenge
5. 🌟 An encouraging closing message

Keep it personal, warm, under 300 words, formatted for mobile (use emojis and short paragraphs)."""

    return _chat([{"role": "user", "content": prompt}], temperature=0.75)


# ── Meal Reminders ────────────────────────────────────────────────────────────

def generate_meal_reminder(meal_type: str, today_calories: int) -> str:
    remaining = CALORIE_GOAL_TARGET - today_calories
    prompts = {
        "breakfast": f"Write a short, warm morning greeting and breakfast reminder. Today's calorie budget: {CALORIE_GOAL_TARGET} kcal. Keep it under 3 sentences, friendly, use 1-2 emojis.",
        "lunch":     f"Write a short friendly lunch reminder. They've had {today_calories} kcal so far ({remaining} kcal remaining). Suggest they share a photo. Under 3 sentences, 1-2 emojis.",
        "snack":     f"Write a short afternoon snack reminder. They've had {today_calories} kcal so far ({remaining} kcal remaining for rest of day). Suggest a light healthy snack. Under 3 sentences.",
        "dinner":    f"Write a short dinner reminder. They've had {today_calories} kcal today ({remaining} kcal remaining). Encourage mindful eating. Under 3 sentences, warm tone.",
    }
    return _chat([{"role": "user", "content": prompts[meal_type]}], temperature=0.9)


# ── General Coach Chat ────────────────────────────────────────────────────────

def coach_reply(user_message: str, today_meals: list, food_prefs: str) -> str:
    meal_summary = ", ".join([f"{m['meal_type']}: {m['description']} ({m['calories']} kcal)"
                               for m in today_meals]) or "nothing logged yet"

    system = f"""You are a warm, knowledgeable personal health and nutrition coach.
The user's daily calorie goal is 1100-1200 kcal. They follow Indian cuisine primarily.
Today they've eaten: {meal_summary}.
Their preferences: {food_prefs or 'Indian cuisine, Bangalore-based'}.
Be encouraging, specific, and concise. Use 1-2 emojis max. Keep responses under 150 words."""

    return _chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user_message}
    ], temperature=0.8)


# ── Weight Feedback ───────────────────────────────────────────────────────────

def generate_weight_feedback(current_kg: float, previous: tuple) -> str:
    if not previous:
        return f"Weight logged: *{current_kg} kg* ✅ Great start tracking! Consistency is key."

    prev_date, prev_kg = previous
    diff = round(current_kg - prev_kg, 1)
    direction = "lost" if diff < 0 else "gained" if diff > 0 else "maintained"
    abs_diff = abs(diff)

    prompt = f"""User logged their weight: {current_kg} kg.
Previous weight ({prev_date}): {prev_kg} kg.
Change: {direction} {abs_diff} kg.
Goal context: They're targeting 1100-1200 kcal/day for weight management.

Write a brief (2-3 sentence) warm, encouraging response acknowledging their weigh-in.
Be realistic and supportive regardless of whether they gained, lost, or maintained.
Use 1-2 emojis. Include the numbers clearly."""

    return _chat([{"role": "user", "content": prompt}], temperature=0.7)

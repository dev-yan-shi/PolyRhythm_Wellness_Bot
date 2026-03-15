"""
Streamlit dashboard — host separately on Streamlit Community Cloud.
Connect to the same life_coach.db file.
"""
import sqlite3
import os
from datetime import date, timedelta, datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "../life_coach.db")
CALORIE_MIN = 1100
CALORIE_MAX = 1200

st.set_page_config(
    page_title="Life Coach Dashboard",
    page_icon="💪",
    layout="wide",
)


@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def query(sql, params=()):
    conn = get_conn()
    return pd.read_sql_query(sql, conn, params=params)


# ── Load data ─────────────────────────────────────────────────────────────────

def load_data():
    try:
        weight_df = query("""
            SELECT date, weight_kg FROM weight_log ORDER BY date
        """)
        meals_df = query("""
            SELECT date, meal_type, description, calories_final as calories,
                   protein_g, carbs_g, fat_g
            FROM meal_log ORDER BY date, created_at
        """)
        reviews_df = query("""
            SELECT week_start, went_well, went_hard, bot_feedback FROM weekly_review ORDER BY week_start DESC
        """)
        return weight_df, meals_df, reviews_df
    except Exception as e:
        st.error(f"Database error: {e}. Make sure DB_PATH points to your life_coach.db file.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# ── Main App ──────────────────────────────────────────────────────────────────

def main():
    st.title("💪 Life Coach — Personal Health Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

    weight_df, meals_df, reviews_df = load_data()

    if weight_df.empty and meals_df.empty:
        st.info("No data yet! Start logging meals and weight in the Telegram bot to see your dashboard.")
        return

    # ── Top KPIs ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if not weight_df.empty:
            latest_w = weight_df.iloc[-1]["weight_kg"]
            prev_w = weight_df.iloc[-2]["weight_kg"] if len(weight_df) > 1 else latest_w
            delta = round(latest_w - prev_w, 1)
            st.metric("⚖️ Latest Weight", f"{latest_w} kg", f"{delta:+.1f} kg")
        else:
            st.metric("⚖️ Latest Weight", "—")

    with col2:
        if not meals_df.empty:
            today_str = date.today().isoformat()
            today_cal = meals_df[meals_df["date"] == today_str]["calories"].sum()
            st.metric("🔥 Today's Calories", f"{int(today_cal)} kcal", f"Goal: {CALORIE_MAX}")
        else:
            st.metric("🔥 Today's Calories", "—")

    with col3:
        if not meals_df.empty:
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            week_meals = meals_df[meals_df["date"] >= week_ago]
            days_logged = week_meals["date"].nunique()
            st.metric("✅ Week Consistency", f"{days_logged}/7 days", f"{round(days_logged/7*100)}%")
        else:
            st.metric("✅ Week Consistency", "—")

    with col4:
        if not meals_df.empty:
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            avg_cal = meals_df[meals_df["date"] >= week_ago].groupby("date")["calories"].sum().mean()
            st.metric("📊 Avg Daily Calories", f"{int(avg_cal or 0)} kcal" if avg_cal else "—")
        else:
            st.metric("📊 Avg Daily Calories", "—")

    st.divider()

    # ── Weight History ────────────────────────────────────────────────────────
    st.subheader("⚖️ Weight History")
    if not weight_df.empty:
        weight_df["date"] = pd.to_datetime(weight_df["date"])
        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(
            x=weight_df["date"], y=weight_df["weight_kg"],
            mode="lines+markers", name="Weight",
            line=dict(color="#00d4aa", width=2),
            marker=dict(size=7)
        ))
        fig_w.update_layout(
            yaxis_title="Weight (kg)", xaxis_title="Date",
            template="plotly_dark", height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_w, use_container_width=True)
    else:
        st.info("No weight entries yet. Use `/weight 65.5` in the bot.")

    # ── Calorie History ───────────────────────────────────────────────────────
    st.subheader("🔥 Daily Calorie Intake (last 30 days)")
    if not meals_df.empty:
        thirty_ago = (date.today() - timedelta(days=30)).isoformat()
        cal_daily = (
            meals_df[meals_df["date"] >= thirty_ago]
            .groupby("date")["calories"].sum().reset_index()
        )
        cal_daily["date"] = pd.to_datetime(cal_daily["date"])
        cal_daily["color"] = cal_daily["calories"].apply(
            lambda c: "#00d4aa" if CALORIE_MIN <= c <= CALORIE_MAX else
                      ("#ffd700" if c < CALORIE_MIN else "#ff6b6b")
        )
        fig_c = go.Figure()
        fig_c.add_trace(go.Bar(
            x=cal_daily["date"], y=cal_daily["calories"],
            marker_color=cal_daily["color"], name="Calories"
        ))
        fig_c.add_hline(y=CALORIE_MIN, line_dash="dash", line_color="#ffd700",
                        annotation_text=f"Min {CALORIE_MIN}")
        fig_c.add_hline(y=CALORIE_MAX, line_dash="dash", line_color="#ff6b6b",
                        annotation_text=f"Max {CALORIE_MAX}")
        fig_c.update_layout(
            yaxis_title="Calories (kcal)", xaxis_title="Date",
            template="plotly_dark", height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_c, use_container_width=True)
        st.caption("🟢 On target  |  🟡 Under  |  🔴 Over")

    st.divider()

    # ── Meal Log ──────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🍽 Recent Meal Log")
        if not meals_df.empty:
            recent = meals_df.sort_values("date", ascending=False).head(30)
            recent["date"] = pd.to_datetime(recent["date"]).dt.strftime("%d %b")
            st.dataframe(
                recent[["date", "meal_type", "description", "calories"]],
                hide_index=True, use_container_width=True,
                column_config={
                    "date": "Date",
                    "meal_type": "Meal",
                    "description": "Food",
                    "calories": st.column_config.NumberColumn("kcal", format="%d"),
                }
            )

    with col_right:
        st.subheader("🥗 Macros Breakdown (last 7 days)")
        if not meals_df.empty:
            week_ago = (date.today() - timedelta(days=7)).isoformat()
            macro_data = meals_df[meals_df["date"] >= week_ago][["protein_g", "carbs_g", "fat_g"]].sum()
            if macro_data.sum() > 0:
                fig_pie = px.pie(
                    values=macro_data.values,
                    names=["Protein", "Carbs", "Fat"],
                    color_discrete_sequence=["#00d4aa", "#ffd700", "#ff6b6b"],
                    template="plotly_dark",
                    hole=0.4,
                )
                fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # ── Weekly Reviews ────────────────────────────────────────────────────────
    st.subheader("🔄 Weekly Reviews")
    if not reviews_df.empty:
        for _, row in reviews_df.iterrows():
            with st.expander(f"Week of {row['week_start']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**What went well:**")
                    st.write(row["went_well"] or "—")
                with col_b:
                    st.write("**What was challenging:**")
                    st.write(row["went_hard"] or "—")
                st.write("**Coach feedback:**")
                st.write(row["bot_feedback"] or "—")
    else:
        st.info("No weekly reviews yet. Complete your first review with /review in the bot.")


if __name__ == "__main__":
    main()

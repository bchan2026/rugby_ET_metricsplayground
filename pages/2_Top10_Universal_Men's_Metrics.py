import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# LOWER IS BETTER METRICS
# ---------------------------------------------------------
LOWER_IS_BETTER = [
    "Penalty Conceded",
    "Penalty Conceded - Scrum",
    "Turnover Conceded",
    "Yellow Card",
    "Red Card",
]

from utils import (
    load_and_merge_players,
    load_descriptors,
)

# ---------------------------------------------------------
# Page Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="Top 10 Universal Metrics – Ealing Recruitment Tool",
    layout="wide",
)

# ---------------------------------------------------------
# Global Styling
# ---------------------------------------------------------
st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Garamond', serif;
    font-weight: 700;
    color: #000000;
}

.metric-card {
    background: white;
    border-radius: 12px;
    padding: 0;
    border: 1px solid rgba(0,0,0,0.15);
    box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
    margin-bottom: 25px;
}

.metric-header {
    background: linear-gradient(90deg, #B30000, #CC0000);
    padding: 12px 18px;
    border-radius: 12px 12px 0 0;
    color: white;
    font-size: 26px;
    font-weight: 700;
    text-align: left;
}

.metric-body {
    padding: 15px 20px;
    font-size: 18px;
    line-height: 1.4;
}

.metric-row {
    display: grid;
    grid-template-columns: 1fr 20px 90px;
    padding: 4px 0;
    border-bottom: 1px solid #eee;
}

.metric-row:last-child {
    border-bottom: none;
}

.metric-name {
    text-align: left;
}

.metric-bar {
    text-align: center;
}

.metric-value {
    text-align: right;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Load Data
# ---------------------------------------------------------
@st.cache_data
def get_data():
    players = load_and_merge_players("data/men")
    descriptors = load_descriptors("config/descriptors.yaml")
    return players, descriptors

players, descriptors = get_data()

# ---------------------------------------------------------
# Universal Metrics
# ---------------------------------------------------------
universal_metrics = [
    "Minutes Played",
    "Points",
    "Dominant Carries",
    "Ball Carries",
    "Post Contact Metres",
    "Line Breaks",
    "Defenders Beaten",
    "Offloads",
    "Passes - Total Pass Attempts (including Offloads)",
    "Try Assists - Total",
    "Tackles Made",
    "Breakdown Steals",
    "Turnover Won",
    "Pass Outcome - Break",
    "Successful Tackles %",
]

# ---------------------------------------------------------
# Position-Specific Metrics
# ---------------------------------------------------------
position_metrics = {
    "Number 8": [
        "Dominant Tackles",
        "Jackals Attempted",
        "Lineout Takes",
        "Yellow Card",
        "Att OOA - 1st Own Team",
        "Att OOA - 2nd Own Team",
    ],
    "Prop": [
        "Dominant Tackles",
        "Penalty Conceded - Scrum",
        "Jackals Attempted",
        "Att OOA - 1st Own Team",
        "Att OOA - 2nd Own Team",
        "Ruck Arrival - Def. Intention - Jackal",
        "Ruck Arrival - Def. Intention - Counter-Ruck",
    ],
    "Scrum Half": [
        "Kicks",
        "Kicking Metres",
        "Kick Outcome - 50/22",
    ],
    "Right Centre": ["Dominant Tackles"],
    "Lock": [
        "Dominant Tackles",
        "Jackals Attempted",
        "Lineout Steals",
        "Lineout Takes",
        "Catch From Kick - Success",
        "Att OOA - 1st Own Team",
        "Att OOA - 2nd Own Team",
        "Ruck Arrival - Def. Intention - Jackal",
        "Ruck Arrival - Def. Intention - Counter-Ruck",
    ],
    "Hooker": [
        "Dominant Tackles",
        "Jackals Attempted",
        "Yellow Card",
        "Own Lineouts Won %",
        "Ruck Arrival - Def. Intention - Jackal",
        "Ruck Arrival - Def. Intention - Counter-Ruck",
    ],
    "Flanker": [
        "Dominant Tackles",
        "Jackals Attempted",
        "Lineout Takes",
        "Yellow Card",
        "Att OOA - 1st Own Team",
        "Att OOA - 2nd Own Team",
        "Ruck Arrival - Def. Intention - Jackal",
        "Ruck Arrival - Def. Intention - Counter-Ruck",
    ],
    "Outside Half": [
        "All Goals %",
        "Kicks",
        "Kicking Metres",
        "Kick Outcome - 50/22",
    ],
    "Left Centre": ["Dominant Tackles"],
    "Full Back": [
        "All Goals %",
        "Kicks",
        "Kicking Metres",
        "Kick Outcome - 50/22",
    ],
    "Left Wing": [
        "Kicks",
        "Kicking Metres",
        "Catch From Kick - Success",
    ],
    "Right Wing": [
        "Kicks",
        "Kicking Metres",
        "Catch From Kick - Success",
    ],
}

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown("<h1 style='font-size:42px;'>Top 10 – Universal & Position Metrics (Per Game)</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# League Filter
# ---------------------------------------------------------
st.subheader("🏆 League Filter")

df = players.copy()
df["Games Played"] = pd.to_numeric(df["Games Played"], errors="coerce").fillna(0)

leagues = sorted(df["league"].dropna().unique())
league_choice = st.selectbox("League", ["All leagues"] + leagues, key="top10_league")

if league_choice != "All leagues":
    df = df[df["league"] == league_choice]

# Only players with 6+ games
df = df[df["Games Played"] >= 6]

# ---------------------------------------------------------
# Metrics that should NOT be per-game
# ---------------------------------------------------------
percentage_metrics = [
    "Successful Tackles %",
    "All Goals %",
    "Own Lineouts Won %",
]

success_metrics = []  # Catch From Kick stays raw

raw_metrics = percentage_metrics + success_metrics

# ---------------------------------------------------------
# Convert metrics
# ---------------------------------------------------------
for m in universal_metrics + sum(position_metrics.values(), []):
    if m not in df.columns:
        continue

    df[m] = pd.to_numeric(df[m], errors="coerce")

    if m in raw_metrics:
        df[m + " (Value)"] = df[m]
    else:
        df[m + " (Value)"] = df.apply(
            lambda row: row[m] / row["Games Played"] if row["Games Played"] > 0 else np.nan,
            axis=1
        )

# ---------------------------------------------------------
# Build Top 10
# ---------------------------------------------------------
def build_top10(group_df: pd.DataFrame, metrics: list):
    results = {}
    for metric in metrics:
        col = metric + " (Value)"
        if col not in group_df.columns:
            continue

        metric_df = group_df[["player", col]].dropna()
        if metric_df.empty:
            continue

        # FIXED: direction-aware sorting
        ascending_order = metric in LOWER_IS_BETTER
        metric_df = metric_df.sort_values(col, ascending=ascending_order)

        results[metric] = metric_df.head(10)

    return results

# ---------------------------------------------------------
# Top 10 per Position
# ---------------------------------------------------------
st.subheader("🧩 Top 10 per Position")

positions = sorted(df["position"].dropna().unique())
selected_position = st.selectbox("Position", positions, key="top10_position")

metrics_for_position = list(dict.fromkeys(
    universal_metrics + position_metrics.get(selected_position, [])
))

pos_df = df[df["position"] == selected_position]
pos_top10 = build_top10(pos_df, metrics_for_position)

# ---------------------------------------------------------
# Display Cards
# ---------------------------------------------------------
cols_per_row = 3
metrics_list = list(pos_top10.keys())
rows = [metrics_list[i:i + cols_per_row] for i in range(0, len(metrics_list), cols_per_row)]

for row in rows:
    cols = st.columns(len(row))
    for idx, metric in enumerate(row):
        with cols[idx]:
            top10 = pos_top10[metric]

            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='metric-header'>{metric} – {selected_position}</div>",
                unsafe_allow_html=True
            )
            st.markdown("<div class='metric-body'>", unsafe_allow_html=True)

            for _, r in top10.iterrows():
                player = r["player"]
                value = r[metric + " (Value)"]

                if metric in percentage_metrics:
                    try:
                        pct = float(value)
                        value_str = f"{int(round(pct * 100))}%"
                    except:
                        value_str = ""
                else:
                    if isinstance(value, float):
                        value_str = f"{value:.2f}".rstrip("0").rstrip(".")
                    else:
                        value_str = str(value)

                st.markdown(
                    f"""
                    <div class='metric-row'>
                        <div class='metric-name'>{player}</div>
                        <div class='metric-bar'>|</div>
                        <div class='metric-value'>{value_str}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("</div></div>", unsafe_allow_html=True)

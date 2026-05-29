import streamlit as st
import pandas as pd
import os
import math

from utils import (
    load_and_merge_players,
    load_descriptors,
    get_metrics_for_position,
)

# ---------------------------------------------------------
# Page + Theme
# ---------------------------------------------------------

st.set_page_config(
    page_title="Player Profiles – Ealing Recruitment Tool",
    layout="wide",
)

st.markdown("""
<style>

html, body, [class*="css"]  {
    font-family: 'Garamond', serif;
    font-weight: 700;
    color: #000000;
}

:root {
    --primary: #00FFFF;
    --bg-dark: #FFFFFF;
    --bg-card: #F5F5F5;
    --text-light: #000000;
}

body {
    background-color: var(--bg-dark);
    color: var(--text-light);
}

section.main > div {
    background: var(--bg-dark);
}

.block-container {
    padding-top: 1.5rem;
}

.neon-card {
    background: var(--bg-card);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid rgba(0, 0, 0, 0.15);
}

h1.neon-title {
    text-align: center;
    letter-spacing: 1px;
}

[data-testid="stMetricValue"] {
    color: black !important;
    font-weight: 700;
}

div[data-testid="stMetricLabel"] {
    color: #333333;
}

hr {
    border: 1px solid rgba(0,0,0,0.15);
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------

def format_number(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        v = float(value)
        if v.is_integer():
            return str(int(v))
        return f"{v:.1f}"
    except:
        return str(value)


def format_percentage(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        v = float(value)
        if v > 1:
            v = v / 100.0
        pct = v * 100.0
        if pct.is_integer():
            return f"{int(pct)}%"
        return f"{pct:.1f}%"
    except:
        return ""


def is_percentage_metric(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    return "%" in n or "percent" in n or "rate" in n

# ---------------------------------------------------------
# Load Data
# ---------------------------------------------------------

@st.cache_data
def get_data():
    players = load_and_merge_players("data/men")
    descriptors = load_descriptors("config/descriptors.yaml")
    return players, descriptors

players, descriptors = get_data()

if players.empty:
    st.error("No player data loaded. Add Excel files to /data.")
    st.stop()

universal_metrics = descriptors.get("universal_metrics", [])

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

col_logo_left, col_title, col_logo_right = st.columns([1, 5, 1])

logo_left_path = "images/Ealing_Trailfinders_logo.jpg"
logo_right_path = "images/Stats_Perform_logo.jpg"

with col_logo_left:
    if os.path.exists(logo_left_path):
        st.image(logo_left_path, width=120)

with col_title:
    st.markdown(
        "<h1 class='neon-title' style='font-size:48px; text-align:center;'>TRAILFINDERS OPTA RECRUITMENT TOOL</h1>",
        unsafe_allow_html=True,
    )

with col_logo_right:
    if os.path.exists(logo_right_path):
        st.image(logo_right_path, width=120)

st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# FILTERS — NON-RESETTING
# ---------------------------------------------------------

with st.container():
    st.markdown("<div class='neon-card'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    leagues = sorted(players["league"].dropna().unique())
    league_choice = c1.selectbox("League", ["All leagues"] + leagues)

    if league_choice == "All leagues":
        teams = sorted(players["team"].dropna().unique())
    else:
        teams = sorted(players[players["league"] == league_choice]["team"].dropna().unique())

    team_choice = c2.selectbox("Team", ["All teams"] + teams)

    filtered_for_positions = players.copy()
    if league_choice != "All leagues":
        filtered_for_positions = filtered_for_positions[filtered_for_positions["league"] == league_choice]
    if team_choice != "All teams":
        filtered_for_positions = filtered_for_positions[filtered_for_positions["team"] == team_choice]

    positions = sorted(filtered_for_positions["position"].dropna().unique())
    pos_choice = c3.selectbox("Position", ["All positions"] + positions)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PLAYER SELECTION — ALWAYS FROM FULL DATASET
# ---------------------------------------------------------

st.subheader("🎯 Select Players")

filtered_players = players.copy()

if league_choice != "All leagues":
    filtered_players = filtered_players[filtered_players["league"] == league_choice]

if team_choice != "All teams":
    filtered_players = filtered_players[filtered_players["team"] == team_choice]

if pos_choice != "All positions":
    filtered_players = filtered_players[filtered_players["position"] == pos_choice]

dropdown_options = sorted(filtered_players["player"].dropna().unique())

if "selected_players" not in st.session_state:
    st.session_state.selected_players = []

cols = st.columns(5)
new_selections = []

for i in range(5):
    default_value = st.session_state.selected_players[i] if i < len(st.session_state.selected_players) else "None"
    pick = cols[i].selectbox(
        f"Player {i+1}",
        ["None"] + dropdown_options,
        index=(["None"] + dropdown_options).index(default_value) if default_value in (["None"] + dropdown_options) else 0,
        key=f"player_pick_{i}"
    )
    new_selections.append(pick)

st.session_state.selected_players = new_selections
selected_players = [p for p in new_selections if p != "None"]

if not selected_players:
    st.info("Select at least one player.")
    st.stop()

df_selected = players[players["player"].isin(selected_players)].set_index("player")

# ---------------------------------------------------------
# PROFILE SECTIONS
# ---------------------------------------------------------

PROFILE_SECTIONS = {
    "General": [
        "Games Played", "Minutes Played", "Points"
    ],
    "Attack": [
        "Dominant Carries", "Ball Carries", "Post Contact Metres",
        "Line Breaks", "Defenders Beaten", "Offloads",
        "Pass Outcome - Break", "Try Assists - Total",
        "Passes - Total Pass Attempts (including Offloads)",
        "Att OOA - 1st Own Team",
        "Att OOA - 2nd Own Team",
    ],
    "Defence": [
        "Dominant Tackles", "Missed Tackles", "Successful Tackles %",
        "Offload Allowed Tackles",
    ],
    "Breakdown": [
        "Breakdown Steals", "Turnover Won", "Turnover Conceded",
        "Jackals Attempted",
        "Ruck Arrival - Def. Intention - Jackal",
        "Ruck Arrival - Def. Intention - Counter-Ruck",
    ],
    "Kicking": [
        "Kicks", "Kicking Metres", "Kick Outcome - 50/22", "All Goals %"
    ],
    "Set Piece": [
        "Lineout Takes", "Lineout Steals", "Own Lineouts Won %",
        "Catch From Kick - Success", "Catch From Restart - Success",
        "Penalty Conceded - Scrum",
    ],
    "Discipline": [
        "Penalty Conceded", "Yellow Card", "Red Card"
    ]
}

# ---------------------------------------------------------
# RENDER PLAYER PROFILES
# ---------------------------------------------------------

st.subheader("📇 Player Profiles")

for name in selected_players:
    row = df_selected.loc[name]

    with st.expander(f"{name} – Profile"):

        st.markdown("<div class='neon-card'>", unsafe_allow_html=True)

        st.write(f"**Team:** {row.get('team', '')}")
        st.write(f"**League:** {row.get('league', '')}")
        st.write(f"**Position:** {row.get('position', '')}")

        games_played = row.get("Games Played", None)

        per_game = False
        if pd.notna(games_played) and games_played not in [0, "0", 0.0]:
            per_game = st.checkbox("Show per-game stats for this player", key=f"per_game_{name}")

        pos_metrics = get_metrics_for_position(descriptors, row.get("position"))

        tabs = st.tabs(list(PROFILE_SECTIONS.keys()))

        for tab, (section, metrics) in zip(tabs, PROFILE_SECTIONS.items()):
            with tab:
                st.markdown(f"### {section}")

                cols_tab = st.columns(4)
                idx = 0

                combined = []
                for metric in metrics:
                    if metric in universal_metrics or metric in pos_metrics or section == "General":
                        combined.append(metric)

                combined = list(dict.fromkeys(combined))

                for metric in combined:
                    if metric in row.index and pd.notna(row.get(metric)):
                        val = row.get(metric)

                        if per_game and not is_percentage_metric(metric) and metric != "Games Played":
                            try:
                                gp = float(games_played)
                                if gp > 0:
                                    val = float(val) / gp
                            except:
                                pass

                        if is_percentage_metric(metric):
                            value = format_percentage(val)
                        else:
                            value = format_number(val)

                        cols_tab[idx % 4].metric(metric, value)
                        idx += 1

        st.markdown("</div>", unsafe_allow_html=True)

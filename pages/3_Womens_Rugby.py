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
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="Women's Rugby – Player Profiles",
    layout="wide",
)

# ---------------------------------------------------------
# DARK THEME CSS
# ---------------------------------------------------------

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Garamond', serif;
    font-weight: 700;
    color: #FFFFFF;
}
:root {
    --bg-dark: #0E1117;
    --bg-card: #1E1E1E;
    --text-light: #FFFFFF;
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
    border: 1px solid rgba(255, 255, 255, 0.15);
}
[data-testid="stMetricValue"] {
    color: #00FFFF !important;
    font-weight: 700;
}
div[data-testid="stMetricLabel"] {
    color: #CCCCCC;
}
hr {
    border: 1px solid rgba(255,255,255,0.15);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FORMATTING HELPERS
# ---------------------------------------------------------

def format_number(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    try:
        v = float(value)
        return str(int(v)) if v.is_integer() else f"{v:.1f}"
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
        return f"{int(pct)}%" if pct.is_integer() else f"{pct:.1f}%"
    except:
        return ""

def is_percentage_metric(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    return "%" in n or "percent" in n or "rate" in n

# ---------------------------------------------------------
# TEAM-BASED WOMEN'S LEAGUE DETECTOR
# ---------------------------------------------------------

def load_womens_players():
    df = load_and_merge_players("data/women")
    df["team"] = df["team"].astype(str).str.upper().str.strip()

    CELTIC_TEAMS = {
        "CLOVERS", "WOLFHOUNDS", "EDINBURGH RUGBY WOMEN",
        "GLASGOW WARRIORS WOMEN", "BRYTHON THUNDER", "GWALIA LIGHTNING"
    }

    PWR_TEAMS = {
        "BRISTOL BEARS WOMEN", "EXETER CHIEFS WOMEN", "GLOUCESTER-HARTPURY",
        "HARLEQUINS WOMEN", "LEICESTER TIGERS WOMEN", "LOUGHBOROUGH LIGHTNING",
        "SALE SHARKS WOMEN", "SARACENS WOMEN", "TRAILFINDERS WOMEN"
    }

    def detect_league(team):
        if team in CELTIC_TEAMS:
            return "Celtic Challenge"
        if team in PWR_TEAMS:
            return "Premiership Women's Rugby"
        return None

    df["womens_league"] = df["team"].apply(detect_league)
    df_women = df[df["womens_league"].notna()].copy()

 
    return df_women

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

players = load_womens_players()
descriptors = load_descriptors("config/descriptors.yaml")

if players.empty:
    st.error("No women's rugby player data loaded. Check PWR & Celtic Challenge files in /data.")
    st.stop()

universal_metrics = descriptors.get("universal_metrics", [])

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
# HEADER
# ---------------------------------------------------------

st.markdown("<h1 style='text-align:center;'>🏉 Women's Rugby – Player Profiles</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# FILTERS — NON-RESETTING
# ---------------------------------------------------------

with st.container():
    st.markdown("<div class='neon-card'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    leagues = sorted(players["womens_league"].dropna().unique())
    league_choice = c1.selectbox("League", ["All leagues"] + leagues)

    filtered_for_teams = players.copy()
    if league_choice != "All leagues":
        filtered_for_teams = filtered_for_teams[filtered_for_teams["womens_league"] == league_choice]

    teams = sorted(filtered_for_teams["team"].dropna().unique())
    team_choice = c2.selectbox("Team", ["All teams"] + teams)

    filtered_for_positions = filtered_for_teams.copy()
    if team_choice != "All teams":
        filtered_for_positions = filtered_for_positions[filtered_for_positions["team"] == team_choice]

    positions = sorted(filtered_for_positions["position"].dropna().unique())
    pos_choice = c3.selectbox("Position", ["All positions"] + positions)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PLAYER SELECTION
# ---------------------------------------------------------

st.subheader("🎯 Select Players")

filtered_players = players.copy()
if league_choice != "All leagues":
    filtered_players = filtered_players[filtered_players["womens_league"] == league_choice]
if team_choice != "All teams":
    filtered_players = filtered_players[filtered_players["team"] == team_choice]
if pos_choice != "All positions":
    filtered_players = filtered_players[filtered_players["position"] == pos_choice]

dropdown_options = sorted(filtered_players["player"].dropna().unique())

if "selected_players_women" not in st.session_state:
    st.session_state.selected_players_women = []

cols = st.columns(5)
new_selections = []

for i in range(5):
    default_value = (
        st.session_state.selected_players_women[i]
        if i < len(st.session_state.selected_players_women)
        else "None"
    )
    pick = cols[i].selectbox(
        f"Player {i+1}",
        ["None"] + dropdown_options,
        index=(["None"] + dropdown_options).index(default_value)
        if default_value in (["None"] + dropdown_options)
        else 0,
        key=f"women_player_pick_{i}"
    )
    new_selections.append(pick)

st.session_state.selected_players_women = new_selections
selected_players = [p for p in new_selections if p != "None"]

if not selected_players:
    st.info("Select at least one player.")
    st.stop()

df_selected = players[players["player"].isin(selected_players)].set_index("player")

# ---------------------------------------------------------
# RENDER PLAYER PROFILES
# ---------------------------------------------------------

st.subheader("📇 Player Profiles")

for name in selected_players:
    row = df_selected.loc[name]

    with st.expander(f"{name} – Profile"):

        st.markdown("<div class='neon-card'>", unsafe_allow_html=True)

        st.write(f"**Team:** {row.get('team', '')}")
        st.write(f"**League:** {row.get('womens_league', '')}")
        st.write(f"**Position:** {row.get('position', '')}")

        games_played = row.get("Games Played", None)

        per_game = False
        if pd.notna(games_played) and games_played not in [0, "0", 0.0]:
            per_game = st.checkbox(
                "Show per-game stats for this player",
                key=f"women_per_game_{name}"
            )

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

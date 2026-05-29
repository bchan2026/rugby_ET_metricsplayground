import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

from utils import (
    load_and_merge_players,
    load_descriptors,
    get_metrics_for_position,
)

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

# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------

st.set_page_config(
    page_title="Women's Player Comparison – Ealing Recruitment Tool",
    layout="wide",
)

# ---------------------------------------------------------
# STYLING
# ---------------------------------------------------------

st.markdown("""
<style>

html, body, [class*="css"]  {
    font-family: 'Garamond', serif;
    font-weight: 700;
    color: #000000;
}

.neon-card {
    background: #F5F5F5;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid rgba(0, 0, 0, 0.15);
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
# FORMATTING HELPERS
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
# WOMEN'S DATA LOADER WITH TEAM-BASED LEAGUE DETECTION
# ---------------------------------------------------------

def load_womens_players():
    df = load_and_merge_players("data/women")
    df["team"] = df["team"].astype(str).str.upper().str.strip()

    # Use substrings so variants like "BRISTOL BEARS WOMEN" still match
    CELTIC_KEYS = [
        "CLOVERS",
        "WOLFHOUNDS",
        "EDINBURGH",
        "GLASGOW",
        "BRYTHON THUNDER",
        "GWALIA",
    ]

    PWR_KEYS = [
        "BRISTOL BEARS",
        "EXETER CHIEFS",
        "GLOUCESTER-HARTPURY",
        "HARLEQUINS",
        "LEICESTER TIGERS",
        "LOUGHBOROUGH",
        "SALE SHARKS",
        "SARACENS",
        "TRAILFINDERS",
    ]

    def detect_league(team: str):
        if not isinstance(team, str):
            return None
        t = team.upper()
        if any(k in t for k in CELTIC_KEYS):
            return "Celtic Challenge"
        if any(k in t for k in PWR_KEYS):
            return "Premiership Women's Rugby"
        return None

    df["womens_league"] = df["team"].apply(detect_league)
    df_women = df[df["womens_league"].notna()].copy()
    return df_women

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

@st.cache_data
def get_data_women():
    players = load_womens_players()
    descriptors = load_descriptors("config/descriptors.yaml")
    return players, descriptors

players, descriptors = get_data_women()
universal_metrics = descriptors.get("universal_metrics", [])

if players.empty:
    st.error("No women's player data loaded. Check PWR & Celtic Challenge files in /data/women.")
    st.stop()

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown("<h1 style='font-size:42px;'>Women's Player Comparison – Radar & Percentiles</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# FILTERS
# ---------------------------------------------------------

with st.container():
    st.markdown("<div class='neon-card'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    leagues = sorted(players["womens_league"].dropna().unique())
    league_choice = c1.selectbox("League", ["All leagues"] + leagues)

    filtered = players.copy()
    if league_choice != "All leagues":
        filtered = filtered[filtered["womens_league"] == league_choice]

    teams = sorted(filtered["team"].dropna().unique())
    team_choice = c2.selectbox("Team", ["All teams"] + teams)

    if team_choice != "All teams":
        filtered = filtered[filtered["team"] == team_choice]

    positions = sorted(filtered["position"].dropna().unique())
    pos_choice = c3.selectbox("Position", ["All positions"] + positions)

    if pos_choice != "All positions":
        filtered = filtered[filtered["position"] == pos_choice]

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PLAYER SELECTION (PERSISTENT)
# ---------------------------------------------------------

st.subheader("🎯 Select Players to Compare (2–6)")

if "compare_players_women" not in st.session_state:
    st.session_state.compare_players_women = ["None"] * 6

player_options = ["None"] + sorted(filtered["player"].dropna().unique())

cols = st.columns(6)
new_selections = []

for i in range(6):
    current_value = st.session_state.compare_players_women[i]

    if current_value not in player_options:
        options = player_options + [current_value]
    else:
        options = player_options

    new_value = cols[i].selectbox(
        f"Player {i+1}",
        options,
        index=options.index(current_value) if current_value in options else 0,
        key=f"compare_women_select_{i}"
    )

    new_selections.append(new_value)

st.session_state.compare_players_women = new_selections
selected_players = [p for p in new_selections if p != "None"]

if len(selected_players) < 2:
    st.info("Select at least two players.")
    st.stop()

df_selected = players[players["player"].isin(selected_players)].set_index("player")

# ---------------------------------------------------------
# PERCENTILE CALCULATION
# ---------------------------------------------------------

def compute_percentile(value, series):
    """Return percentile rank of value within a pandas Series."""
    if pd.isna(value):
        return np.nan
    try:
        return (series < value).mean() * 100
    except:
        return np.nan

# ---------------------------------------------------------
# RADAR CHART BUILDER (SINGLE PLAYER – NOT SHOWN BUT AVAILABLE)
# ---------------------------------------------------------

def build_radar(player_name, row, descriptors, players_df):
    position = row.get("position")

    # Metrics for this player
    pos_metrics = get_metrics_for_position(descriptors, position)
    metrics = universal_metrics + pos_metrics

    # POSITIONAL GROUP (ALL LEAGUES)
    position_group = players_df[
        (players_df["position"] == position)
    ]

    # Compute percentiles
    percentiles = []
    position_avg = []

    for metric in metrics:
        if metric not in row.index:
            percentiles.append(0)
            position_avg.append(50)
            continue

        series = position_group[metric].dropna()
        if series.empty:
            percentiles.append(0)
            position_avg.append(50)
            continue

        val = row.get(metric)
        pct = compute_percentile(val, series)
        percentiles.append(0 if pd.isna(pct) else pct)

        # Positional average = 50th percentile
        position_avg.append(50)

    # Radar chart
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=percentiles,
        theta=metrics,
        fill='toself',
        name=player_name,
        line=dict(color="green")
    ))

    fig.add_trace(go.Scatterpolar(
        r=position_avg,
        theta=metrics,
        fill='toself',
        name=f"{position} Positional Avg",
        line=dict(color="black")
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        height=600
    )

    return fig

# ---------------------------------------------------------
# COMBINED RADAR CHART
# ---------------------------------------------------------

st.subheader("📊 Combined Radar Chart (All Selected Players)")

# Build metric list for radar (union of all players' metrics)
radar_metrics = list(universal_metrics)
for name in selected_players:
    pos = df_selected.loc[name].get("position")
    pos_metrics = get_metrics_for_position(descriptors, pos)
    for m in pos_metrics:
        if m not in radar_metrics:
            radar_metrics.append(m)

# Compute league averages per metric (50th percentile placeholder = 50)
league_avg = []
for metric in radar_metrics:
    vals = players[metric].dropna() if metric in players.columns else pd.Series([])
    if vals.empty:
        league_avg.append(50)
    else:
        league_avg.append(50)

# Build combined radar
fig = go.Figure()

# Colour palette
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

for idx, name in enumerate(selected_players):
    row = df_selected.loc[name]
    position = row.get("position")
    league = row.get("womens_league")

    # Positional league group
    league_group = players[
        (players["womens_league"] == league) &
        (players["position"] == position)
    ]

    percentiles = []
    for metric in radar_metrics:
        if metric not in row.index:
            percentiles.append(0)
            continue

        series = league_group[metric].dropna()
        if series.empty:
            percentiles.append(0)
            continue

        val = row.get(metric)
        pct = compute_percentile(val, series)
        percentiles.append(0 if pd.isna(pct) else pct)

    fig.add_trace(go.Scatterpolar(
        r=percentiles,
        theta=radar_metrics,
        fill='toself',
        name=name,
        line=dict(color=colors[idx % len(colors)], width=3)
    ))

# Add league average
fig.add_trace(go.Scatterpolar(
    r=league_avg,
    theta=radar_metrics,
    fill='toself',
    name="League Positional Avg",
    line=dict(color="black", width=2, dash="dot")
))

fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 100]
        )
    ),
    showlegend=True,
    height=700
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# CLEAN COMPARISON TABLE (VALUES ONLY, COLOUR HIGHLIGHTING)
# ---------------------------------------------------------

st.subheader("📋 Comparison Table")

# Toggles
colA, colB = st.columns(2)
per_game = colA.checkbox("Show per‑game values")
pos_only = colB.checkbox("Show only position‑specific metrics")

# Build metric list
all_metrics = []

if not pos_only:
    all_metrics.extend(universal_metrics)

# Add all position‑specific metrics for selected players
for name in selected_players:
    pos = df_selected.loc[name].get("position")
    pos_metrics = get_metrics_for_position(descriptors, pos)
    for m in pos_metrics:
        if m not in all_metrics:
            all_metrics.append(m)

# Build raw numeric table
raw = pd.DataFrame(index=all_metrics)

for name in selected_players:
    row = df_selected.loc[name]

    values = []
    for metric in all_metrics:
        val = row.get(metric, np.nan)

        # Per‑game conversion
        if per_game and metric != "Games Played" and not is_percentage_metric(metric):
            gp = row.get("Games Played", 1)
            if gp and gp != 0:
                val = val / gp

        values.append(val)

    raw[name] = values

# ---------------------------------------------------------
# CONVERT TO DISPLAY TABLE (STRING FORMATTING)
# ---------------------------------------------------------

styled = pd.DataFrame(index=all_metrics)

def format_value(metric, v):
    if pd.isna(v):
        return ""

    # Percentage metrics: convert 0.83 → 83
    if is_percentage_metric(metric):
        try:
            return f"{float(v) * 100:.1f}".rstrip("0").rstrip(".")
        except:
            return ""

    # Normal numeric formatting
    try:
        v = float(v)
        if v.is_integer():
            return str(int(v))
        return f"{v:.1f}"
    except:
        return str(v)

for name in selected_players:
    styled[name] = [
        format_value(metric, raw.loc[metric, name])
        for metric in all_metrics
    ]

# ---------------------------------------------------------
# HIGHLIGHT BEST + SECOND BEST (COLOUR ONLY)
# ---------------------------------------------------------

best_counts = {name: 0 for name in selected_players}

# Create a parallel style table
style_map = pd.DataFrame("", index=all_metrics, columns=styled.columns)

for metric in all_metrics:
    # Extract numeric values only
    row_vals = {
        name: raw.loc[metric, name]
        for name in selected_players
        if pd.notna(raw.loc[metric, name])
    }

    if len(row_vals) >= 2:

        # NORMAL METRICS → higher is better
        if metric not in LOWER_IS_BETTER:
            sorted_vals = sorted(row_vals.items(), key=lambda x: x[1], reverse=True)

        # LOWER IS BETTER METRICS → lower is better
        else:
            sorted_vals = sorted(row_vals.items(), key=lambda x: x[1], reverse=False)

        best, second = sorted_vals[0][0], sorted_vals[1][0]

        # Best = bold + green text
        style_map.loc[metric, best] = "font-weight:700; color:#2ecc71;"
        best_counts[best] += 1

        # Second best = orange text
        style_map.loc[metric, second] = "color:#e67e22;"

# ---------------------------------------------------------
# ADD 1️⃣ BADGE TO TOP PERFORMER
# ---------------------------------------------------------

top_player = max(best_counts, key=best_counts.get)
styled.rename(columns={top_player: f"1️⃣ {top_player}"}, inplace=True)
style_map.rename(columns={top_player: f"1️⃣ {top_player}"}, inplace=True)

# ---------------------------------------------------------
# DISPLAY TABLE WITH STYLING
# ---------------------------------------------------------

st.dataframe(
    styled.style.set_properties(**{"text-align": "center"}).apply(
        lambda row: style_map.loc[row.name], axis=1
    ),
    use_container_width=True
)

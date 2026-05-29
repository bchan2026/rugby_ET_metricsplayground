import os
import pandas as pd
import yaml

LEAGUE_TEAMS = {
    "BUNNINGS WAREHOUSE NPC": [
        "AUCKLAND", "BAY OF PLENTY", "CANTERBURY", "COUNTIES MANUKAU",
        "HAWKES BAY", "MANAWATŪ", "NORTH HARBOUR", "NORTHLAND",
        "OTAGO", "SOUTHLAND", "TARANAKI", "TASMAN", "WAIKATO", "WELLINGTON"
    ],
    "PREM RUGBY": [
        "BATH RUGBY", "BRISTOL BEARS", "EXETER CHIEFS", "GLOUCESTER RUGBY",
        "HARLEQUINS", "LEICESTER TIGERS", "NEWCASTLE RED BULLS",
        "NORTHAMPTON SAINTS", "SALE SHARKS", "SARACENS"
    ],
    "SUPER RUGBY": [
        "ACT BRUMBIES", "BLUES", "CHIEFS", "CRUSADERS", "FIJIAN DRUA",
        "HIGHLANDERS", "HURRICANES", "MOANA PASIFIKA", "NSW WARATAHS",
        "QUEENSLAND REDS", "WESTERN FORCE"
    ],
    "UNITED RUGBY CHAMPIONSHIP": [
        "BENETTON RUGBY", "BULLS", "CARDIFF RUGBY", "CONNACHT RUGBY",
        "DRAGONS RFC", "EDINBURGH RUGBY", "GLASGOW WARRIORS",
        "LEINSTER RUGBY", "LIONS", "MUNSTER RUGBY", "OSPREYS",
        "SCARLETS", "SHARKS", "STORMERS", "ULSTER RUGBY", "ZEBRE PARMA"
    ],
    "TOP 14": [
        "ASM CLERMONT AUVERGNE", "BAYONNE", "CASTRES OLYMPIQUE", "LYON",
        "MONTPELLIER HERAULT RUGBY", "RACING 92", "RC TOULON",
        "SECTION PALOISE", "STADE FRANCAIS PARIS", "STADE ROCHELAIS",
        "STADE TOULOUSAIN", "UNION BORDEAUX-BEGLES", "US MONTAUBAN", "USAP"
    ],
    "SHUTE SHIELD": [
        "EASTERN SUBURBS",
        "EASTWOOD",
        "GORDON",
        "HUNTER WILDFIRES",
        "MANLY",
        "NORTHERN SUBURBS",
        "RANDWICK",
        "SOUTHERN DISTRICTS",
        "SYDNEY UNIVERSITY",
        "WARRINGAH",
        "WEST HARBOUR",
        "WESTERN SYDNEY"
    ],
}

TEAM_TO_LEAGUE = {}
for league, teams in LEAGUE_TEAMS.items():
    for t in teams:
        TEAM_TO_LEAGUE[t.upper()] = league


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Player": "player",
        "PLAYER": "player",
        "Player Name": "player",
        "Name": "player",

        "Team": "team",
        "TEAM": "team",

        "Position": "position",
        "POS": "position",

        "Games Played": "Games Played",
        "Minutes Played": "Minutes Played",
    }
    return df.rename(columns={c: rename_map[c] for c in df.columns if c in rename_map})


def detect_league(team: str) -> str:
    if not team or pd.isna(team):
        return "Unknown"
    return TEAM_TO_LEAGUE.get(str(team).upper().strip(), "Unknown")


def load_and_merge_players(data_path: str) -> pd.DataFrame:
    if not os.path.exists(data_path):
        return pd.DataFrame()

    excel_files = [
        f for f in os.listdir(data_path)
        if f.lower().endswith((".xlsx", ".xls"))
    ]

    dfs = []
    for file in excel_files:
        full_path = os.path.join(data_path, file)
        try:
            df = pd.read_excel(full_path)
            df = normalise_columns(df)
            df["source_mtime"] = os.path.getmtime(full_path)

            if "team" in df.columns:
                df["league"] = df["team"].apply(detect_league)
            else:
                df["league"] = "Unknown"

            dfs.append(df)

        except Exception as e:
            print(f"⚠️ Could not read {file}: {e}")

    if not dfs:
        return pd.DataFrame()

    merged = pd.concat(dfs, ignore_index=True)

    if "position" in merged.columns:
        merged = merged[
            (~merged["position"].isin(["-", ""])) &
            (merged["position"].str.lower() != "unknown")
        ]

    merged = merged.sort_values("source_mtime", ascending=False)
    merged = merged.drop_duplicates(subset=["player"], keep="first")

    return merged


def load_descriptors(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ Could not load descriptors: {e}")
        return {}


def get_metrics_for_position(descriptors: dict, position: str):
    if not position:
        return []
    return descriptors.get("positions", {}).get(position, [])

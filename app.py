import streamlit as st
import pandas as pd
import sys
import numpy as np
from pathlib import Path
from datetime import datetime

# ---------------------------
# Ensure project root on path
# ---------------------------
sys.path.append(str(Path(__file__).resolve().parent))

from services.nba_player_logs import fetch_player_logs
from nba_api.stats.static import players
from services.lineups import show_lineups_page

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="NBA Player Game Logs", layout="wide")

# ---------------------------
# Session state initialization
# ---------------------------
if "logs" not in st.session_state:
    st.session_state.logs = None
if "cache" not in st.session_state:
    st.session_state.cache = {}
if "parlay" not in st.session_state:
    st.session_state.parlay = []

# ---------------------------
# Constants & Team Data
# ---------------------------
TEAM_ABBR_TO_ID = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751, "CHA": 1610612766,
    "CHI": 1610612741, "CLE": 1610612739, "DAL": 1610612742, "DEN": 1610612743,
    "DET": 1610612765, "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763, "MIA": 1610612748,
    "MIL": 1610612749, "MIN": 1610612750, "NOP": 1610612740, "NYK": 1610612752,
    "OKC": 1610612760, "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "TOR": 1610612761,
    "UTA": 1610612762, "WAS": 1610612764,
}

TEAM_COLORS = {
    "ATL": ("#E03A3E", "#C1D32F"), "BOS": ("#007A33", "#BA9653"),
    "BKN": ("#000000", "#FFFFFF"), "CHA": ("#1D1160", "#00788C"),
    "CHI": ("#CE1141", "#000000"), "CLE": ("#6F263D", "#FFB81C"),
    "DAL": ("#00538C", "#B8C4CA"), "DEN": ("#0E2240", "#FEC524"),
    "DET": ("#C8102E", "#1D42BA"), "GSW": ("#1D428A", "#FFC72C"),
    "HOU": ("#CE1141", "#C4CED4"), "IND": ("#002D62", "#FDBB30"),
    "LAC": ("#C8102E", "#1D428A"), "LAL": ("#552583", "#FDB927"),
    "MEM": ("#5D76A9", "#12173F"), "MIA": ("#98002E", "#F9A01B"),
    "MIL": ("#00471B", "#EEE1C6"), "MIN": ("#0C2340", "#78BE20"),
    "NOP": ("#0C2340", "#C8102E"), "NYK": ("#006BB6", "#F58426"),
    "OKC": ("#007AC1", "#EF3B24"), "ORL": ("#0077C0", "#C4CED4"),
    "PHI": ("#006BB6", "#ED174C"), "PHX": ("#1D1160", "#E56020"),
    "POR": ("#E03A3E", "#000000"), "SAC": ("#5A2D81", "#63727A"),
    "SAS": ("#C4CED4", "#000000"), "TOR": ("#CE1141", "#000000"),
    "UTA": ("#002B5C", "#F9A01B"), "WAS": ("#002B5C", "#E31837"),
}

# ---------------------------
# Helpers
# ---------------------------
@st.cache_data(show_spinner=False)
def load_players():
    return sorted(p["full_name"] for p in players.get_active_players())

def headshot(pid: int) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"

def team_logo(abbr: str) -> str:
    tid = TEAM_ABBR_TO_ID.get(abbr)
    return f"https://cdn.nba.com/logos/nba/{tid}/primary/L/logo.svg" if tid else ""

def american_to_decimal(o: float) -> float:
    return (o / 100.0 + 1.0) if o > 0 else (100.0 / abs(o) + 1.0)

def decimal_to_american(d: float) -> str:
    if d <= 1: return "N/A"
    return f"+{int((d - 1) * 100)}" if d >= 2 else f"-{int(100 / (d - 1))}"

def ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    numeric_cols = ["PTS", "REB", "AST", "FG3M", "MIN"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce")
    df = df.dropna(subset=["GAME_DATE"])
    if "TEAM_ABBR" not in df.columns:
        df["TEAM_ABBR"] = df["MATCHUP"].astype(str).str[:3]
    if "OPP_ABBR" not in df.columns:
        df["OPP_ABBR"] = df["MATCHUP"].astype(str).str[-3:]
    df["Pts+Reb+Ast"] = df["PTS"] + df["REB"] + df["AST"]
    df["Pts+Reb"] = df["PTS"] + df["REB"]
    df["Pts+Ast"] = df["PTS"] + df["AST"]
    df["Reb+Ast"] = df["REB"] + df["AST"]
    return df.sort_values("GAME_DATE", ascending=False)

# ---------------------------
# Navigation Routing
# ---------------------------
with st.sidebar:
    st.title("Navigation")
    page = st.radio("Go to", ["Prop Analysis", "Lineups & Injuries"])
    st.divider()

if page == "Lineups & Injuries":
    show_lineups_page(TEAM_ABBR_TO_ID)
    st.stop()

# ---------------------------
# PROP ANALYSIS PAGE
# ---------------------------
st.title("🏀 NBA Player Game Log & Prop Analysis")
player = st.selectbox("Search active player", load_players(), index=None)

if st.button("Fetch Game Logs") and player:
    if player not in st.session_state.cache:
        st.session_state.cache[player] = fetch_player_logs(player)
    st.session_state.logs = ensure_cols(st.session_state.cache[player])

if st.session_state.logs is None:
    st.info("Search for a player to load game logs.")
    st.stop()

logs = st.session_state.logs
pid = int(logs["PLAYER_ID"].iloc[0])
team_abbr = str(logs["TEAM_ABBR"].iloc[0])
player_name = str(logs["PLAYER_NAME"].iloc[0])
c1, c2 = TEAM_COLORS.get(team_abbr, ("#111111", "#222222"))

# Player Header
st.markdown(
    f'<div style="background:linear-gradient(135deg,{c1},{c2});border-radius:16px;padding:18px;color:white;margin-bottom:18px;">'
    f'<div style="display:flex;align-items:center;justify-content:space-between;">'
    f'<div style="display:flex;gap:16px;align-items:center;">'
    f'<img src="{headshot(pid)}" style="width:88px;height:88px;border-radius:50%;border:2px solid rgba(255,255,255,.4);object-fit:cover;">'
    f'<div><div style="font-size:26px;font-weight:800;">{player_name}</div><div style="font-size:13px;opacity:.9;">{team_abbr}</div></div>'
    f'</div>'
    f'<img src="{team_logo(team_abbr)}" style="width:74px;height:74px;object-fit:contain;">'
    f'</div></div>',
    unsafe_allow_html=True,
)

# Filters
st.subheader("Filters")
f1, f2, f3 = st.columns(3)
with f1: season_filter = st.selectbox("Season", ["All"] + sorted(logs["SEASON_USED"].unique()))
with f2: opp_filter = st.selectbox("Opponent", ["All"] + sorted(logs["OPP_ABBR"].unique()))
with f3: recent_filter = st.selectbox("Recent Games", ["All", "Last 5", "Last 10"])

flt = logs.copy()
if season_filter != "All": flt = flt[flt["SEASON_USED"] == season_filter]
if opp_filter != "All": flt = flt[flt["OPP_ABBR"] == opp_filter]
if recent_filter == "Last 5": flt = flt.head(5)
elif recent_filter == "Last 10": flt = flt.head(10)

# --- SEASON AVERAGES (RESTORED) ---
st.subheader("Averages")
a, b, c, d = st.columns(4)
avg = flt[["PTS", "REB", "AST", "FG3M"]].mean().round(2)
a.metric("PTS", f"{avg['PTS']:.1f}")
b.metric("REB", f"{avg['REB']:.1f}")
c.metric("AST", f"{avg['AST']:.1f}")
d.metric("3PM", f"{avg['FG3M']:.1f}")

# Prop Evaluation Inputs
st.subheader("Prop Evaluation")
STAT_OPTIONS = ["PTS", "REB", "AST", "FG3M", "Pts+Reb+Ast", "Pts+Reb", "Pts+Ast", "Reb+Ast"]
p1, p2, p3, p4, p5 = st.columns(5)
with p1: selected_stat = st.selectbox("Stat", STAT_OPTIONS, key="prop_stat")
with p2: prop_line = st.selectbox("Line", [x * 0.5 for x in range(0, 121)], key="prop_line")
with p3: side = st.selectbox("Side", ["Over", "Under"], key="prop_side")
with p4: odds_type = st.selectbox("Odds Type", ["American", "Decimal"], key="prop_odds_type")
with p5: odds = st.number_input("Odds", value=-110.0 if odds_type == "American" else 1.91, key="prop_odds")

# Hit Rate / Edge
if prop_line > 0 and not flt.empty:
    flt["HIT"] = flt[selected_stat] > float(prop_line) if side == "Over" else flt[selected_stat] < float(prop_line)
    hits = int(flt["HIT"].sum())
    rate = (hits / len(flt) * 100)
    dec = american_to_decimal(float(odds)) if odds_type == "American" else float(odds)
    edge = rate - (1/dec * 100)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Games", len(flt))
    c2.metric("Hits", hits)
    c3.metric("Hit Rate", f"{rate:.1f}%")
    c4.markdown(f'<div style="background:{"#16a34a" if edge > 0 else "#dc2626"};padding:12px;border-radius:10px;text-align:center;color:white;font-weight:800;">{edge:+.1f}% Edge</div>', unsafe_allow_html=True)

is_mobile = st.checkbox("📱 Mobile view", value=False)

# ---------------------------
# LOGS RENDERING
# ---------------------------
if is_mobile:
    for _, r in flt.iterrows():
        matchup = str(r["MATCHUP"])
        parts = matchup.split(" ")
        left_abbr, connector, right_abbr = (parts[0], parts[1], parts[2]) if len(parts) >= 3 else ("???", "VS", "???")
        
        # HIGHLIGHTING HELPER
        def get_style(stat_name):
            if stat_name == selected_stat or (stat_name == "3PM" and selected_stat == "FG3M"):
                return "border: 2px solid #3b82f6; background: rgba(59, 130, 246, 0.15); border-radius: 8px;"
            return "border: 1px solid #222;"

        card_html = (
            f'<div style="background:#111; border-radius:14px; padding:16px; margin-bottom:16px; border:1px solid #262626; color: white;">'
            f'<div style="display:flex; justify-content:space-between; margin-bottom:12px;">'
            f'<span style="color:#3b82f6; font-weight:800;">{r["GAME_DATE"].strftime("%a, %b %d").upper()}</span>'
            f'<span style="font-weight:700;">⏱ {int(r["MIN"])} MIN</span></div>'
            
            f'<div style="display:flex; justify-content:center; gap:25px; padding-bottom:12px; border-bottom:1px solid #222;">'
            f'<div style="text-align:center;"><img src="{team_logo(left_abbr)}" style="width:35px;"><br><b>{left_abbr}</b></div>'
            f'<div style="margin-top:8px; font-weight:900; color:#444;">{connector}</div>'
            f'<div style="text-align:center;"><img src="{team_logo(right_abbr)}" style="width:35px;"><br><b>{right_abbr}</b></div>'
            f'</div>'
            
            f'<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; text-align:center; margin-top:12px;">'
            f'<div style="{get_style("PTS")}"><b>{int(r["PTS"])}</b><br><small style="color:#aaa;">PTS</small></div>'
            f'<div style="{get_style("REB")}"><b>{int(r["REB"])}</b><br><small style="color:#aaa;">REB</small></div>'
            f'<div style="{get_style("AST")}"><b>{int(r["AST"])}</b><br><small style="color:#aaa;">AST</small></div>'
            f'<div style="{get_style("FG3M")}"><b>{int(r["FG3M"])}</b><br><small style="color:#aaa;">3PM</small></div>'
            f'<div style="{get_style("Pts+Reb+Ast")}"><b>{int(r["Pts+Reb+Ast"])}</b><br><small style="color:#aaa;">PRA</small></div>'
            f'<div style="{get_style("Pts+Reb")}"><b>{int(r["Pts+Reb"])}</b><br><small style="color:#aaa;">PR</small></div>'
            f'<div style="{get_style("Pts+Ast")}"><b>{int(r["Pts+Ast"])}</b><br><small style="color:#aaa;">PA</small></div>'
            f'<div style="{get_style("Reb+Ast")}"><b>{int(r["Reb+Ast"])}</b><br><small style="color:#aaa;">RA</small></div>'
            f'</div></div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
else:
    st.dataframe(flt[["GAME_DATE", "MATCHUP", "MIN", "PTS", "REB", "AST", "FG3M", "Pts+Reb+Ast", "Pts+Reb", "Pts+Ast", "Reb+Ast"]], use_container_width=True)
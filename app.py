import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# ---------------------------
# Ensure project root on path
# ---------------------------
sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.nba_player_logs import fetch_player_logs
from nba_api.stats.static import players
from auth import require_login

# ---------------------------
# AUTH GATE
# ---------------------------
if not require_login():
    st.stop()

with st.sidebar:
    st.markdown("### Account")
    st.write(f"Logged in as **{st.session_state.get('user')}**")

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="NBA Player Game Logs",
    layout="wide"
)

st.title("🏀 NBA Player Game Log Search")

# ---------------------------
# Animations
# ---------------------------
st.markdown("""
<style>
@keyframes fadeSlideUp {
  from {opacity: 0; transform: translateY(12px);}
  to {opacity: 1; transform: translateY(0);}
}
.gamelog-card {
  animation: fadeSlideUp 0.35s ease-out forwards;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Team mapping
# ---------------------------
TEAM_ABBR_TO_ID = {
    "ATL":1610612737,"BOS":1610612738,"BKN":1610612751,"CHA":1610612766,
    "CHI":1610612741,"CLE":1610612739,"DAL":1610612742,"DEN":1610612743,
    "DET":1610612765,"GSW":1610612744,"HOU":1610612745,"IND":1610612754,
    "LAC":1610612746,"LAL":1610612747,"MEM":1610612763,"MIA":1610612748,
    "MIL":1610612749,"MIN":1610612750,"NOP":1610612740,"NYK":1610612752,
    "OKC":1610612760,"ORL":1610612753,"PHI":1610612755,"PHX":1610612756,
    "POR":1610612757,"SAC":1610612758,"SAS":1610612759,"TOR":1610612761,
    "UTA":1610612762,"WAS":1610612764,
}

TEAM_COLORS = {
    "ATL":("#E03A3E","#C1D32F"),"BOS":("#007A33","#BA9653"),
    "BKN":("#000000","#FFFFFF"),"CHA":("#1D1160","#00788C"),
    "CHI":("#CE1141","#000000"),"CLE":("#6F263D","#FFB81C"),
    "DAL":("#00538C","#B8C4CA"),"DEN":("#0E2240","#FEC524"),
    "DET":("#C8102E","#1D42BA"),"GSW":("#1D428A","#FFC72C"),
    "HOU":("#CE1141","#C4CED4"),"IND":("#002D62","#FDBB30"),
    "LAC":("#C8102E","#1D428A"),"LAL":("#552583","#FDB927"),
    "MEM":("#5D76A9","#12173F"),"MIA":("#98002E","#F9A01B"),
    "MIL":("#00471B","#EEE1C6"),"MIN":("#0C2340","#78BE20"),
    "NOP":("#0C2340","#C8102E"),"NYK":("#006BB6","#F58426"),
    "OKC":("#007AC1","#EF3B24"),"ORL":("#0077C0","#C4CED4"),
    "PHI":("#006BB6","#ED174C"),"PHX":("#1D1160","#E56020"),
    "POR":("#E03A3E","#000000"),"SAC":("#5A2D81","#63727A"),
    "SAS":("#C4CED4","#000000"),"TOR":("#CE1141","#000000"),
    "UTA":("#002B5C","#F9A01B"),"WAS":("#002B5C","#E31837"),
}

# ---------------------------
# Helpers
# ---------------------------
@st.cache_data
def load_player_names():
    return sorted(p["full_name"] for p in players.get_players())

@st.cache_data(ttl=3600)
def cached_fetch_player_logs(player_name):
    return fetch_player_logs(player_name)

def player_headshot(pid):
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"

def team_logo(abbr):
    tid = TEAM_ABBR_TO_ID.get(abbr)
    return f"https://cdn.nba.com/logos/nba/{tid}/primary/L/logo.svg" if tid else ""

# ---------------------------
# Search
# ---------------------------
player_list = load_player_names()

player_name = st.selectbox(
    "Search player",
    options=player_list,
    index=None,
    placeholder="e.g. Curry, Jokic, Luka"
)

if st.button("Fetch Game Logs") and player_name:
    with st.spinner("Fetching game logs..."):
        st.session_state["logs"] = cached_fetch_player_logs(player_name)

if "logs" not in st.session_state:
    st.stop()

logs = st.session_state["logs"].copy()

# ---------------------------
# Mobile toggle
# ---------------------------
is_mobile = st.checkbox("📱 Mobile-friendly view", value=False)

# ---------------------------
# Player Header
# ---------------------------
player_id = logs["PLAYER_ID"].iloc[0]
player_name = logs["PLAYER_NAME"].iloc[0]
team_abbr = logs["TEAM_ABBR"].iloc[0]

primary, secondary = TEAM_COLORS.get(team_abbr, ("#111", "#222"))
avatar = 72 if is_mobile else 88
logo = 56 if is_mobile else 72

st.markdown(
f"""
<div style="background:linear-gradient(135deg,{primary},{secondary});
border-radius:16px;padding:18px;color:white;margin-bottom:16px;">
<div style="display:flex;align-items:center;justify-content:space-between;">
<div style="display:flex;gap:18px;align-items:center;">
<img src="{player_headshot(player_id)}" style="width:{avatar}px;height:{avatar}px;border-radius:50%;">
<div>
<div style="font-size:26px;font-weight:700;">{player_name}</div>
<div style="opacity:0.85;">{team_abbr}</div>
</div>
</div>
<img src="{team_logo(team_abbr)}" style="width:{logo}px;height:{logo}px;">
</div>
</div>
""",
unsafe_allow_html=True
)

# ---------------------------
# Filters
# ---------------------------
st.subheader("Filters")

c1, c2, c3 = st.columns(3)

season = c1.selectbox("Season", ["All"] + sorted(logs["SEASON_USED"].unique()))
opp = c2.selectbox("Opponent", ["All"] + sorted(logs["OPP_ABBR"].unique()))
recent = c3.selectbox("Recent Games", ["All", "Last 5", "Last 10"])

filtered = logs.copy()
if season != "All":
    filtered = filtered[filtered["SEASON_USED"] == season]
if opp != "All":
    filtered = filtered[filtered["OPP_ABBR"] == opp]
filtered = filtered.sort_values("GAME_DATE", ascending=False)

if recent == "Last 5":
    filtered = filtered.head(5)
elif recent == "Last 10":
    filtered = filtered.head(10)

# ---------------------------
# Season Averages
# ---------------------------
st.subheader("Season Averages")

avg = filtered[["PTS","REB","AST","FG3M"]].mean().round(2)
a,b,c,d = st.columns(4)
a.metric("PTS", avg["PTS"])
b.metric("REB", avg["REB"])
c.metric("AST", avg["AST"])
d.metric("3PM", avg["FG3M"])

# ---------------------------
# Game Logs
# ---------------------------
st.subheader(f"Showing {len(filtered)} games")

if not is_mobile:
    df = filtered[["GAME_DATE","MATCHUP","MIN","PTS","REB","AST","FG3M"]].copy()
    df["GAME_DATE"] = df["GAME_DATE"].dt.strftime("%Y-%m-%d")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    for _, r in filtered.iterrows():
        st.markdown(
f"""
<div class="gamelog-card" style="background:#0e0e0e;border-radius:14px;padding:14px;margin-bottom:14px;color:white;">
<div style="display:flex;align-items:center;gap:12px;">
<img src="{player_headshot(r['PLAYER_ID'])}" style="width:48px;height:48px;border-radius:50%;">
<div style="flex:1;">
<div style="font-weight:600;">{r['MATCHUP']}</div>
<div style="font-size:12px;color:#aaa;">{r['GAME_DATE'].strftime('%Y-%m-%d')}</div>
</div>
</div>
<div style="display:flex;justify-content:space-between;margin-top:12px;text-align:center;">
<div><b>{r['PTS']}</b><br>PTS</div>
<div><b>{r['REB']}</b><br>REB</div>
<div><b>{r['AST']}</b><br>AST</div>
<div><b>{r['FG3M']}</b><br>3PM</div>
</div>
</div>
""",
unsafe_allow_html=True
)

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# ---------------------------
# Ensure project root on path
# ---------------------------
sys.path.append(str(Path(__file__).resolve().parents[0]))

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
    if st.button("Logout", key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="NBA Player Game Logs", layout="wide")
st.title("🏀 NBA Player Game Log Search")

# ---------------------------
# CSS (loader + card animation)
# ---------------------------
st.markdown(
    """
<style>
@keyframes bounce{0%,100%{transform:translateY(0);}50%{transform:translateY(-18px);}}
.loader{display:flex;flex-direction:column;align-items:center;justify-content:center;margin:26px 0;}
.ball{font-size:52px;animation:bounce 0.8s infinite ease-in-out;}
.loader-text{margin-top:10px;font-size:14px;color:#666;}

@keyframes fadeSlideUp{from{opacity:0;transform:translateY(12px);}to{opacity:1;transform:translateY(0);}}
.gamelog-card{animation:fadeSlideUp 0.35s ease-out forwards;}
</style>
""",
    unsafe_allow_html=True,
)

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

def player_headshot(pid: int) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"

def team_logo(abbr: str) -> str:
    tid = TEAM_ABBR_TO_ID.get(abbr)
    return f"https://cdn.nba.com/logos/nba/{tid}/primary/L/logo.svg" if tid else ""

def parse_team_opp_from_matchup(matchup: str):
    matchup = str(matchup)
    if " vs. " in matchup:
        t, o = matchup.split(" vs. ")
        return t.strip(), o.strip()
    if " @ " in matchup:
        t, o = matchup.split(" @ ")
        return t.strip(), o.strip()
    # fallback
    return matchup[:3].strip(), matchup[-3:].strip()

def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # GAME_DATE parse
    if "GAME_DATE" in df.columns:
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce")
        df = df.dropna(subset=["GAME_DATE"])
    else:
        df["GAME_DATE"] = pd.NaT

    # TEAM_ABBR
    if "TEAM_ABBR" not in df.columns:
        if "TEAM_ABBREVIATION" in df.columns:
            df["TEAM_ABBR"] = df["TEAM_ABBREVIATION"]
        elif "TEAM" in df.columns:
            df["TEAM_ABBR"] = df["TEAM"]
        else:
            df["TEAM_ABBR"] = df["MATCHUP"].astype(str).str[:3]

    # OPP_ABBR
    if "OPP_ABBR" not in df.columns:
        df["OPP_ABBR"] = df["MATCHUP"].astype(str).str[-3:]

    # Derived props (if not already present)
    if "Pts+Reb+Ast" not in df.columns:
        df["Pts+Reb+Ast"] = df.get("PTS", 0) + df.get("REB", 0) + df.get("AST", 0)
    if "Pts+Reb" not in df.columns:
        df["Pts+Reb"] = df.get("PTS", 0) + df.get("REB", 0)
    if "Pts+Ast" not in df.columns:
        df["Pts+Ast"] = df.get("PTS", 0) + df.get("AST", 0)
    if "Reb+Ast" not in df.columns:
        df["Reb+Ast"] = df.get("REB", 0) + df.get("AST", 0)

    return df

# ---------------------------
# Search
# ---------------------------
player_list = load_player_names()

player_name = st.selectbox(
    "Search player",
    options=player_list,
    index=None,
    placeholder="e.g. Curry, Jokic, Luka",
    key="player_select",
)

fetch_clicked = st.button("Fetch Game Logs", key="fetch_btn")

if fetch_clicked and player_name:
    loader = st.empty()
    loader.markdown(
        '<div class="loader"><div class="ball">🏀</div><div class="loader-text">Loading game logs…</div></div>',
        unsafe_allow_html=True,
    )

    # Session-state cache to avoid Streamlit's cache “Running ...” message
    if "logs_cache" not in st.session_state:
        st.session_state["logs_cache"] = {}

    if player_name not in st.session_state["logs_cache"]:
        logs = fetch_player_logs(player_name)
        st.session_state["logs_cache"][player_name] = logs

    st.session_state["logs"] = st.session_state["logs_cache"][player_name]
    loader.empty()

if "logs" not in st.session_state:
    st.stop()

logs = ensure_required_columns(st.session_state["logs"])
logs = logs.sort_values("GAME_DATE", ascending=False).reset_index(drop=True)

# ---------------------------
# Mobile toggle
# ---------------------------
is_mobile = st.checkbox("📱 Mobile-friendly view", value=False, key="mobile_toggle")

# ---------------------------
# Player Header
# ---------------------------
player_id = int(logs["PLAYER_ID"].iloc[0]) if "PLAYER_ID" in logs.columns else None
player_display_name = logs["PLAYER_NAME"].iloc[0] if "PLAYER_NAME" in logs.columns else player_name
team_abbr = logs["TEAM_ABBR"].iloc[0] if "TEAM_ABBR" in logs.columns else ""

primary, secondary = TEAM_COLORS.get(team_abbr, ("#111111", "#222222"))
avatar = 72 if is_mobile else 88
logo = 56 if is_mobile else 72

st.markdown(
    f'<div style="background:linear-gradient(135deg,{primary},{secondary});border-radius:16px;padding:18px;color:white;margin-bottom:16px;"><div style="display:flex;align-items:center;justify-content:space-between;"><div style="display:flex;gap:18px;align-items:center;">'
    + (f'<img src="{player_headshot(player_id)}" style="width:{avatar}px;height:{avatar}px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,0.35);">' if player_id else "")
    + f'<div><div style="font-size:26px;font-weight:800;line-height:1;">{player_display_name}</div><div style="opacity:0.9;margin-top:4px;font-size:13px;">{team_abbr}</div></div></div>'
    + (f'<img src="{team_logo(team_abbr)}" style="width:{logo}px;height:{logo}px;object-fit:contain;filter:drop-shadow(0 6px 10px rgba(0,0,0,0.25));">' if team_abbr else "")
    + "</div></div>",
    unsafe_allow_html=True,
)

# ---------------------------
# Filters
# ---------------------------
st.subheader("Filters")
c1, c2, c3 = st.columns(3)

season = c1.selectbox("Season", ["All"] + sorted(logs["SEASON_USED"].dropna().unique().tolist()) if "SEASON_USED" in logs.columns else ["All"], key="season_filter")
opp = c2.selectbox("Opponent", ["All"] + sorted(logs["OPP_ABBR"].dropna().unique().tolist()), key="opp_filter")
recent = c3.selectbox("Recent Games", ["All", "Last 5", "Last 10"], key="recent_filter")

filtered = logs.copy()
if season != "All" and "SEASON_USED" in filtered.columns:
    filtered = filtered[filtered["SEASON_USED"] == season]
if opp != "All":
    filtered = filtered[filtered["OPP_ABBR"] == opp]
filtered = filtered.sort_values("GAME_DATE", ascending=False).reset_index(drop=True)

if recent == "Last 5":
    filtered = filtered.head(5)
elif recent == "Last 10":
    filtered = filtered.head(10)

# ---------------------------
# Season Averages (PTS/REB/AST/3PM only)
# ---------------------------
st.subheader("Season Averages")
avg = filtered[["PTS", "REB", "AST", "FG3M"]].mean(numeric_only=True).round(2)
a, b, c, d = st.columns(4)
a.metric("PTS", avg.get("PTS", 0))
b.metric("REB", avg.get("REB", 0))
c.metric("AST", avg.get("AST", 0))
d.metric("3PM", avg.get("FG3M", 0))

# ---------------------------
# Prop Evaluation (LINES/ODDS/EDGE)
# ---------------------------
st.subheader("Prop Evaluation")
p1, p2, p3, p4, p5 = st.columns(5)

with p1:
    prop_type = st.selectbox(
        "Stat",
        ["PTS", "REB", "AST", "FG3M", "Pts+Reb+Ast", "Pts+Reb", "Pts+Ast", "Reb+Ast"],
        key="prop_stat",
    )

with p2:
    # dropdown/scroll, 0.5 increments
    line_options = [round(x * 0.5, 1) for x in range(0, 121)]  # 0.0 -> 60.0
    prop_line = st.select_slider("Line", options=line_options, value=0.0, key="prop_line")

with p3:
    side = st.selectbox("Side", ["Over", "Under"], key="prop_side")

with p4:
    odds_type = st.selectbox("Odds Type", ["American", "Decimal"], key="odds_type")

with p5:
    odds_default = -110 if odds_type == "American" else 1.91
    odds_step = 1 if odds_type == "American" else 0.01
    odds = st.number_input("Odds", value=float(odds_default), step=float(odds_step), key="odds_val")

# Hit Rate & Edge
if prop_line > 0 and not filtered.empty and prop_type in filtered.columns:
    analysis_df = filtered.copy()

    if side == "Over":
        analysis_df["HIT"] = analysis_df[prop_type] > prop_line
    else:
        analysis_df["HIT"] = analysis_df[prop_type] < prop_line

    total_games = int(len(analysis_df))
    hits = int(analysis_df["HIT"].sum())
    hit_rate_pct = (hits / total_games * 100.0) if total_games > 0 else 0.0

    if odds_type == "American":
        if odds == 0:
            implied_prob_pct = 0.0
        elif odds < 0:
            implied_prob_pct = (-odds) / ((-odds) + 100) * 100
        else:
            implied_prob_pct = 100 / (odds + 100) * 100
    else:
        implied_prob_pct = (1 / odds) * 100 if odds else 0.0

    edge_pct = hit_rate_pct - implied_prob_pct

    st.subheader("Hit Rate & Edge")
    cA, cB, cC, cD = st.columns(4)
    cA.metric("Games", total_games)
    cB.metric("Hits", hits)
    cC.metric("Hit Rate", f"{hit_rate_pct:.1f}%")

    edge_color = "#2e7d32" if edge_pct > 0 else "#c62828"
    edge_bg = "#e6f7e6" if edge_pct > 0 else "#fdecea"
    edge_sign = "+" if edge_pct > 0 else ""

    cD.markdown(
        f'<div style="background:{edge_bg};padding:12px;border-radius:8px;text-align:center;"><div style="font-size:14px;color:{edge_color};">Edge</div><div style="font-size:24px;font-weight:700;color:{edge_color};">{edge_sign}{edge_pct:.1f}%</div><div style="font-size:12px;color:#666;margin-top:4px;">Implied: {implied_prob_pct:.1f}%</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------
# Game Logs (Desktop table / Mobile cards)
# ---------------------------
st.subheader(f"Showing {len(filtered)} games")

if not is_mobile:
    show_cols = ["GAME_DATE", "MATCHUP", "MIN", "PTS", "REB", "AST", "FG3M", "Pts+Reb+Ast", "Pts+Reb", "Pts+Ast", "Reb+Ast"]
    df = filtered[[c for c in show_cols if c in filtered.columns]].copy()
    df["GAME_DATE"] = df["GAME_DATE"].dt.strftime("%Y-%m-%d")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    for _, r in filtered.iterrows():
        matchup = r.get("MATCHUP", "")
        team_t, opp_t = parse_team_opp_from_matchup(matchup)

        team_ab = r.get("TEAM_ABBR", team_t)
        opp_ab = r.get("OPP_ABBR", opp_t)

        pts = int(r.get("PTS", 0))
        reb = int(r.get("REB", 0))
        ast = int(r.get("AST", 0))
        fg3m = int(r.get("FG3M", 0))
        pra = int(r.get("Pts+Reb+Ast", pts + reb + ast))
        pr = int(r.get("Pts+Reb", pts + reb))
        pa = int(r.get("Pts+Ast", pts + ast))
        ra = int(r.get("Reb+Ast", reb + ast))

        mins = r.get("MIN", 0)
        try:
            mins = int(float(mins))
        except Exception:
            mins = mins

        date_str = r["GAME_DATE"].strftime("%Y-%m-%d") if pd.notnull(r.get("GAME_DATE")) else ""

        head = player_headshot(int(r["PLAYER_ID"])) if "PLAYER_ID" in r and pd.notnull(r["PLAYER_ID"]) else ""
        tlogo = team_logo(team_ab)
        ologo = team_logo(opp_ab)

        st.markdown(
            f'<div class="gamelog-card" style="background:#0e0e0e;border-radius:16px;padding:14px 14px 12px 14px;margin-bottom:14px;color:white;">'
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<img src="{head}" style="width:46px;height:46px;border-radius:50%;object-fit:cover;border:1px solid rgba(255,255,255,0.25);">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-weight:800;font-size:14px;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{matchup}</div>'
            f'<div style="font-size:12px;color:#aaa;margin-top:3px;">{date_str}</div>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<img src="{tlogo}" style="width:30px;height:30px;object-fit:contain;">'
            f'<img src="{ologo}" style="width:30px;height:30px;object-fit:contain;">'
            f'</div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:12px;text-align:center;">'
            f'<div><div style="font-size:22px;font-weight:900;">{pts}</div><div style="font-size:11px;color:#aaa;">PTS</div></div>'
            f'<div><div style="font-size:22px;font-weight:900;">{reb}</div><div style="font-size:11px;color:#aaa;">REB</div></div>'
            f'<div><div style="font-size:22px;font-weight:900;">{ast}</div><div style="font-size:11px;color:#aaa;">AST</div></div>'
            f'<div><div style="font-size:22px;font-weight:900;">{fg3m}</div><div style="font-size:11px;color:#aaa;">3PM</div></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px;color:#bdbdbd;">'
            f'<div>PRA <b style="color:#fff;">{pra}</b></div>'
            f'<div>PR <b style="color:#fff;">{pr}</b></div>'
            f'<div>PA <b style="color:#fff;">{pa}</b></div>'
            f'<div>RA <b style="color:#fff;">{ra}</b></div>'
            f'</div>'
            f'<div style="margin-top:8px;font-size:11px;color:#aaa;">⏱ {mins} min</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
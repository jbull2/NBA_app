import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# ---------------------------
# Ensure project root on path
# ---------------------------
sys.path.append(str(Path(__file__).resolve().parent))

from services.nba_player_logs import fetch_player_logs
from nba_api.stats.static import players

from auth import require_login, logout

if "logs" not in st.session_state:
    st.session_state.logs = None

# ---------------------------
# Feature flags
# ---------------------------
USE_AUTH = False  # set to False to disable login

# ---------------------------
# AUTH (optional)
# ---------------------------
if USE_AUTH:

    if not require_login():
        st.stop()

    with st.sidebar:
        st.markdown("### Account")
        st.write(f"Logged in as **{st.session_state.get('user', '')}**")

        if st.button("Logout"):
            logout()

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="NBA Player Game Logs", layout="wide")
st.title("🏀 NBA Player Game Log & Prop Analysis")

# ---------------------------
# CSS
# ---------------------------
st.markdown(
    """
<style>
@keyframes bounce{0%,100%{transform:translateY(0);}50%{transform:translateY(-18px);}}
.loader{display:flex;flex-direction:column;align-items:center;justify-content:center;margin:28px 0;}
.ball{font-size:52px;animation:bounce .8s infinite ease-in-out;}
.loader-text{margin-top:10px;font-size:14px;color:#666;}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.card{animation:fadeUp .35s ease-out forwards;}
/* Parlay button row look */
.parlay-row{display:flex;justify-content:flex-end;gap:10px;align-items:center;margin-top:-8px;margin-bottom:10px;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------
# Team data
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
    # Active only
    return sorted(p["full_name"] for p in players.get_active_players())

def headshot(pid: int) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png"

def team_logo(abbr: str) -> str:
    tid = TEAM_ABBR_TO_ID.get(abbr)
    return f"https://cdn.nba.com/logos/nba/{tid}/primary/L/logo.svg" if tid else ""

def american_to_decimal(o: float) -> float:
    return (o / 100.0 + 1.0) if o > 0 else (100.0 / abs(o) + 1.0)

def decimal_to_american(d: float) -> str:
    if d <= 1:
        return "N/A"
    return f"+{int((d - 1) * 100)}" if d >= 2 else f"-{int(100 / (d - 1))}"

def parse_matchup_team_opp(matchup: str):
    # "DEN vs. LAL" or "DEN @ LAL"
    if "vs." in matchup:
        team, opp = matchup.split(" vs. ")
    elif " @ " in matchup:
        team, opp = matchup.split(" @ ")
    else:
        team, opp = matchup[:3], matchup[-3:]
    team = team.strip()
    opp = opp.strip()
    return team, opp

def ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce")
    df = df.dropna(subset=["GAME_DATE"])
    df = df.sort_values("GAME_DATE")

    # TEAM / OPP
    if "TEAM_ABBR" not in df.columns:
        df["TEAM_ABBR"] = df["MATCHUP"].astype(str).str[:3]
    if "OPP_ABBR" not in df.columns:
        df["OPP_ABBR"] = df["MATCHUP"].astype(str).str[-3:]

    # Derived stats
    df["Pts+Reb+Ast"] = df["PTS"] + df["REB"] + df["AST"]
    df["Pts+Reb"] = df["PTS"] + df["REB"]
    df["Pts+Ast"] = df["PTS"] + df["AST"]
    df["Reb+Ast"] = df["REB"] + df["AST"]

    # Rolling averages (SAFE)
    for stat in ["PTS", "REB", "AST", "FG3M"]:
        df[f"{stat}_L5"] = df[stat].rolling(5).mean()
        df[f"{stat}_L10"] = df[stat].rolling(10).mean()

    return df

# ---------------------------
# Session state
# ---------------------------
if "cache" not in st.session_state:
    st.session_state.cache = {}
if "parlay" not in st.session_state:
    st.session_state.parlay = []

# ---------------------------
# Search
# ---------------------------
player = st.selectbox("Search active player", load_players(), index=None)

if st.button("Fetch Game Logs") and player:
    loader = st.empty()
    loader.markdown('<div class="loader"><div class="ball">🏀</div><div class="loader-text">Loading…</div></div>', unsafe_allow_html=True)
    if player not in st.session_state.cache:
        st.session_state.cache[player] = fetch_player_logs(player)
    st.session_state.logs = st.session_state.cache[player]
    loader.empty()

if st.session_state.logs is None:
    st.info("Search for a player to load game logs.")
    st.stop()

logs = ensure_cols(st.session_state.logs).sort_values("GAME_DATE", ascending=False)

# ---------------------------
# Player Header
# ---------------------------
pid = int(logs["PLAYER_ID"].iloc[0])
team_abbr = str(logs["TEAM_ABBR"].iloc[0])
player_name = str(logs["PLAYER_NAME"].iloc[0])
c1, c2 = TEAM_COLORS.get(team_abbr, ("#111111", "#222222"))

st.markdown(
    f'<div style="background:linear-gradient(135deg,{c1},{c2});border-radius:16px;padding:18px;color:white;margin-bottom:18px;">'
    f'<div style="display:flex;align-items:center;justify-content:space-between;">'
    f'<div style="display:flex;gap:16px;align-items:center;">'
    f'<img src="{headshot(pid)}" style="width:88px;height:88px;border-radius:50%;border:2px solid rgba(255,255,255,.4);object-fit:cover;">'
    f'<div><div style="font-size:26px;font-weight:800;line-height:1.05;">{player_name}</div><div style="margin-top:6px;font-size:13px;opacity:.9;">{team_abbr}</div></div>'
    f'</div>'
    f'<img src="{team_logo(team_abbr)}" style="width:74px;height:74px;object-fit:contain;filter:drop-shadow(0 6px 10px rgba(0,0,0,.3));">'
    f'</div></div>',
    unsafe_allow_html=True,
)

# ---------------------------
# Filters
# ---------------------------
st.subheader("Filters")
f1, f2, f3 = st.columns(3)
with f1:
    season_filter = st.selectbox("Season", ["All"] + sorted(logs["SEASON_USED"].unique()))
with f2:
    opp_filter = st.selectbox("Opponent", ["All"] + sorted(logs["OPP_ABBR"].unique()))
with f3:
    recent_filter = st.selectbox("Recent Games", ["All", "Last 5", "Last 10"])

is_mobile = st.checkbox("📱 Mobile view", value=False, key="mobile_view")

flt = logs.copy()
if season_filter != "All":
    flt = flt[flt["SEASON_USED"] == season_filter]
if opp_filter != "All":
    flt = flt[flt["OPP_ABBR"] == opp_filter]
flt = flt.sort_values("GAME_DATE", ascending=False)
if recent_filter == "Last 5":
    flt = flt.head(5)
elif recent_filter == "Last 10":
    flt = flt.head(10)

# ---------------------------
# Averages (Season + Rolling)
# ---------------------------
st.subheader("Averages")

a, b, c, d = st.columns(4)

season_avg = flt[["PTS", "REB", "AST", "FG3M"]].mean().round(2)

rolling_5 = flt[["PTS_L5", "REB_L5", "AST_L5", "FG3M_L5"]].mean().round(2)
rolling_10 = flt[["PTS_L10", "REB_L10", "AST_L10", "FG3M_L10"]].mean().round(2)

a.metric("PTS", f"{season_avg['PTS']:.1f}", f"L5 {rolling_5['PTS_L5']:.1f}")
b.metric("REB", f"{season_avg['REB']:.1f}", f"L5 {rolling_5['REB_L5']:.1f}")
c.metric("AST", f"{season_avg['AST']:.1f}", f"L5 {rolling_5['AST_L5']:.1f}")
d.metric("3PM", f"{season_avg['FG3M']:.1f}", f"L5 {rolling_5['FG3M_L5']:.1f}")

st.caption(
    f"Rolling context — L10: "
    f"PTS {rolling_10['PTS_L10']:.1f} • "
    f"REB {rolling_10['REB_L10']:.1f} • "
    f"AST {rolling_10['AST_L10']:.1f} • "
    f"3PM {rolling_10['FG3M_L10']:.1f}"
)

# ---------------------------
# Parlay UI (top-right popover trigger)
# ---------------------------
st.markdown('<div class="parlay-row">', unsafe_allow_html=True)
with st.popover(f"🧾 Parlay ({len(st.session_state.parlay)})"):
    if not st.session_state.parlay:
        st.info("No legs yet")
    else:
        total_dec = 1.0
        for i, leg in enumerate(list(st.session_state.parlay)):
            total_dec *= float(leg["dec"])
            cols = st.columns([7, 2])
            cols[0].write(
                f"**{leg['player']}** — {leg['stat']} {leg['side']} {leg['line']}  \n"
                f"Odds: {leg['dec']:.2f} (dec)"
            )
            if cols[1].button("❌", key=f"parlay_remove_{i}"):
                st.session_state.parlay.pop(i)
                st.rerun()

        st.divider()
        st.metric("Total Decimal", f"{total_dec:.2f}")
        st.metric("Total American", decimal_to_american(total_dec))

        if st.button("Clear Parlay", type="secondary"):
            st.session_state.parlay = []
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Safe defaults (prevents NameError)
# ---------------------------
prop_type = "PTS"
prop_line = 0.0
side = "Over"
odds_type = "American"
odds = -110.0

# ---------------------------
# Prop Evaluation (narrower on desktop)
# ---------------------------
st.subheader("Prop Evaluation")

# Rolling form context (latest game row)
latest = flt.iloc[0] if not flt.empty else None

# ---------------------------
# Rolling averages context
# ---------------------------
if latest is not None:
    l5_col = f"{prop_type}_L5"
    l10_col = f"{prop_type}_L10"

    if l5_col in latest and l10_col in latest:
        if not pd.isna(latest[l5_col]) and not pd.isna(latest[l10_col]):
            st.caption(
                f"📈 Form — "
                f"Last 5: {latest[l5_col]:.1f} • "
                f"Last 10: {latest[l10_col]:.1f}"
            )

if latest is not None and f"{prop_type}_L5" in latest:
    st.caption(
        f"Form context — "
        f"L5: {latest[f'{prop_type}_L5']:.1f} • "
        f"L10: {latest[f'{prop_type}_L10']:.1f}"
    )

LINE_OPTIONS = [x * 0.5 for x in range(0, 121)]  # 0.0 .. 60.0

STAT_OPTIONS = [
    "PTS", "REB", "AST", "FG3M",
    "Pts+Reb+Ast", "Pts+Reb", "Pts+Ast", "Reb+Ast",
]

if is_mobile:
    p1, p2, p3, p4, p5 = st.columns(5)
    with p1:
        prop_type = st.selectbox("Stat", STAT_OPTIONS, key="prop_stat")
    with p2:
        prop_line = st.selectbox("Line", LINE_OPTIONS, index=0, key="prop_line")
    with p3:
        side = st.selectbox("Side", ["Over", "Under"], key="prop_side")
    with p4:
        odds_type = st.selectbox("Odds Type", ["American", "Decimal"], key="prop_odds_type")
    with p5:
        odds = st.number_input("Odds", value=-110.0 if odds_type == "American" else 1.91, step=1.0 if odds_type == "American" else 0.01, key="prop_odds")
else:
    left, right = st.columns([2, 3])
    with left:
        p1, p2 = st.columns(2)
        with p1:
            prop_type = st.selectbox("Stat", STAT_OPTIONS, key="prop_stat")
        with p2:
            prop_line = st.selectbox("Line", LINE_OPTIONS, index=0, key="prop_line")

        p3, p4, p5 = st.columns(3)
        with p3:
            side = st.selectbox("Side", ["Over", "Under"], key="prop_side")
        with p4:
            odds_type = st.selectbox("Odds Type", ["American", "Decimal"], key="prop_odds_type")
        with p5:
            odds = st.number_input(
                "Odds",
                value=-110.0 if odds_type == "American" else 1.91,
                step=1.0 if odds_type == "American" else 0.01,
                key="prop_odds",
            )
    with right:
        st.caption("")

# ---------------------------
# Hit Rate & Edge (styled green/red)
# ---------------------------
if prop_line > 0 and not flt.empty:
    analysis_df = flt.copy()

    if side == "Over":
        analysis_df["HIT"] = analysis_df[prop_type] > float(prop_line)
    else:
        analysis_df["HIT"] = analysis_df[prop_type] < float(prop_line)

    total_games = int(len(analysis_df))
    hits = int(analysis_df["HIT"].sum())
    hit_rate_pct = (hits / total_games * 100.0) if total_games else 0.0

    if odds_type == "American":
        dec = american_to_decimal(float(odds))
    else:
        dec = float(odds) if float(odds) > 0 else 1.0

    implied_prob_pct = (1.0 / dec * 100.0) if dec > 0 else 0.0
    edge_pct = hit_rate_pct - implied_prob_pct

    st.subheader("Hit Rate & Edge")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Games", total_games)
    c2.metric("Hits", hits)
    c3.metric("Hit Rate", f"{hit_rate_pct:.1f}%")

    edge_color = "#2e7d32" if edge_pct > 0 else "#c62828"
    edge_bg = "#e6f7e6" if edge_pct > 0 else "#fdecea"
    edge_sign = "+" if edge_pct > 0 else ""

    c4.markdown(
        f'<div style="background:{edge_bg};padding:12px;border-radius:10px;text-align:center;">'
        f'<div style="font-size:13px;color:{edge_color};font-weight:600;">Edge</div>'
        f'<div style="font-size:24px;font-weight:800;color:{edge_color};line-height:1.1;">{edge_sign}{edge_pct:.1f}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Add to parlay
    add_cols = st.columns([1, 5])
    with add_cols[0]:
        if st.button("➕ Add to Parlay", key="add_to_parlay_btn"):
            st.session_state.parlay.append(
                {"player": player_name, "stat": prop_type, "line": float(prop_line), "side": side, "dec": float(dec)}
            )
            st.rerun()

# ---------------------------
# Game Logs
# ---------------------------
st.subheader(f"Showing {len(flt)} games")

if not is_mobile:
    # Desktop table view
    show_cols = [
        "GAME_DATE", "MATCHUP", "MIN",
        "PTS", "REB", "AST", "FG3M",
        "PTS_L5", "PTS_L10"
    ]

    st.dataframe(
        flt[show_cols].reset_index(drop=True),
        use_container_width=True
    )
else:
    # Mobile card view (compact HTML, include logos + extra stats)
    for _, r in flt.iterrows():
        matchup = str(r["MATCHUP"])
        t_abbr, o_abbr = parse_matchup_team_opp(matchup)
        opp_logo_url = team_logo(o_abbr)
        my_logo_url = team_logo(t_abbr)
        date_str = r["GAME_DATE"].strftime("%Y-%m-%d")
        mins = int(r["MIN"]) if pd.notna(r["MIN"]) else 0

        pra = int(r["Pts+Reb+Ast"])
        pr = int(r["Pts+Reb"])
        pa = int(r["Pts+Ast"])
        ra = int(r["Reb+Ast"])

        # IMPORTANT: keep HTML tight (no extra whitespace between elements)
        st.markdown(
            f'<div class="card" style="background:#0e0e0e;border-radius:14px;padding:14px;margin-bottom:12px;color:white;">'
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<img src="{headshot(int(r["PLAYER_ID"]))}" style="width:44px;height:44px;border-radius:50%;object-fit:cover;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-weight:800;font-size:14px;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{player_name}</div>'
            f'<div style="font-size:12px;color:#aaa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{matchup} • {date_str}</div>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'{f"<img src={my_logo_url!r} style=\'width:28px;height:28px;object-fit:contain;\'>" if my_logo_url else ""}'
            f'{f"<img src={opp_logo_url!r} style=\'width:28px;height:28px;object-fit:contain;\'>" if opp_logo_url else ""}'
            f'</div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:12px;text-align:center;">'
            f'<div><div style="font-size:20px;font-weight:900;">{int(r["PTS"])}</div><div style="font-size:10px;color:#aaa;">PTS</div></div>'
            f'<div><div style="font-size:20px;font-weight:900;">{int(r["REB"])}</div><div style="font-size:10px;color:#aaa;">REB</div></div>'
            f'<div><div style="font-size:20px;font-weight:900;">{int(r["AST"])}</div><div style="font-size:10px;color:#aaa;">AST</div></div>'
            f'<div><div style="font-size:20px;font-weight:900;">{int(r["FG3M"])}</div><div style="font-size:10px;color:#aaa;">3PM</div></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:10px;text-align:center;opacity:.95;">'
            f'<div><div style="font-size:14px;font-weight:800;">{pra}</div><div style="font-size:10px;color:#aaa;">PRA</div></div>'
            f'<div><div style="font-size:14px;font-weight:800;">{pr}</div><div style="font-size:10px;color:#aaa;">P+R</div></div>'
            f'<div><div style="font-size:14px;font-weight:800;">{pa}</div><div style="font-size:10px;color:#aaa;">P+A</div></div>'
            f'<div><div style="font-size:14px;font-weight:800;">{ra}</div><div style="font-size:10px;color:#aaa;">R+A</div></div>'
            f'</div>'
            f'<div style="margin-top:10px;font-size:11px;color:#aaa;">⏱ {mins} min</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

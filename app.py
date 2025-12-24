import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import joblib

# ---------------------------
# Ensure project root on path
# ---------------------------
sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.nba_player_logs import fetch_player_logs
from nba_api.stats.static import players

st.markdown("""
<style>
@keyframes fadeSlideUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.gamelog-card {
  animation: fadeSlideUp 0.35s ease-out forwards;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="NBA Player Game Logs",
    layout="wide"
)

st.title("🏀 NBA Player Game Log Search")

# ---------------------------
# Team mapping (NBA CDN)
# ---------------------------
TEAM_ABBR_TO_ID = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751,
    "CHA": 1610612766, "CHI": 1610612741, "CLE": 1610612739,
    "DAL": 1610612742, "DEN": 1610612743, "DET": 1610612765,
    "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763,
    "MIA": 1610612748, "MIL": 1610612749, "MIN": 1610612750,
    "NOP": 1610612740, "NYK": 1610612752, "OKC": 1610612760,
    "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759,
    "TOR": 1610612761, "UTA": 1610612762, "WAS": 1610612764,
}

TEAM_COLORS = {
    "ATL": ("#E03A3E", "#C1D32F"),
    "BOS": ("#007A33", "#BA9653"),
    "BKN": ("#000000", "#FFFFFF"),
    "CHA": ("#1D1160", "#00788C"),
    "CHI": ("#CE1141", "#000000"),
    "CLE": ("#6F263D", "#FFB81C"),
    "DAL": ("#00538C", "#B8C4CA"),
    "DEN": ("#0E2240", "#FEC524"),
    "DET": ("#C8102E", "#1D42BA"),
    "GSW": ("#1D428A", "#FFC72C"),
    "HOU": ("#CE1141", "#C4CED4"),
    "IND": ("#002D62", "#FDBB30"),
    "LAC": ("#C8102E", "#1D428A"),
    "LAL": ("#552583", "#FDB927"),
    "MEM": ("#5D76A9", "#12173F"),
    "MIA": ("#98002E", "#F9A01B"),
    "MIL": ("#00471B", "#EEE1C6"),
    "MIN": ("#0C2340", "#78BE20"),
    "NOP": ("#0C2340", "#C8102E"),
    "NYK": ("#006BB6", "#F58426"),
    "OKC": ("#007AC1", "#EF3B24"),
    "ORL": ("#0077C0", "#C4CED4"),
    "PHI": ("#006BB6", "#ED174C"),
    "PHX": ("#1D1160", "#E56020"),
    "POR": ("#E03A3E", "#000000"),
    "SAC": ("#5A2D81", "#63727A"),
    "SAS": ("#C4CED4", "#000000"),
    "TOR": ("#CE1141", "#000000"),
    "UTA": ("#002B5C", "#F9A01B"),
    "WAS": ("#002B5C", "#E31837"),
}

# ---------------------------
# ML Feature Configuration
# ---------------------------
MODEL_FEATURES = [
    "last_5_PTS", "last_10_PTS",
    "last_5_REB", "last_10_REB",
    "last_5_AST", "last_10_AST",
    "last_5_FG3M", "last_10_FG3M",
    "last_5_MIN", "last_10_MIN",
    "PTS_trend_5", "MIN_trend_5",
]

PRED_TARGETS = ["PTS", "REB", "AST", "FG3M"]

# ---------------------------
# Cached data
# ---------------------------
@st.cache_data
def load_player_names():
    return sorted([p["full_name"] for p in players.get_players()])


@st.cache_data(ttl=3600)
def cached_fetch_player_logs(player_name):
    return fetch_player_logs(player_name)

def player_headshot(player_id):
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

def team_logo_from_abbr(abbr):
    team_id = TEAM_ABBR_TO_ID.get(abbr)
    if not team_id:
        return ""
    return f"https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"


player_list = load_player_names()

# ---------------------------
# Search
# ---------------------------
player_name = st.selectbox(
    "Search player (first or last name)",
    options=player_list,
    index=None,
    placeholder="e.g. Curry, Jokic, Luka"
)

fetch_btn = st.button("Fetch Game Logs")

if fetch_btn and player_name:
    with st.spinner("Fetching game logs..."):
        st.session_state["logs"] = cached_fetch_player_logs(player_name)

# ---------------------------
# Main UI
# ---------------------------
if "logs" not in st.session_state:
    st.stop()

logs = st.session_state["logs"].copy()

# ---------------------------
# Player Header (Gradient Banner)
# ---------------------------

player_id = logs["PLAYER_ID"].iloc[0]
player_name = logs["PLAYER_NAME"].iloc[0]
team_abbr = logs["TEAM_ABBR"].iloc[0]

# Headshot
headshot_url = f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png"

# Team logo
team_id = TEAM_ABBR_TO_ID.get(team_abbr)
team_logo_url = (
    f"https://cdn.nba.com/logos/nba/{team_id}/global/L/logo.svg"
    if team_id else ""
)

# ✅ DEFINE ONCE WITH UNIQUE KEY
is_mobile = st.checkbox(
    "📱 Mobile-friendly view",
    value=False,
    key="mobile_view_toggle"
)

# Team colors
team_colors = TEAM_COLORS.get(team_abbr, ("#111111", "#222222"))
primary, secondary = team_colors

# Responsive sizing
avatar_size = 72 if is_mobile else 88
logo_size = 56 if is_mobile else 72

st.markdown(
f"""
<div style="background:
linear-gradient(135deg,{primary},{secondary}),
radial-gradient(circle at left,rgba(255,255,255,0.12),transparent 65%);
border-radius:16px;
padding:18px;
margin:12px 0 20px 0;
color:white;">
    <div style="display:flex;align-items:center;gap:18px;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:18px;">
            <img src="{headshot_url}"
                 style="width:{avatar_size}px;height:{avatar_size}px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,0.4);">
            <div>
                <div style="font-size:26px;font-weight:700;line-height:1;">
                    {player_name}
                </div>
                <div style="margin-top:6px;font-size:13px;color:rgba(255,255,255,0.85);">
                    {team_abbr}
                </div>
            </div>
        </div>
        {"<img src='" + team_logo_url + "' style='width:" + str(logo_size) + "px;height:" + str(logo_size) + "px;object-fit:contain;opacity:0.9;'>" if team_logo_url else ""}
    </div>
</div>
""",
unsafe_allow_html=True
)

st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

# ---------------------------
# Filters
# ---------------------------
st.subheader("Filters")

f1, f2, f3 = st.columns(3)

with f1:
    season_filter = st.selectbox(
        "Season",
        ["All"] + sorted(logs["SEASON_USED"].unique().tolist())
    )

with f2:
    opponent_filter = st.selectbox(
        "Opponent",
        ["All"] + sorted(logs["OPP_ABBR"].unique().tolist())
    )

with f3:
    recent_filter = st.selectbox(
        "Recent Games",
        ["All", "Last 5", "Last 10"]
    )

# ---------------------------
# Apply filters
# ---------------------------
filtered_logs = logs.copy()

if season_filter != "All":
    filtered_logs = filtered_logs[filtered_logs["SEASON_USED"] == season_filter]

if opponent_filter != "All":
    filtered_logs = filtered_logs[filtered_logs["OPP_ABBR"] == opponent_filter]

filtered_logs = filtered_logs.sort_values("GAME_DATE", ascending=False)

if recent_filter == "Last 5":
    filtered_logs = filtered_logs.head(5)
elif recent_filter == "Last 10":
    filtered_logs = filtered_logs.head(10)

# ---------------------------
# Season Averages (RESPECT FILTERS)
# ---------------------------
st.subheader("Season Averages")

avg_base = filtered_logs if not filtered_logs.empty else logs

season_avg = avg_base[
    ["PTS", "REB", "AST", "FG3M"]
].mean().round(2)

c1, c2, c3, c4 = st.columns(4)

c1.metric("PTS", season_avg["PTS"])
c2.metric("REB", season_avg["REB"])
c3.metric("AST", season_avg["AST"])
c4.metric("3PM", season_avg["FG3M"])

# ---------------------------
# Prop Evaluation
# ---------------------------
st.subheader("Prop Evaluation")

p1, p2, p3, p4, p5 = st.columns(5)

with p1:
    prop_type = st.selectbox(
        "Stat",
        [
            "PTS", "REB", "AST", "FG3M",
            "Pts+Reb+Ast", "Pts+Reb", "Pts+Ast", "Reb+Ast",
            "DOUBLE_DOUBLE", "TRIPLE_DOUBLE",
        ]
    )

with p2:
    # ---------------------------
    # Line selector (bettor-friendly)
    # ---------------------------

    LINE_RANGES = {
        "PTS": (0, 60),
        "REB": (0, 25),
        "AST": (0, 20),
        "FG3M": (0, 15),
        "Pts+Reb+Ast": (0, 80),
        "Pts+Reb": (0, 60),
        "Pts+Ast": (0, 60),
        "Reb+Ast": (0, 40),
        "DOUBLE_DOUBLE": (0, 1),
        "TRIPLE_DOUBLE": (0, 1),
    }

    min_line, max_line = LINE_RANGES.get(prop_type, (0, 60))

    line_options = [
        round(x * 0.5, 1)
        for x in range(int(min_line * 2), int(max_line * 2) + 1)
    ]

    prop_line = st.selectbox(
        "Line",
        options=line_options,
        index=line_options.index(0.5) if 0.5 in line_options else 0
    )

with p3:
    side = st.selectbox("Side", ["Over", "Under"])

with p4:
    odds_type = st.selectbox("Odds Type", ["American", "Decimal"])

with p5:
    odds = st.number_input(
        "Odds",
        value=-110 if odds_type == "American" else 1.91,
        step=1 if odds_type == "American" else 0.01
    )

# ---------------------------
# Hit Rate & Edge
# ---------------------------
if prop_line > 0 and not filtered_logs.empty:
    analysis_df = filtered_logs.copy()

    if side == "Over":
        analysis_df["HIT"] = analysis_df[prop_type] > prop_line
    else:
        analysis_df["HIT"] = analysis_df[prop_type] < prop_line

    total_games = len(analysis_df)
    hits = int(analysis_df["HIT"].sum())
    hit_rate_pct = hits / total_games * 100

    if odds_type == "American":
        implied_prob_pct = (
            (-odds) / ((-odds) + 100) * 100
            if odds < 0 else
            100 / (odds + 100) * 100
        )
    else:
        implied_prob_pct = (1 / odds) * 100

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
        f"""
        <div style="
            background:{edge_bg};
            padding:12px;
            border-radius:8px;
            text-align:center;
        ">
            <div style="font-size:14px;color:{edge_color};">Edge</div>
            <div style="font-size:24px;font-weight:600;color:{edge_color};">
                {edge_sign}{edge_pct:.1f}%
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------
# Game Logs
# ---------------------------
st.subheader(f"Showing {len(filtered_logs)} games")

if not is_mobile:
    # ===========================
    # DESKTOP: TABLE VIEW
    # ===========================
    table_cols = [
        "GAME_DATE",
        "MATCHUP",
        "MIN",
        "PTS",
        "REB",
        "AST",
        "FG3M",
    ]

    table_df = filtered_logs[table_cols].copy()
    table_df["GAME_DATE"] = table_df["GAME_DATE"].dt.strftime("%Y-%m-%d")

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True
    )

else:
    for _, row in filtered_logs.iterrows():

        # Parse teams safely from MATCHUP
        matchup = row["MATCHUP"]
        if "vs." in matchup:
            team, opp = matchup.split(" vs. ")
        else:
            team, opp = matchup.split(" @ ")

        st.markdown(
            f"""
            <div style="
                background:#0e0e0e;
                border-radius:14px;
                padding:14px;
                margin-bottom:14px;
                color:white;
            ">
                <!-- HEADER -->
                <div class="gamelog-card" style="display:flex;align-items:center;gap:12px;">
                    <img src="{player_headshot(row['PLAYER_ID'])}"
                         style="width:48px;height:48px;border-radius:50%;">
                    <div style="flex:1;">
                        <div style="font-weight:600;font-size:14px;">
                            {row['PLAYER_NAME']}
                        </div>
                        <div style="font-size:12px;color:#aaa;">
                            {matchup} • {row['GAME_DATE'].strftime('%Y-%m-%d')}
                        </div>
                    </div>
                    <img src="{team_logo_from_abbr(team)}"
                         style="width:32px;height:32px;">
                    <img src="{team_logo_from_abbr(opp)}"
                         style="width:32px;height:32px;">
                </div>
                <!-- STATS -->
                <div class="gamelog-card" style="
                    display:flex;
                    justify-content:space-between;
                    margin-top:14px;
                    text-align:center;
                ">
                    <div><div style="font-size:22px;font-weight:700;">{row['PTS']}</div><div style="font-size:11px;color:#aaa;">PTS</div></div>
                    <div><div style="font-size:22px;font-weight:700;">{row['REB']}</div><div style="font-size:11px;color:#aaa;">REB</div></div>
                    <div><div style="font-size:22px;font-weight:700;">{row['AST']}</div><div style="font-size:11px;color:#aaa;">AST</div></div>
                    <div><div style="font-size:22px;font-weight:700;">{row['FG3M']}</div><div style="font-size:11px;color:#aaa;">3PM</div></div>
                    <div><div style="font-size:22px;font-weight:700;">{row['Pts+Reb+Ast']}</div><div style="font-size:11px;color:#aaa;">Pts+Reb+Ast</div></div>
                    <div><div style="font-size:22px;font-weight:700;">{row['Pts+Reb']}</div><div style="font-size:11px;color:#aaa;">Pts+Reb</div></div>
                    <div><div style="font-size:22px;font-weight:700;">{row['Pts+Ast']}</div><div style="font-size:11px;color:#aaa;">Pts+Ast</div></div>
                    <div><div style="font-size:22px;font-weight:700;">{row['Reb+Ast']}</div><div style="font-size:11px;color:#aaa;">Reb+Ast</div></div>
                </div>
                <!-- FOOTER -->
                <div class="gamelog-card" style="margin-top:10px;font-size:11px;color:#aaa;">
                    ⏱ {int(row['MIN'])} min
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
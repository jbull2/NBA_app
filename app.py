import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# -------------------------------------------------
# Ensure project root on path
# -------------------------------------------------
ROOT = Path(__file__).resolve().parents[0]
sys.path.append(str(ROOT))

from services.nba_player_logs import fetch_player_logs

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="NBA Player Prop Analyzer",
    layout="wide",
)

st.title("🏀 NBA Player Prop Analyzer")

# -------------------------------------------------
# Session state init
# -------------------------------------------------
if "logs" not in st.session_state:
    st.session_state.logs = None

if "cache" not in st.session_state:
    st.session_state.cache = {}

# -------------------------------------------------
# Player search
# -------------------------------------------------
player = st.text_input(
    "Search player (full name)",
    placeholder="e.g. Nikola Jokic"
)

fetch_btn = st.button("Fetch Game Logs")

# -------------------------------------------------
# Fetch logs with loader
# -------------------------------------------------
if fetch_btn and player:
    loader = st.empty()
    loader.markdown(
        "<div style='text-align:center;font-size:22px;'>🏀 Loading game logs…</div>",
        unsafe_allow_html=True
    )

    if player not in st.session_state.cache:
        st.session_state.cache[player] = fetch_player_logs(player)

    st.session_state.logs = st.session_state.cache[player]
    loader.empty()

# -------------------------------------------------
# Main UI
# -------------------------------------------------
if st.session_state.logs is not None:

    logs = st.session_state.logs.copy()

    # -------------------------------------------------
    # Mobile toggle
    # -------------------------------------------------
    is_mobile = st.checkbox("📱 Mobile view", value=False)

    # -------------------------------------------------
    # Player header
    # -------------------------------------------------
    player_name = logs["PLAYER_NAME"].iloc[0]
    player_id = logs["PLAYER_ID"].iloc[0]
    team_abbr = logs["TEAM_ABBR"].iloc[0]

    headshot_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
    team_logo_url = f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbr.lower()}.png"

    TEAM_COLORS = {
        "DEN": ("#0E2240", "#FEC524"),
        "LAL": ("#552583", "#FDB927"),
        "BOS": ("#007A33", "#BA9653"),
        "MIL": ("#00471B", "#EEE1C6"),
        "DAL": ("#00538C", "#B8C4CA"),
        "PHX": ("#1D1160", "#E56020"),
        "GSW": ("#1D428A", "#FFC72C"),
    }

    primary, secondary = TEAM_COLORS.get(team_abbr, ("#111111", "#333333"))
    avatar_size = 72 if is_mobile else 88

    st.markdown(
        f"""
        <div style="
            background:linear-gradient(135deg,{primary},{secondary});
            border-radius:16px;
            padding:18px;
            margin:12px 0 20px 0;
            color:white;
        ">
            <div style="display:flex;align-items:center;gap:18px;">
                <img src="{headshot_url}"
                     style="width:{avatar_size}px;height:{avatar_size}px;
                            border-radius:50%;object-fit:cover;
                            border:2px solid rgba(255,255,255,0.4);">
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:14px;">
                        <div style="font-size:26px;font-weight:700;">
                            {player_name}
                        </div>
                        <img src="{team_logo_url}"
                             style="width:56px;height:56px;object-fit:contain;">
                    </div>
                    <div style="margin-top:6px;font-size:13px;color:rgba(255,255,255,0.85);">
                        {team_abbr}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------
    # Filters
    # -------------------------------------------------
    st.subheader("Filters")

    f1, f2, f3 = st.columns(3)

    with f1:
        season = st.selectbox(
            "Season",
            ["All"] + sorted(logs["SEASON_USED"].unique().tolist())
        )

    with f2:
        opponent = st.selectbox(
            "Opponent",
            ["All"] + sorted(logs["OPP_ABBR"].unique().tolist())
        )

    with f3:
        recent = st.selectbox(
            "Recent games",
            ["All", "Last 5", "Last 10"]
        )

    filtered = logs.copy()

    if season != "All":
        filtered = filtered[filtered["SEASON_USED"] == season]

    if opponent != "All":
        filtered = filtered[filtered["OPP_ABBR"] == opponent]

    filtered = filtered.sort_values("GAME_DATE", ascending=False)

    if recent == "Last 5":
        filtered = filtered.head(5)
    elif recent == "Last 10":
        filtered = filtered.head(10)

    # -------------------------------------------------
    # Prop evaluation
    # -------------------------------------------------
    st.subheader("Prop Evaluation")

    p1, p2, p3, p4 = st.columns(4)

    with p1:
        prop = st.selectbox(
            "Stat",
            ["PTS", "REB", "AST", "FG3M", "PRA", "PR", "PA", "RA"]
        )

    with p2:
        line = st.slider(
            "Line",
            0.0, 60.0, 20.0, step=0.5
        )

    with p3:
        side = st.selectbox("Side", ["Over", "Under"])

    with p4:
        odds = st.number_input("Decimal Odds", value=1.91, step=0.01)

    # -------------------------------------------------
    # Hit rate & edge
    # -------------------------------------------------
    if not filtered.empty:

        df = filtered.copy()

        if side == "Over":
            df["HIT"] = df[prop] > line
        else:
            df["HIT"] = df[prop] < line

        games = len(df)
        hits = int(df["HIT"].sum())
        hit_rate = hits / games * 100 if games else 0
        implied = (1 / odds) * 100
        edge = hit_rate - implied

        st.subheader("Hit Rate & Edge")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Games", games)
        c2.metric("Hits", hits)
        c3.metric("Hit Rate", f"{hit_rate:.1f}%")

        color = "#2e7d32" if edge > 0 else "#c62828"
        bg = "#e6f7e6" if edge > 0 else "#fdecea"
        sign = "+" if edge > 0 else ""

        c4.markdown(
            f"""
            <div style="background:{bg};padding:12px;border-radius:8px;text-align:center;">
                <div style="font-size:14px;color:{color};">Edge</div>
                <div style="font-size:24px;font-weight:700;color:{color};">
                    {sign}{edge:.1f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # -------------------------------------------------
    # Rolling context (key insight)
    # -------------------------------------------------
    st.subheader("Recent Form (Rolling Averages)")

    last = logs.iloc[0]

    r1, r2, r3, r4 = st.columns(4)

    r1.metric("PTS (L5 / L10)", f"{last['PTS_L5']:.1f} / {last['PTS_L10']:.1f}")
    r2.metric("REB (L5 / L10)", f"{last['REB_L5']:.1f} / {last['REB_L10']:.1f}")
    r3.metric("AST (L5 / L10)", f"{last['AST_L5']:.1f} / {last['AST_L10']:.1f}")
    r4.metric("PRA (L5 / L10)", f"{last['PRA_L5']:.1f} / {last['PRA_L10']:.1f}")

    # -------------------------------------------------
    # Game logs (mobile cards)
    # -------------------------------------------------
    st.subheader(f"Game Logs ({len(filtered)})")

    if is_mobile:
        for _, row in filtered.iterrows():
            st.markdown(
                f"""
                <div style="
                    background:#111;
                    border-radius:14px;
                    padding:14px;
                    margin-bottom:14px;
                    color:white;
                ">
                    <div style="font-size:13px;color:#aaa;">
                        {row['MATCHUP']} • {row['GAME_DATE'].strftime('%Y-%m-%d')}
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:10px;">
                        <div><b>{row['PTS']}</b><br><span style="font-size:11px;color:#aaa;">PTS</span></div>
                        <div><b>{row['REB']}</b><br><span style="font-size:11px;color:#aaa;">REB</span></div>
                        <div><b>{row['AST']}</b><br><span style="font-size:11px;color:#aaa;">AST</span></div>
                        <div><b>{row['FG3M']}</b><br><span style="font-size:11px;color:#aaa;">3PM</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.dataframe(
            filtered[
                [
                    "GAME_DATE",
                    "MATCHUP",
                    "MIN",
                    "PTS",
                    "REB",
                    "AST",
                    "FG3M",
                    "PRA",
                    "PTS_L5",
                    "PTS_L10",
                ]
            ],
            use_container_width=True
        )

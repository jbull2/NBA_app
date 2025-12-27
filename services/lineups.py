import streamlit as st
import pandas as pd
import re
from datetime import datetime
from nba_api.live.nba.endpoints import scoreboard, boxscore

# --- HELPER FUNCTIONS ---

def get_team_logo(team_id):
    """Returns the URL for the NBA team's primary logo."""
    return f"https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"

def format_nba_minutes(duration_str):
    """Converts NBA API duration strings (PT24M30.00S) to readable minutes (24:30)."""
    if not duration_str or duration_str in ['PT00M00S', 'PT00M00.00S', '']:
        return "0:00"
    match = re.search(r'PT(\d+)M(\d+)', duration_str)
    if match:
        return f"{match.group(1)}:{match.group(2).zfill(2)}"
    return "0:00"

@st.cache_data(ttl=5) # Short cache to keep toggle snappy but data fresh
def get_boxscore_data(game_id):
    """Fetches player stats and on-court status."""
    try:
        box = boxscore.BoxScore(game_id)
        data = box.get_dict().get('game', {})
        
        def process_players(team_data):
            players = team_data.get('players', [])
            stats_list = []
            for p in players:
                s = p.get('statistics', {})
                
                # Identify if player is currently on the court (1 = Yes, 0 = No)
                is_on_court = p.get('oncourt') == '1'
                status_label = "🟢 ON" if is_on_court else "⚪ Bench"
                
                mins_raw = s.get('minutes', 'PT00M00S')
                formatted_min = format_nba_minutes(mins_raw)
                
                # Filter: Include players who have played minutes or are currently on court
                if formatted_min != "0:00" or is_on_court:
                    stats_list.append({
                        "Status": status_label,
                        "Player": p.get('name'), 
                        "MIN": formatted_min,
                        "PTS": s.get('points', 0),
                        "REB": s.get('reboundsTotal', 0),
                        "AST": s.get('assists', 0),
                        "3PM": s.get('threePointersMade', 0),
                        "3PA": s.get('threePointersAttempted', 0),
                        "3P%": s.get('threePointersPercentage', 0) * 100,
                        "FTM": s.get('freeThrowsMade', 0),
                        "FTA": s.get('freeThrowsAttempted', 0),
                        "FT%": s.get('freeThrowsPercentage', 0) * 100,
                        "+/-": s.get('plusMinusPoints', 0)
                    })
            
            df = pd.DataFrame(stats_list)
            if not df.empty:
                # Sort: 'ON' players first, then by +/-
                df = df.sort_values(by=["Status", "+/-"], ascending=[False, False])
            return df
        
        return process_players(data.get('awayTeam', {})), process_players(data.get('homeTeam', {}))
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

# --- UI COMPONENT ---

def render_game_card(g):
    """Renders the HTML Scorecard and the Stats Expander."""
    status_text = g.get('gameStatusText', 'Unknown')
    game_status = g.get('gameStatus') # 1: Scheduled, 2: Live, 3: Final
    score_html = "VS" if game_status == 1 else f"{g['awayTeam']['score']} — {g['homeTeam']['score']}"
    
    st.markdown(f"""
    <div style="background:#111; border-radius:15px; padding:20px; border:1px solid #333; margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="text-align:center; flex:1;">
                <img src="{get_team_logo(g['awayTeam']['teamId'])}" style="width:45px;">
                <div style="font-weight:bold; color:white; font-size:14px;">{g['awayTeam']['teamTricode']}</div>
            </div>
            <div style="text-align:center; flex:1;">
                <div style="font-size:22px; font-weight:900; color:white;">{score_html}</div>
                <div style="color:{'#FF4B4B' if game_status == 2 else '#00FF00' if game_status == 3 else '#777'}; font-size:10px; font-weight:bold;">{status_text}</div>
            </div>
            <div style="text-align:center; flex:1;">
                <img src="{get_team_logo(g['homeTeam']['teamId'])}" style="width:45px;">
                <div style="font-weight:bold; color:white; font-size:14px;">{g['homeTeam']['teamTricode']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if game_status != 1:
        with st.expander(f"📊 Stats: {g['awayTeam']['teamTricode']} @ {g['homeTeam']['teamTricode']}", expanded=False):
            a_df, h_df = get_boxscore_data(g.get('gameId'))
            
            # Robust Column Configuration (No styling to prevent AttributeError)
            col_cfg = {
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Player": st.column_config.TextColumn("Player", width="medium"),
                "3P%": st.column_config.NumberColumn("3P%", format="%.0f%%"),
                "FT%": st.column_config.NumberColumn("FT%", format="%.0f%%"),
                "+/-": st.column_config.NumberColumn("+/-", format="%d")
            }
            display_cols = ["Status", "Player", "MIN", "PTS", "REB", "AST", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%", "+/-"]
            
            if not a_df.empty:
                t1, t2 = st.tabs([g['awayTeam']['teamTricode'], g['homeTeam']['teamTricode']])
                with t1: 
                    st.dataframe(a_df[display_cols], column_config=col_cfg, hide_index=True, use_container_width=True)
                with t2: 
                    st.dataframe(h_df[display_cols], column_config=col_cfg, hide_index=True, use_container_width=True)
    st.divider()

# --- REFRESH FRAGMENT ---

@st.fragment(run_every="10s")
def scoreboard_zone(hide_static):
    """Refreshes the entire scoreboard every 10 seconds."""
    try:
        board = scoreboard.ScoreBoard()
        all_games = board.get_dict().get('scoreboard', {}).get('games', [])
    except Exception:
        all_games = []

    if not all_games:
        st.warning("No games found.")
        return

    live_games = [g for g in all_games if g.get('gameStatus') == 2]
    upcoming_games = [g for g in all_games if g.get('gameStatus') == 1]
    final_games = [g for g in all_games if g.get('gameStatus') == 3]

    # 1. LIVE SECTION (Top)
    if live_games:
        st.subheader("🔥 Live Action")
        for g in live_games:
            render_game_card(g)
    else:
        st.info("No games are currently live.")

    # 2. STATIC SECTIONS (Toggle Filter)
    if not hide_static:
        if upcoming_games:
            st.subheader("🕒 Upcoming")
            for g in upcoming_games:
                render_game_card(g)

        if final_games:
            st.subheader("✅ Completed")
            for g in final_games:
                render_game_card(g)
    
    st.caption(f"Last sync: {datetime.now().strftime('%I:%M:%S %p')} • Auto-refreshing every 10s")

# --- MAIN PAGE EXPORT ---

def show_lineups_page(team_id_map):
    st.markdown("# 🏀 NBA Live Hub")
    
    # Persistent Toggle
    hide_static = st.toggle("Focus on Live Action Only", value=False)
    
    # Launch Fragment
    scoreboard_zone(hide_static)
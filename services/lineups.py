import streamlit as st
import pandas as pd
from datetime import datetime, date
from nba_api.stats.endpoints import leaguegamefinder, scoreboardv2

def get_team_logo(team_id):
    return f"https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"

def get_future_scoreboard(target_date):
    """
    Uses ScoreboardV2 to fetch matchups for a future date.
    Returns a dataframe formatted to match the UI's expectations.
    """
    try:
        # ScoreboardV2 returns all games for one specific day
        sb = scoreboardv2.ScoreboardV2(
            game_date=target_date.strftime("%Y-%m-%d"),
            league_id="00"
        )
        df_raw = sb.game_header.get_data_frame()
        
        if df_raw.empty:
            return pd.DataFrame()

        processed_games = []
        for _, row in df_raw.iterrows():
            # We create two entries per game (Home/Away) to match LeagueGameFinder format
            game_id = row['GAME_ID']
            home_id = row['HOME_TEAM_ID']
            away_id = row['VISITOR_TEAM_ID']
            
            # Extract Team Abbs from GAMECODE (e.g., "20251226/MIAATL" -> MIA and ATL)
            # Or use a mapping. Since GAMECODE is reliable:
            teams_str = row['GAMECODE'].split('/')[-1]
            away_abbr = teams_str[:3]
            home_abbr = teams_str[3:]

            # Common data
            common = {
                "GAME_ID": game_id,
                "GAME_DATE": target_date,
                "IS_FUTURE": True,
                "GAME_STATUS_TEXT": row['GAME_STATUS_TEXT'] # e.g. "7:00 pm ET"
            }

            # Away Row
            processed_games.append({
                **common,
                "TEAM_ID": away_id,
                "TEAM_ABBREVIATION": away_abbr,
                "MATCHUP": f"{away_abbr} @ {home_abbr}",
                "PTS": None, "WL": None
            })
            # Home Row
            processed_games.append({
                **common,
                "TEAM_ID": home_id,
                "TEAM_ABBREVIATION": home_abbr,
                "MATCHUP": f"{home_abbr} vs. {away_abbr}",
                "PTS": None, "WL": None
            })

        return pd.DataFrame(processed_games)
    except Exception as e:
        st.error(f"Scoreboard Error: {e}")
        return pd.DataFrame()

def show_lineups_page(team_id_map):
    st.markdown("## 🗓️ NBA Game Schedule & Results")
    
    selected_date = st.date_input("Select Date", date.today())
    st.divider()

    # --- ROUTING ---
    if selected_date < date.today():
        # PAST: Use LeagueGameFinder
        try:
            date_str = selected_date.strftime('%m/%d/%Y')
            finder = leaguegamefinder.LeagueGameFinder(
                date_from_nullable=date_str,
                date_to_nullable=date_str,
                league_id_nullable='00'
            )
            df = finder.get_data_frames()[0]
            df['IS_FUTURE'] = False
        except:
            df = pd.DataFrame()
    else:
        # TODAY or FUTURE: Use ScoreboardV2
        # (ScoreboardV2 is better for "Today" because it shows live status/times)
        df = get_future_scoreboard(selected_date)

    if df.empty:
        st.info(f"No games found for {selected_date.strftime('%B %d, %Y')}.")
        return

    # --- RENDERING ---
    home_games = df[df['MATCHUP'].str.contains(' vs. ')]

    for _, home_row in home_games.iterrows():
        try:
            away_row = df[(df['GAME_ID'] == home_row['GAME_ID']) & (df['MATCHUP'].str.contains(' @ '))].iloc[0]
        except:
            continue

        is_future = home_row.get('IS_FUTURE', False)
        h_pts = home_row.get('PTS')
        a_pts = away_row.get('PTS')
        
        # Display Logic
        if is_future:
            score_display = "VS"
            # Use the actual tip-off time from the API
            status_text = home_row.get('GAME_STATUS_TEXT', 'UPCOMING')
        else:
            score_display = f"{int(a_pts)} - {int(h_pts)}" if pd.notnull(h_pts) else "VS"
            status_text = "FINAL"
        
        h_color = "#3b82f6" if home_row.get('WL') == 'W' else "white"
        a_color = "#3b82f6" if away_row.get('WL') == 'W' else "white"

        card_html = f"""
        <div style="background:#0f0f0f; border-radius:12px; padding:20px; margin-bottom:15px; border:1px solid #222; display:flex; justify-content:space-between; align-items:center;">
            <div style="text-align:center; flex:1;">
                <img src="{get_team_logo(away_row['TEAM_ID'])}" style="width:50px;">
                <div style="color:{a_color}; font-weight:800; margin-top:5px;">{away_row['TEAM_ABBREVIATION']}</div>
            </div>
            <div style="text-align:center; flex:1.5;">
                <div style="font-size:26px; font-weight:900; color:white;">{score_display}</div>
                <div style="font-size:11px; color:#555; font-weight:700; margin-top:8px;">{status_text}</div>
            </div>
            <div style="text-align:center; flex:1;">
                <img src="{get_team_logo(home_row['TEAM_ID'])}" style="width:50px;">
                <div style="color:{h_color}; font-weight:800; margin-top:5px;">{home_row['TEAM_ABBREVIATION']}</div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
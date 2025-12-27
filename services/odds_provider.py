import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Retrieve the API key from the environment
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_au_odds():
    """
    Fetches H2H, Spreads, and Totals from Australian bookmakers 
    using the key from the .env file.
    """
    if not ODDS_API_KEY:
        st.error("ODDS_API_KEY not found in .env file.")
        return pd.DataFrame()

    url = 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'au',
        'markets': 'h2h,spreads,totals',
        'dateFormat': 'iso',
        'oddsFormat': 'decimal'
    }
    
    # Australian bookmakers you specified
    selected_bookmakers = [
        'TAB', 'SportsBet', 'Bet Right', 'Betr', 'PointsBet (AU)', 
        'PlayUp', 'Neds', 'Ladbrokes', 'Unibet', 'TABtouch'
    ]
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Mapping logic (Simplified for brevity, use the full map in your lineups.py)
        # In a real app, you might want to move TEAM_NAME_TO_ABBR here 
        # to normalize names before they reach the UI.
        
        rows = []
        for game in data:
            for bm in game.get('bookmakers', []):
                title = bm.get('title')
                if title not in selected_bookmakers:
                    continue
                
                row = {
                    'game_id': game['id'],
                    'home_team_full': game['home_team'],
                    'away_team_full': game['away_team'],
                    'bookmaker': title,
                    'h2h_h': None, 'h2h_a': None,
                    'spr_h': None, 'spr_h_o': None,
                    'tot': None, 'ov': None, 'un': None
                }
                
                for mkt in bm.get('markets', []):
                    out = mkt.get('outcomes', [])
                    if mkt['key'] == 'h2h':
                        for o in out:
                            if o['name'] == game['home_team']: row['h2h_h'] = o['price']
                            else: row['h2h_a'] = o['price']
                    elif mkt['key'] == 'spreads':
                        for o in out:
                            if o['name'] == game['home_team']:
                                row['spr_h'], row['spr_h_o'] = o['point'], o['price']
                    elif mkt['key'] == 'totals':
                        for o in out:
                            row['tot'] = o['point']
                            if o['name'] == 'Over': row['ov'] = o['price']
                            else: row['un'] = o['price']
                rows.append(row)
                
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error fetching odds: {e}")
        return pd.DataFrame()
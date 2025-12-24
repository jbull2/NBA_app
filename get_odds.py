import os
import requests
from datetime import datetime
from dateutil import tz
from dotenv import load_dotenv

# Load env
load_dotenv()
API_KEY = os.getenv("ODDS_API_KEY")
if not API_KEY:
    raise RuntimeError("ODDS_API_KEY not found in .env")

AEST = tz.gettz("Australia/Sydney")
TARGET_DATE = datetime(2025, 12, 24).date()

# 1) Get all NBA events
events = requests.get(
    "https://api.the-odds-api.com/v4/sports/basketball_nba/events",
    params={"apiKey": API_KEY},
).json()

# 2) Filter by date (AEDT)
events_for_date = []
for e in events:
    commence = datetime.fromisoformat(
        e["commence_time"].replace("Z", "+00:00")
    )
    if commence.astimezone(AEST).date() == TARGET_DATE:
        events_for_date.append(e)

print(f"Found {len(events_for_date)} games on {TARGET_DATE}")

# 3) Fetch historical odds per event
all_odds = []
for e in events_for_date:
    odds = requests.get(
        f"https://api.the-odds-api.com/v4/historical/sports/basketball_nba/events/{e['id']}/odds",
        params={
            "apiKey": API_KEY,
            # midpoint of the day avoids missing games
            "date": "2025-12-24T12:00:00Z",
            "regions": "au",
            "markets": "player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists,player_points_rebounds,player_points_assists,player_rebounds_assists,player_double_double,player_triple_double",
        },
    ).json()
    all_odds.append(odds)

print(f"Fetched odds for {len(all_odds)} games")
print(all_odds)

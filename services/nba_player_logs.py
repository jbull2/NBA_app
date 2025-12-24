import pandas as pd
import time
from functools import lru_cache

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog


# ---------------------------
# Image helpers (UI-safe)
# ---------------------------
def player_headshot_url(player_id: int) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"


def team_logo_url(team_abbr: str) -> str:
    return f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbr.lower()}.png"


# ---------------------------
# Cached wrapper
# ---------------------------
@lru_cache(maxsize=128)
def fetch_player_logs_cached(player_name, end_year, years_back):
    return fetch_player_logs(player_name, end_year, years_back)


# ---------------------------
# Main fetch
# ---------------------------
def fetch_player_logs(
    player_name: str,
    end_year: int = 2026,
    years_back: int = 5
) -> pd.DataFrame:
    """
    Fetch multi-season NBA game logs for a single player.
    Stable version: NO pace, NO usage, NO external joins.
    """

    # ---------------------------
    # Resolve player
    # ---------------------------
    found = players.find_players_by_full_name(player_name)
    if not found:
        raise ValueError(f"Player not found: {player_name}")

    player_id = found[0]["id"]

    # ---------------------------
    # Seasons to fetch (e.g. 2025-26)
    # ---------------------------
    seasons = [
        f"{y-1}-{str(y)[2:]}"
        for y in range(end_year, end_year - years_back - 1, -1)
    ]

    all_logs = []

    # ---------------------------
    # Fetch game logs
    # ---------------------------
    for season in seasons:
        try:
            df = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season
            ).get_data_frames()[0]
        except Exception:
            df = pd.DataFrame()

        if not df.empty:
            df = df.copy()
            df["SEASON_USED"] = season
            all_logs.append(df)

        time.sleep(0.2)  # rate-limit safety

    if not all_logs:
        raise ValueError("No game logs found for any season.")

    logs = pd.concat(all_logs, ignore_index=True)

    # ---------------------------
    # Clean & sort
    # ---------------------------
    logs["GAME_DATE"] = pd.to_datetime(
        logs["GAME_DATE"],
        errors="coerce"
    )
    logs = logs.dropna(subset=["GAME_DATE"])
    logs = logs.sort_values("GAME_DATE", ascending=False)
    logs = logs[logs["MIN"] > 0].reset_index(drop=True)

    # ---------------------------
    # Opponent abbreviation (FIX)
    # ---------------------------
    # ---------------------------
    # Player team abbreviation (SAFE)
    # ---------------------------
    logs["TEAM_ABBR"] = logs["MATCHUP"].str[:3]
    logs["OPP_ABBR"] = logs["MATCHUP"].str[-3:]

    # ---------------------------
    # Metadata (UI-safe)
    # ---------------------------
    logs["PLAYER_NAME"] = player_name
    logs["PLAYER_ID"] = player_id

    # ---------------------------
    # Team / Opponent extraction
    # ---------------------------
    logs["TEAM"] = logs["MATCHUP"].str[:3]
    logs["OPPONENT"] = logs["MATCHUP"].str[-3:]

    # ---------------------------
    # Image URLs for UI
    # ---------------------------
    logs["HEADSHOT_URL"] = player_headshot_url(player_id)
    logs["TEAM_LOGO_URL"] = logs["TEAM"].apply(team_logo_url)
    logs["OPP_LOGO_URL"] = logs["OPPONENT"].apply(team_logo_url)

    # ---------------------------
    # Derived prop stats
    # ---------------------------
    logs["Pts+Reb+Ast"] = logs["PTS"] + logs["REB"] + logs["AST"]
    logs["Pts+Reb"] = logs["PTS"] + logs["REB"]
    logs["Pts+Ast"] = logs["PTS"] + logs["AST"]
    logs["Reb+Ast"] = logs["REB"] + logs["AST"]

    # ---------------------------
    # Double / Triple Double
    # ---------------------------
    dd_count = (
        (logs["PTS"] >= 10).astype(int) +
        (logs["REB"] >= 10).astype(int) +
        (logs["AST"] >= 10).astype(int)
    )

    logs["DOUBLE_DOUBLE"] = (dd_count >= 2).astype(int)
    logs["TRIPLE_DOUBLE"] = (dd_count >= 3).astype(int)

    return logs

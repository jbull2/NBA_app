import time
import pandas as pd
from functools import lru_cache

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog


# ---------------------------
# Rolling feature helper
# ---------------------------
def add_rolling_features(df: pd.DataFrame, cols=None) -> pd.DataFrame:
    """
    Adds rolling L5 and L10 averages for specified columns.
    Uses previous games only (no leakage).
    """
    df = df.copy()

    if cols is None:
        cols = [
            "MIN",
            "PTS", "REB", "AST", "FG3M",
            "PRA", "PR", "PA", "RA",
        ]

    # oldest → newest for rolling
    df = df.sort_values("GAME_DATE", ascending=True)

    for col in cols:
        if col in df.columns:
            df[f"{col}_L5"] = (
                df[col]
                .shift(1)
                .rolling(window=5, min_periods=1)
                .mean()
            )

            df[f"{col}_L10"] = (
                df[col]
                .shift(1)
                .rolling(window=10, min_periods=1)
                .mean()
            )

    # return newest → oldest for UI
    df = df.sort_values("GAME_DATE", ascending=False).reset_index(drop=True)
    return df


# ---------------------------
# Cached wrapper
# ---------------------------
@lru_cache(maxsize=128)
def fetch_player_logs_cached(player_name: str, end_year: int, years_back: int):
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
    Includes derived stats + rolling features (L5/L10).
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
    # Fetch game logs per season
    # ---------------------------
    for season in seasons:
        try:
            df = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season
            ).get_data_frames()[0]
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            continue

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
    # Team / Opponent (safe parse)
    # ---------------------------
    logs["TEAM_ABBR"] = logs["MATCHUP"].astype(str).str[:3]
    logs["OPP_ABBR"] = logs["MATCHUP"].astype(str).str[-3:]

    # ---------------------------
    # Metadata (UI-safe)
    # ---------------------------
    logs["PLAYER_NAME"] = player_name
    logs["PLAYER_ID"] = player_id

    # ---------------------------
    # Derived prop stats
    # ---------------------------
    logs["PRA"] = logs["PTS"] + logs["REB"] + logs["AST"]
    logs["PR"] = logs["PTS"] + logs["REB"]
    logs["PA"] = logs["PTS"] + logs["AST"]
    logs["RA"] = logs["REB"] + logs["AST"]

    # Backwards-compatible labels (if UI still uses them)
    logs["Pts+Reb+Ast"] = logs["PRA"]
    logs["Pts+Reb"] = logs["PR"]
    logs["Pts+Ast"] = logs["PA"]
    logs["Reb+Ast"] = logs["RA"]

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

    # ---------------------------
    # Rolling features (L5 / L10)
    # ---------------------------
    logs = add_rolling_features(
        logs,
        cols=[
            "MIN",
            "PTS", "REB", "AST", "FG3M",
            "PRA", "PR", "PA", "RA",
        ]
    )

    return logs
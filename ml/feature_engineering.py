import pandas as pd

def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("GAME_DATE").reset_index(drop=True)

    stats = ["PTS", "REB", "AST", "FG3M", "MIN"]
    windows = [5, 10]

    for stat in stats:
        for w in windows:
            df[f"{stat}_L{w}"] = (
                df[stat]
                .rolling(window=w, min_periods=w)
                .mean()
            )

    return df
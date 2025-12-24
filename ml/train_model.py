import pandas as pd
import joblib
from pathlib import Path

from services.nba_player_logs import fetch_player_logs
from NBA_app.ml.feature_engineering import add_rolling_features

from sklearn.ensemble import RandomForestRegressor

# -------------------------
# Config
# -------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

TARGETS = ["PTS", "REB", "AST", "FG3M"]

FEATURES = [
    "MIN_L5", "MIN_L10",
    "PTS_L5", "REB_L5", "AST_L5", "FG3M_L5",
    "PTS_L10", "REB_L10", "AST_L10", "FG3M_L10",
]

# -------------------------
# Load training data
# -------------------------
def load_training_data(player_name: str):
    df = fetch_player_logs(player_name)
    df = add_rolling_features(df)

    df = df.dropna(subset=FEATURES + TARGETS)
    return df


# -------------------------
# Train models
# -------------------------
def train_models(player_name: str):
    df = load_training_data(player_name)

    X = df[FEATURES]

    models = {}

    for target in TARGETS:
        y = df[target]

        model = RandomForestRegressor(
            n_estimators=200,
            random_state=42
        )
        model.fit(X, y)

        models[target] = model

        joblib.dump(
            model,
            MODEL_DIR / f"{player_name}_{target}.joblib"
        )

    print(f"✅ Models trained for {player_name}")
    print("Features used:", FEATURES)


if __name__ == "__main__":
    # Example training run
    train_models("Nikola Jokic")
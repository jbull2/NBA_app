# 🏀 NBA Player Game Log & Prop Analysis App

A Streamlit application for exploring NBA player game logs, season averages, opponent splits, and prop-style statistical analysis in a clean, mobile-friendly interface.

This project focuses on **data exploration and betting analysis** — no machine learning is required.

---

## 🚀 Features

- 🔍 Player search with autocomplete
- 📊 Full historical game logs (multi-season)
- 🎯 Filters:
  - Season
  - Opponent
  - Last 5 / Last 10 games
- 📈 Season averages (PTS / REB / AST / 3PM)
- 💰 Prop-style analysis:
  - Over / Under evaluation
  - Hit rate
  - Edge vs implied odds
- 📱 Mobile-friendly game log cards
- 🖥️ Desktop tabular view for detailed analysis
- 🧢 Player headshots & team branding

---

## 📁 Project Structure

NBA_app/
├── app.py
├── main.py
├── services/
│ ├── init.py
│ └── nba_player_logs.py
├── ui/
│ ├── init.py
│ └── get_odds.py
├── venv/
├── README.md
└── requirements.txt

## 🖥️ Getting Started (Windows)

### 1️⃣ Navigate to the project directory

```powershell
cd NBA_app
```

### 2️⃣ Activate the virtual environment
venv\Scripts\Activate.ps1

If PowerShell blocks execution, run:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

### 3️⃣ Install dependencies
pip install streamlit pandas numpy nba_api

Tip: Always ensure the virtual environment is active before installing packages.

### 4️⃣ Run the Streamlit app
python -m streamlit run app.py

The app will open automatically in your browser at:

http://localhost:8501

🏀📊 Data Source

All NBA data is fetched live using:

nba_api (https://github.com/swar/nba_api)
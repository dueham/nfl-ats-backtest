"""
NFL ATS 3-Factor System — Streamlit App (v5)
=============================================
- LIVE ODDS via The Odds API (env var: ODDS_API_KEY)
- Auto-detects current NFL week and shows upcoming games
- Top 4 books side-by-side for line shopping
- Bet tracking with Railway persistent volume
- Historical backtest for validation
- Circa Stadium Swim theme
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os

st.set_page_config(
    page_title="Sir Ron's Sharp Signal",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# CIRCA STADIUM SWIM COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════
TWILIGHT_DARK = "#1A1B3A"
TWILIGHT_MID  = "#2B2D5C"
POOL_CYAN     = "#00D4FF"
POOL_DEEP     = "#0088B8"
SCREEN_WHITE  = "#F0F5FA"
AMBER_GOLD    = "#FFB84D"
AMBER_DEEP    = "#E89A2E"
SUNSET_CORAL  = "#FF6B7A"
CORAL_DEEP    = "#D84556"
NEON_MINT     = "#4EFFA8"
CLOUD_GRAY    = "#8891B0"
NIGHT_BLACK   = "#0A0B1E"

# ═══════════════════════════════════════════════════════════════════════════
# STYLING
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Bebas+Neue&display=swap');

    .stApp {{
        background: linear-gradient(180deg, {TWILIGHT_DARK} 0%, {NIGHT_BLACK} 100%);
        color: {SCREEN_WHITE};
    }}
    p, div, span, label {{ color: {SCREEN_WHITE}; }}
    h1, h2, h3, h4, h5, h6 {{ color: {SCREEN_WHITE}; font-family: 'Inter', sans-serif; font-weight: 700; }}

    .header-banner {{
        background: linear-gradient(135deg, {TWILIGHT_MID} 0%, {POOL_DEEP} 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 2px solid {POOL_CYAN};
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
        position: relative;
        overflow: hidden;
    }}
    .header-banner::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 30% 20%, rgba(0, 212, 255, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(255, 184, 77, 0.1) 0%, transparent 50%);
        pointer-events: none;
    }}
    .header-banner h1 {{
        color: {SCREEN_WHITE};
        margin: 0;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.4rem;
        letter-spacing: 2px;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        position: relative;
    }}
    .header-banner p {{
        color: {AMBER_GOLD};
        margin: 0.4rem 0 0 0;
        font-size: 0.95rem;
        font-style: italic;
        letter-spacing: 1px;
        position: relative;
    }}

    [data-testid="stMetric"] {{
        background: linear-gradient(135deg, {TWILIGHT_MID} 0%, rgba(43, 45, 92, 0.6) 100%);
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 4px solid {AMBER_GOLD};
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }}
    [data-testid="stMetricValue"] {{
        color: {POOL_CYAN};
        font-weight: 800;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.2rem;
        letter-spacing: 1px;
    }}
    [data-testid="stMetricLabel"] {{
        color: {AMBER_GOLD};
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 1.5px;
    }}
    [data-testid="stMetricDelta"] {{ color: {CLOUD_GRAY}; }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {NIGHT_BLACK} 0%, {TWILIGHT_DARK} 100%);
        border-right: 1px solid {POOL_DEEP};
    }}
    section[data-testid="stSidebar"] * {{ color: {SCREEN_WHITE} !important; }}
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{ color: {AMBER_GOLD} !important; }}

    .stSlider [data-baseweb="slider"] > div > div > div {{ background: {POOL_CYAN}; }}

    .stButton > button {{
        background: linear-gradient(135deg, {POOL_CYAN} 0%, {POOL_DEEP} 100%);
        color: {NIGHT_BLACK};
        border: none;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        box-shadow: 0 2px 8px rgba(0, 212, 255, 0.3);
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 212, 255, 0.5);
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: {NIGHT_BLACK};
        padding: 6px;
        border-radius: 10px;
        border: 1px solid {TWILIGHT_MID};
    }}
    .stTabs [data-baseweb="tab"] {{
        background: {TWILIGHT_MID};
        border-radius: 6px;
        padding: 12px 24px;
        font-weight: 700;
        color: {CLOUD_GRAY};
        letter-spacing: 1px;
        border: 1px solid transparent;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {POOL_DEEP} 0%, {POOL_CYAN} 100%) !important;
        color: {NIGHT_BLACK} !important;
        border: 1px solid {AMBER_GOLD} !important;
        box-shadow: 0 0 12px rgba(0, 212, 255, 0.4);
    }}

    .callout {{
        color: {SCREEN_WHITE};
        padding: 1.5rem 2rem;
        border-radius: 12px;
        border-left: 6px solid {AMBER_GOLD};
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }}
    .callout h2 {{
        color: {SCREEN_WHITE};
        margin: 0 0 0.5rem 0;
        font-family: 'Bebas Neue', sans-serif;
        letter-spacing: 2px;
        font-size: 1.8rem;
    }}

    .info-banner {{
        background: rgba(255, 184, 77, 0.1);
        border-left: 4px solid {AMBER_GOLD};
        padding: 0.9rem 1.2rem;
        border-radius: 6px;
        margin: 0.75rem 0 1.25rem 0;
        color: {AMBER_GOLD};
        font-size: 0.9rem;
    }}
    .live-banner {{
        background: rgba(78, 255, 168, 0.1);
        border-left: 4px solid {NEON_MINT};
        padding: 0.9rem 1.2rem;
        border-radius: 6px;
        margin: 0.75rem 0 1.25rem 0;
        color: {NEON_MINT};
        font-size: 0.9rem;
    }}
    .warn-banner {{
        background: rgba(255, 107, 122, 0.1);
        border-left: 4px solid {SUNSET_CORAL};
        padding: 0.9rem 1.2rem;
        border-radius: 6px;
        margin: 0.75rem 0 1.25rem 0;
        color: {SUNSET_CORAL};
        font-size: 0.9rem;
    }}

    .pick-card {{
        background: linear-gradient(135deg, {TWILIGHT_MID} 0%, rgba(43, 45, 92, 0.8) 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 10px;
        border-left: 5px solid {POOL_CYAN};
        margin-bottom: 1rem;
        box-shadow: 0 2px 12px rgba(0, 212, 255, 0.15);
    }}
    .pick-card.watch {{ border-left-color: {AMBER_GOLD}; box-shadow: 0 2px 12px rgba(255, 184, 77, 0.15); }}
    .pick-card.no {{ border-left-color: {CORAL_DEEP}; opacity: 0.6; }}
    .pick-card h3 {{
        margin: 0 0 0.35rem 0;
        color: {SCREEN_WHITE};
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
    }}
    .pick-card p {{
        margin: 0.2rem 0;
        color: {CLOUD_GRAY};
        font-size: 0.9rem;
    }}
    .pick-card .factor-row {{
        display: flex; gap: 0.6rem; margin-top: 0.7rem; flex-wrap: wrap;
    }}
    .factor-chip {{
        padding: 0.25rem 0.8rem;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
    }}
    .factor-chip.on {{ background: {NEON_MINT}; color: {NIGHT_BLACK}; }}
    .factor-chip.off {{ background: {CORAL_DEEP}; color: {SCREEN_WHITE}; }}

    /* Odds board — compact side-by-side */
    .odds-board {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 8px;
        margin: 0.75rem 0;
    }}
    .odds-cell {{
        background: rgba(0, 212, 255, 0.08);
        border: 1px solid rgba(0, 212, 255, 0.25);
        border-radius: 6px;
        padding: 8px 10px;
        text-align: center;
    }}
    .odds-cell.best {{
        background: rgba(78, 255, 168, 0.15);
        border-color: {NEON_MINT};
        box-shadow: 0 0 12px rgba(78, 255, 168, 0.3);
    }}
    .odds-book {{
        color: {CLOUD_GRAY};
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }}
    .odds-line {{
        color: {SCREEN_WHITE};
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.4rem;
        letter-spacing: 1px;
    }}
    .odds-price {{
        color: {AMBER_GOLD};
        font-size: 0.8rem;
        font-weight: 600;
    }}
    .odds-cell.best .odds-book {{ color: {NEON_MINT}; }}

    [data-testid="stDataFrame"] {{
        background: {TWILIGHT_MID};
        border-radius: 8px;
        border: 1px solid {POOL_DEEP};
    }}
    .stTextInput input, .stNumberInput input, .stDateInput input {{
        background: {TWILIGHT_MID};
        color: {SCREEN_WHITE};
        border: 1px solid {POOL_DEEP};
    }}
    .stSelectbox > div > div {{
        background: {TWILIGHT_MID};
        color: {SCREEN_WHITE};
    }}
    div[data-baseweb="notification"] {{
        background: {TWILIGHT_MID};
        border-radius: 8px;
    }}
    .streamlit-expanderHeader {{
        background: {TWILIGHT_MID};
        color: {AMBER_GOLD};
        border-radius: 6px;
    }}
    hr {{ border-color: {POOL_DEEP}; opacity: 0.4; }}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="header-banner">
    <h1>🏈 SIR RON'S SHARP SIGNAL</h1>
    <p>3-Factor NFL ATS System · Live Odds · EPA + Line Movement + Situational Edge</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG — API key from env var
# ═══════════════════════════════════════════════════════════════════════════
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "").strip()
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Books to display (top 4 US books)
PREFERRED_BOOKS = ["draftkings", "fanduel", "betmgm", "caesars"]
BOOK_DISPLAY = {
    "draftkings": "DK",
    "fanduel": "FD",
    "betmgm": "MGM",
    "caesars": "CZR",
    "pointsbetus": "PB",
    "wynnbet": "Wynn",
    "betrivers": "BR",
    "unibet_us": "UB",
}

# ═══════════════════════════════════════════════════════════════════════════
# TEAM NAME MAPPING — Odds API uses full names, nflverse uses abbreviations
# ═══════════════════════════════════════════════════════════════════════════
TEAM_NAME_TO_ABBR = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL", "Denver Broncos": "DEN",
    "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN", "New England Patriots": "NE",
    "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT", "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


# ═══════════════════════════════════════════════════════════════════════════
# BET LOG PERSISTENCE (Railway volume mounted at /data)
# ═══════════════════════════════════════════════════════════════════════════
BETS_FILE = Path(os.environ.get("BETS_FILE_PATH", "/data/bets.csv"))
if not BETS_FILE.parent.exists():
    BETS_FILE = Path("bets.csv")
else:
    BETS_FILE.parent.mkdir(parents=True, exist_ok=True)

BET_COLUMNS = [
    "bet_id", "logged_at", "season", "week", "game_date",
    "sharp_side", "opponent", "location", "spread", "amount",
    "odds", "book", "bet_source",
    "factor_score", "epa_gap", "result", "profit"
]


def load_bets() -> pd.DataFrame:
    if BETS_FILE.exists():
        try:
            df = pd.read_csv(BETS_FILE)
            for col in BET_COLUMNS:
                if col not in df.columns:
                    df[col] = np.nan
            return df[BET_COLUMNS]
        except Exception:
            pass
    return pd.DataFrame(columns=BET_COLUMNS)


def save_bets(df: pd.DataFrame):
    df.to_csv(BETS_FILE, index=False)


def american_to_profit(amount: float, odds: int) -> float:
    if odds > 0:
        return amount * (odds / 100)
    else:
        return amount * (100 / abs(odds))


def calc_bet_profit(amount: float, odds: int, result: str) -> float:
    if result == "WIN":
        return american_to_profit(amount, odds)
    if result == "LOSS":
        return -amount
    if result == "PUSH":
        return 0.0
    return np.nan


def add_bet(bet_dict: dict):
    df = load_bets()
    bet_dict.setdefault("bet_id", int(datetime.now().timestamp() * 1000))
    bet_dict.setdefault("logged_at", datetime.now().isoformat(timespec="seconds"))
    for col in BET_COLUMNS:
        bet_dict.setdefault(col, np.nan)
    new_row = pd.DataFrame([bet_dict])[BET_COLUMNS]
    df = pd.concat([df, new_row], ignore_index=True)
    save_bets(df)


# ═══════════════════════════════════════════════════════════════════════════
# LIVE ODDS from The Odds API
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, ttl=3600)  # 1-hour cache — respect API quota
def fetch_live_odds() -> pd.DataFrame:
    """
    Pull current NFL spreads from The Odds API.
    Returns one row per game with spreads from each preferred book.
    """
    if not ODDS_API_KEY:
        return pd.DataFrame()

    url = f"{ODDS_API_BASE}/sports/americanfootball_nfl/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "spreads",
        "oddsFormat": "american",
        "bookmakers": ",".join(PREFERRED_BOOKS + ["betrivers", "pointsbetus"]),
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
    except Exception as e:
        st.session_state["odds_error"] = str(e)
        return pd.DataFrame()

    # Track API usage from response headers
    remaining = r.headers.get("x-requests-remaining", "?")
    used = r.headers.get("x-requests-used", "?")
    st.session_state["odds_api_remaining"] = remaining
    st.session_state["odds_api_used"] = used

    games = r.json()
    if not games:
        return pd.DataFrame()

    rows = []
    for g in games:
        home = g.get("home_team")
        away = g.get("away_team")
        commence = g.get("commence_time")
        home_abbr = TEAM_NAME_TO_ABBR.get(home, home)
        away_abbr = TEAM_NAME_TO_ABBR.get(away, away)

        row = {
            "game_id": g.get("id"),
            "home_team": home_abbr,
            "away_team": away_abbr,
            "home_full": home,
            "away_full": away,
            "commence_time": commence,
        }

        # Per-book spreads (from home team perspective)
        for bm in g.get("bookmakers", []):
            book_key = bm.get("key")
            if book_key not in BOOK_DISPLAY:
                continue
            for market in bm.get("markets", []):
                if market.get("key") != "spreads":
                    continue
                for outcome in market.get("outcomes", []):
                    team = outcome.get("name")
                    point = outcome.get("point")
                    price = outcome.get("price")
                    if team == home:
                        row[f"{book_key}_home_spread"] = point
                        row[f"{book_key}_home_price"] = price
                    elif team == away:
                        row[f"{book_key}_away_spread"] = point
                        row[f"{book_key}_away_price"] = price
        rows.append(row)

    df = pd.DataFrame(rows)
    if len(df) > 0:
        df["commence_time"] = pd.to_datetime(df["commence_time"], errors="coerce")
    return df


def consensus_home_spread(row: pd.Series) -> float:
    """Median home spread across available books — used as 'the line' for scoring."""
    vals = []
    for book in PREFERRED_BOOKS:
        col = f"{book}_home_spread"
        if col in row and pd.notna(row[col]):
            vals.append(row[col])
    return np.median(vals) if vals else np.nan


# ═══════════════════════════════════════════════════════════════════════════
# nflverse loaders (for EPA + schedule fallback + backtest)
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, ttl=3600)
def load_play_by_play(season: int) -> pd.DataFrame:
    url = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=180)
    r.raise_for_status()
    return pd.read_parquet(BytesIO(r.content))


@st.cache_data(show_spinner=False, ttl=3600)
def load_schedules() -> pd.DataFrame:
    url = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    r.raise_for_status()
    return pd.read_csv(BytesIO(r.content), low_memory=False)


@st.cache_data(show_spinner=False)
def compute_lagged_epa(seasons_tuple: tuple) -> pd.DataFrame:
    frames = [load_play_by_play(s) for s in seasons_tuple]
    pbp = pd.concat(frames, ignore_index=True)
    plays = pbp[
        (pbp["play_type"].isin(["pass", "run"]))
        & (pbp["epa"].notna())
        & (pbp["posteam"].notna())
        & (pbp["defteam"].notna())
    ].copy()
    off = plays.groupby(["season", "week", "posteam"])["epa"].mean().reset_index().rename(
        columns={"posteam": "team", "epa": "off_epa"})
    dfn = plays.groupby(["season", "week", "defteam"])["epa"].mean().reset_index().rename(
        columns={"defteam": "team", "epa": "def_epa"})
    weekly = off.merge(dfn, on=["season", "week", "team"], how="outer")
    weekly["net_epa"] = weekly["off_epa"] - weekly["def_epa"]
    weekly = weekly.sort_values(["team", "season", "week"]).reset_index(drop=True)
    weekly["rolling_net_epa"] = (
        weekly.groupby(["team", "season"])["net_epa"]
        .transform(lambda x: x.shift(1).rolling(window=4, min_periods=2).mean())
    )
    weekly["prior_games_played"] = weekly.groupby(["team", "season"]).cumcount()
    return weekly


# ═══════════════════════════════════════════════════════════════════════════
# CURRENT SEASON / WEEK DETECTION
# ═══════════════════════════════════════════════════════════════════════════
def get_current_nfl_context(schedules_df: pd.DataFrame) -> tuple:
    """Return (season, week) of upcoming games right now."""
    today = pd.Timestamp.now().normalize()
    if "gameday" in schedules_df.columns:
        sd = schedules_df.copy()
        sd["gameday"] = pd.to_datetime(sd["gameday"], errors="coerce")
        upcoming = sd[sd["gameday"] >= today - pd.Timedelta(days=1)]
        if len(upcoming) > 0:
            next_game = upcoming.sort_values("gameday").iloc[0]
            return int(next_game["season"]), int(next_game["week"])
    # fallback — most recent completed week
    return int(schedules_df["season"].max()), int(schedules_df["week"].max())


def get_current_season_from_date() -> int:
    """Rough NFL season heuristic: Sep-Feb = current calendar year, Mar-Aug = coming season."""
    today = datetime.now()
    if today.month >= 3 and today.month <= 8:
        return today.year   # upcoming season
    if today.month >= 9:
        return today.year
    return today.year - 1  # Jan/Feb — still in previous season's playoffs


# ═══════════════════════════════════════════════════════════════════════════
# FACTOR SCORING
# ═══════════════════════════════════════════════════════════════════════════
def score_games(games, weekly_epa, epa_thresh, sp_min, sp_max, rest, late, min_prior,
                require_result: bool = True):
    g = games[games["spread_line"].notna()].copy()
    if require_result:
        g = g[
            g["result"].notna()
            & g["home_score"].notna()
            & g["away_score"].notna()
        ].copy()

    lookup = weekly_epa[["season", "week", "team", "rolling_net_epa", "prior_games_played"]]
    g = g.merge(
        lookup.rename(columns={"team": "home_team", "rolling_net_epa": "home_epa",
                                "prior_games_played": "home_prior_games"}),
        on=["season", "week", "home_team"], how="left")
    g = g.merge(
        lookup.rename(columns={"team": "away_team", "rolling_net_epa": "away_epa",
                                "prior_games_played": "away_prior_games"}),
        on=["season", "week", "away_team"], how="left")

    g = g[
        (g["home_prior_games"] >= min_prior)
        & (g["away_prior_games"] >= min_prior)
        & g["home_epa"].notna()
        & g["away_epa"].notna()
    ].copy()

    g["home_is_favorite"] = g["spread_line"] < 0
    g["sharp_side"] = np.where(g["home_epa"] > g["away_epa"], g["home_team"], g["away_team"])
    g["sharp_is_home"] = g["sharp_side"] == g["home_team"]
    g["sharp_is_favorite"] = g["sharp_is_home"] == g["home_is_favorite"]
    g["epa_gap_abs"] = (g["home_epa"] - g["away_epa"]).abs()
    g["abs_spread"] = g["spread_line"].abs()

    g["F1_epa"] = (g["epa_gap_abs"] >= epa_thresh).astype(int)
    g["F2_line_proxy"] = (
        (~g["sharp_is_favorite"]) & (g["epa_gap_abs"] >= epa_thresh * 0.75)
    ).astype(int)

    if "home_rest" in g.columns and "away_rest" in g.columns:
        g["sharp_rest"] = np.where(g["sharp_is_home"], g["home_rest"], g["away_rest"])
        g["opp_rest"] = np.where(g["sharp_is_home"], g["away_rest"], g["home_rest"])
        g["rest_advantage"] = g["sharp_rest"] - g["opp_rest"]
    else:
        g["rest_advantage"] = 0

    g["is_divisional"] = g["div_game"].fillna(0).astype(int) if "div_game" in g.columns else 0
    g["is_late_season"] = (g["week"] >= late).astype(int)

    g["F3_rest"] = (g["rest_advantage"] >= rest).astype(int)
    g["F3_div_dog"] = ((g["is_divisional"] == 1) & (~g["sharp_is_favorite"])).astype(int)
    g["F3_late"] = ((g["is_late_season"] == 1) & (g["epa_gap_abs"] >= epa_thresh)).astype(int)
    g["F3_situational"] = (
        (g["F3_rest"] == 1) | (g["F3_div_dog"] == 1) | (g["F3_late"] == 1)
    ).astype(int)

    g["factor_score"] = g["F1_epa"] + g["F2_line_proxy"] + g["F3_situational"]
    g["trigger_fired"] = (
        (g["factor_score"] == 3)
        & (g["abs_spread"] >= sp_min)
        & (g["abs_spread"] <= sp_max)
    ).astype(int)

    if require_result:
        g["home_margin"] = g["home_score"] - g["away_score"]
        g["sharp_margin"] = np.where(g["sharp_is_home"], g["home_margin"], -g["home_margin"])
        g["sharp_needed_margin"] = np.where(g["sharp_is_favorite"], g["abs_spread"], -g["abs_spread"])
        g["ats_diff"] = g["sharp_margin"] - g["sharp_needed_margin"]
        g["ats_result"] = g["ats_diff"].apply(
            lambda d: "COVER" if pd.notna(d) and d > 0
            else ("NO_COVER" if pd.notna(d) and d < 0
                  else ("PUSH" if pd.notna(d) else "NO_DATA"))
        )

    g["sharp_spread"] = np.where(g["sharp_is_favorite"], -g["abs_spread"], g["abs_spread"])
    g["opponent"] = np.where(g["sharp_is_home"], g["away_team"], g["home_team"])
    g["location"] = np.where(g["sharp_is_home"], "vs.", "@")

    return g


def render_odds_board(row: pd.Series, sharp_team_abbr: str, sharp_is_home: bool) -> str:
    """Return HTML for a side-by-side odds board across books, from sharp side's perspective."""
    cells = []
    side_suffix = "home" if sharp_is_home else "away"
    prices_and_spreads = []
    for book in PREFERRED_BOOKS:
        sp = row.get(f"{book}_{side_suffix}_spread")
        pr = row.get(f"{book}_{side_suffix}_price")
        if pd.notna(sp) and pd.notna(pr):
            prices_and_spreads.append((book, sp, pr))

    if not prices_and_spreads:
        return f"<p style='color:{CLOUD_GRAY}; font-style:italic;'>No live odds available for this game.</p>"

    # Best line for the sharp side is the HIGHEST spread number (most points if dog, least layout if fav)
    best_spread = max(p[1] for p in prices_and_spreads)

    for book, sp, pr in prices_and_spreads:
        is_best = (sp == best_spread)
        cls = "odds-cell best" if is_best else "odds-cell"
        book_disp = BOOK_DISPLAY.get(book, book.upper())
        sp_txt = f"{sp:+.1f}"
        pr_txt = f"{int(pr):+d}" if pr else ""
        cells.append(f"""
            <div class="{cls}">
                <div class="odds-book">{book_disp}{' ★' if is_best else ''}</div>
                <div class="odds-line">{sp_txt}</div>
                <div class="odds-price">{pr_txt}</div>
            </div>
        """)

    return f'<div class="odds-board">{"".join(cells)}</div>'


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🌊 SYSTEM CONFIG")
    st.markdown("---")

    st.markdown("### Factor Thresholds")
    epa_threshold = st.slider("F1: Net EPA Gap min", 0.05, 0.25, 0.12, 0.01)
    spread_min = st.slider("Spread band — min", 1.0, 7.0, 3.0, 0.5)
    spread_max = st.slider("Spread band — max", 6.0, 17.0, 10.0, 0.5)
    rest_days = st.slider("F3a: Rest advantage (days)", 1, 7, 3, 1)
    late_week = st.slider("F3c: Late season starts week", 10, 17, 14, 1)
    min_games_seen = st.slider("Min prior games / team", 2, 8, 2, 1)

    st.markdown("---")
    st.markdown("### 💰 Default Bet Config")
    default_amount = st.number_input("Default bet amount ($)", value=100.0, step=10.0, min_value=1.0)
    default_odds = st.number_input("Default odds (American)", value=-110, step=5)
    default_book = st.text_input("Default sportsbook", value="DraftKings")

    st.markdown("---")
    st.markdown("### 📡 API Status")
    if ODDS_API_KEY:
        remaining = st.session_state.get("odds_api_remaining", "?")
        used = st.session_state.get("odds_api_used", "?")
        st.markdown(f"""
        <div style="color:{NEON_MINT}; font-size:0.8rem;">
            ✅ Odds API connected<br>
            Used: {used} / Remaining: {remaining}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="color:{SUNSET_CORAL}; font-size:0.8rem;">
            ⚠️ No ODDS_API_KEY set<br>
            Live odds disabled
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🔄 Refresh live odds", width="stretch"):
        st.cache_data.clear()
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL TABS
# ═══════════════════════════════════════════════════════════════════════════
mode_picks, mode_track, mode_bt = st.tabs([
    "🎯 THIS WEEK'S PICKS",
    "💰 BET TRACKING",
    "🔬 HISTORICAL BACKTEST"
])

# ═══════════════════════════════════════════════════════════════════════════
# MODE 1 — LIVE WEEKLY PICKS with LIVE ODDS
# ═══════════════════════════════════════════════════════════════════════════
with mode_picks:
    # Load schedule for week/season detection
    with st.spinner("Loading schedule..."):
        try:
            schedules_all = load_schedules()
            schedules_all["gameday"] = pd.to_datetime(schedules_all["gameday"], errors="coerce")
        except Exception as e:
            st.error(f"❌ Schedule load: {e}")
            st.stop()

    # Load live odds
    with st.spinner("Fetching live odds from The Odds API..."):
        live_odds = fetch_live_odds()

    # Determine current context
    current_season, current_week = get_current_nfl_context(schedules_all)

    # Header banner showing status
    if len(live_odds) > 0 and ODDS_API_KEY:
        st.markdown(f"""
        <div class="live-banner">
            <strong>🟢 LIVE:</strong> {len(live_odds)} upcoming NFL games with real-time odds
            from {len(PREFERRED_BOOKS)} sportsbooks.
            Season {current_season}, Week {current_week}. Best line shown with ★ and mint highlight.
        </div>
        """, unsafe_allow_html=True)
    elif not ODDS_API_KEY:
        st.markdown(f"""
        <div class="warn-banner">
            <strong>⚠️ Live odds disabled.</strong> Set <code>ODDS_API_KEY</code> environment variable
            in Railway to enable. Falling back to historical closing lines.
        </div>
        """, unsafe_allow_html=True)
    else:
        err = st.session_state.get("odds_error", "unknown")
        st.markdown(f"""
        <div class="warn-banner">
            <strong>⚠️ Live odds unavailable:</strong> {err}. Falling back to historical closing lines.
        </div>
        """, unsafe_allow_html=True)

    # Week/season selector (defaults to current)
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_season = st.selectbox(
            "Season",
            options=sorted(schedules_all["season"].dropna().unique().astype(int).tolist(), reverse=True),
            index=0
        )
    with col2:
        weeks_for_sel = sorted(
            schedules_all[schedules_all["season"] == selected_season]["week"].dropna().unique().astype(int).tolist()
        )
        if selected_season == current_season and current_week in weeks_for_sel:
            default_idx = weeks_for_sel.index(current_week)
        else:
            default_idx = 0
        selected_week = st.selectbox(
            f"Week (Season {selected_season})",
            options=weeks_for_sel,
            index=default_idx
        )

    is_current_week = (selected_season == current_season and selected_week == current_week)

    # ── Build the games dataframe: prefer live odds when it's the current week
    if is_current_week and len(live_odds) > 0:
        # Build a synthetic games df from live odds, use consensus spread
        live = live_odds.copy()
        live["spread_line"] = live.apply(consensus_home_spread, axis=1)
        live["season"] = selected_season
        live["week"] = selected_week
        live["gameday"] = live["commence_time"]
        # Add empty rest/div columns so score_games doesn't fail
        # Try to look up rest/div from the schedule
        sched_this_wk = schedules_all[
            (schedules_all["season"] == selected_season)
            & (schedules_all["week"] == selected_week)
        ][["home_team", "away_team", "home_rest", "away_rest", "div_game"]]
        live = live.merge(sched_this_wk, on=["home_team", "away_team"], how="left")
        if "home_rest" not in live.columns:
            live["home_rest"] = 7
            live["away_rest"] = 7
        else:
            live["home_rest"] = live["home_rest"].fillna(7)
            live["away_rest"] = live["away_rest"].fillna(7)
        live["div_game"] = live["div_game"].fillna(0)
        live["result"] = np.nan
        live["home_score"] = np.nan
        live["away_score"] = np.nan
        week_games = live
        odds_by_gameid = live_odds.set_index(
            live_odds["home_team"] + "_" + live_odds["away_team"]
        ).to_dict("index")
    else:
        # Fall back to historical schedule spread
        week_games = schedules_all[
            (schedules_all["season"] == selected_season)
            & (schedules_all["week"] == selected_week)
        ].copy()
        odds_by_gameid = {}

    if len(week_games) == 0:
        st.info(f"No games available for Season {selected_season}, Week {selected_week}.")
        st.stop()

    # Compute EPA
    seasons_needed = [selected_season]
    if selected_week <= 4 and selected_season > 2020:
        seasons_needed.append(selected_season - 1)
    seasons_needed = tuple(sorted(set(seasons_needed)))

    with st.spinner(f"Computing lagged EPA through Week {selected_week - 1}..."):
        try:
            weekly_epa = compute_lagged_epa(seasons_needed)
        except Exception as e:
            # Fall back to prior season only
            if selected_season > 2020:
                try:
                    weekly_epa = compute_lagged_epa((selected_season - 1,))
                    st.warning(f"Using {selected_season - 1} EPA data as fallback.")
                except Exception as e2:
                    st.error(f"❌ EPA load failed: {e2}")
                    st.stop()
            else:
                st.error(f"❌ EPA load: {e}")
                st.stop()

    # Score
    scored = score_games(
        week_games, weekly_epa,
        epa_threshold, spread_min, spread_max, rest_days, late_week, min_games_seen,
        require_result=False
    )

    if len(scored) == 0:
        st.warning("No games scored — try lowering 'Min prior games' in sidebar.")
        st.stop()

    triggers = scored[scored["trigger_fired"] == 1]
    n_triggers = len(triggers)

    if n_triggers > 0:
        bg = f"linear-gradient(135deg, {POOL_DEEP} 0%, {POOL_CYAN} 100%)"
        msg = f"⭐ {n_triggers} TRIGGER{'S' if n_triggers != 1 else ''} — LIGHT 'EM UP"
    else:
        bg = f"linear-gradient(135deg, {AMBER_DEEP} 0%, {AMBER_GOLD} 100%)"
        msg = "⚠️ NO FULL TRIGGERS — CHECK WATCH LIST"

    st.markdown(f"""
    <div class="callout" style="background: {bg};">
        <h2>{msg}</h2>
        <p style="margin: 0; color: {NIGHT_BLACK}; font-weight: 600;">
            Season {selected_season} · Week {selected_week} · {len(scored)} games scored
        </p>
    </div>
    """, unsafe_allow_html=True)

    def render_pick_card(row, card_class="pick-card", trigger_full=True):
        game_date = row.get('gameday', pd.NaT)
        game_date_str = game_date.strftime("%a %m/%d %I:%M %p") if pd.notna(game_date) else "TBD"
        spread_txt = f"{row['sharp_spread']:+.1f}"

        st.markdown(f"""
        <div class="{card_class}">
            <h3>{row['sharp_side']} {spread_txt} {row['location']} {row['opponent']}</h3>
            <p><strong>{game_date_str}</strong> · EPA Edge: <strong style="color: {POOL_CYAN};">+{row['epa_gap_abs']:.3f}</strong>
            · Rest Adv: <strong>{int(row['rest_advantage'])} days</strong>
            · Divisional: <strong>{'Yes' if row['is_divisional'] else 'No'}</strong></p>
        </div>
        """, unsafe_allow_html=True)

        # Live odds board if available
        game_key = f"{row['home_team']}_{row['away_team']}"
        if game_key in odds_by_gameid:
            odds_row = pd.Series(odds_by_gameid[game_key])
            st.markdown(render_odds_board(odds_row, row['sharp_side'], row['sharp_is_home']),
                        unsafe_allow_html=True)

        # Factor chips row
        f1_c = "on" if row['F1_epa'] else "off"
        f2_c = "on" if row['F2_line_proxy'] else "off"
        f3_c = "on" if row['F3_situational'] else "off"
        f1_s = "✓" if row['F1_epa'] else "✗"
        f2_s = "✓" if row['F2_line_proxy'] else "✗"
        f3_s = "✓" if row['F3_situational'] else "✗"
        st.markdown(f"""
        <div style="display:flex; gap:0.6rem; margin: 0.5rem 0 1rem 0;">
            <span class="factor-chip {f1_c}">F1 EPA {f1_s}</span>
            <span class="factor-chip {f2_c}">F2 LINE {f2_s}</span>
            <span class="factor-chip {f3_c}">F3 SITUATION {f3_s}</span>
        </div>
        """, unsafe_allow_html=True)

    def render_bet_form(row, source, key_prefix):
        with st.expander(f"💰 Log bet on {row['sharp_side']}"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                bet_amount = st.number_input(
                    "Amount ($)", value=default_amount, step=10.0, min_value=1.0,
                    key=f"amt_{key_prefix}_{row.name}"
                )
            with c2:
                bet_odds = st.number_input(
                    "Odds", value=default_odds, step=5,
                    key=f"odds_{key_prefix}_{row.name}"
                )
            with c3:
                bet_book = st.text_input(
                    "Book", value=default_book,
                    key=f"book_{key_prefix}_{row.name}"
                )
            with c4:
                st.write("")
                st.write("")
                if st.button(f"✅ LOG BET", key=f"log_{key_prefix}_{row.name}", width="stretch"):
                    game_date = row.get('gameday', pd.NaT)
                    game_date_str = game_date.strftime("%a %m/%d") if pd.notna(game_date) else "TBD"
                    add_bet({
                        "season": selected_season,
                        "week": selected_week,
                        "game_date": game_date_str,
                        "sharp_side": row['sharp_side'],
                        "opponent": row['opponent'],
                        "location": row['location'],
                        "spread": float(row['sharp_spread']),
                        "amount": float(bet_amount),
                        "odds": int(bet_odds),
                        "book": bet_book,
                        "bet_source": source,
                        "factor_score": int(row['factor_score']),
                        "epa_gap": float(row['epa_gap_abs']),
                        "result": "PENDING",
                        "profit": np.nan,
                    })
                    st.success(f"Logged: {row['sharp_side']} {row['sharp_spread']:+.1f} @ {bet_book}")
                    st.rerun()

    if n_triggers > 0:
        st.markdown("### 🎯 Triggered Picks — All 3 Factors Aligned")
        for _, row in triggers.iterrows():
            render_pick_card(row, "pick-card")
            render_bet_form(row, "trigger", "trig")

    two_of_three = scored[(scored["factor_score"] == 2) & (scored["trigger_fired"] == 0)]
    if len(two_of_three) > 0:
        st.markdown(f"### 👀 Watch List — 2/3 Factors ({len(two_of_three)} games)")
        st.caption("Historical hit ~71% — worth logging if you like the spot")
        for _, row in two_of_three.iterrows():
            render_pick_card(row, "pick-card watch")
            render_bet_form(row, "watch_list", "watch")

    with st.expander(f"📁 Full slate ({len(scored)} games)"):
        cols = ["gameday", "sharp_side", "location", "opponent",
                "sharp_spread", "epa_gap_abs", "rest_advantage",
                "is_divisional", "factor_score", "trigger_fired"]
        avail = [c for c in cols if c in scored.columns]
        show = scored[avail].sort_values("factor_score", ascending=False).copy()
        if "epa_gap_abs" in show.columns:
            show["epa_gap_abs"] = show["epa_gap_abs"].round(3)
        if "sharp_spread" in show.columns:
            show["sharp_spread"] = show["sharp_spread"].round(1)
        st.dataframe(show, width="stretch", hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# MODE 2 — BET TRACKING
# ═══════════════════════════════════════════════════════════════════════════
with mode_track:
    bets_df = load_bets()

    if len(bets_df) == 0:
        st.markdown(f"""
        <div class="info-banner">
            <strong>No bets logged yet.</strong> Head to <strong>THIS WEEK'S PICKS</strong> and click
            "💰 Log bet" on any triggered pick or watch-list game.
        </div>
        """, unsafe_allow_html=True)
    else:
        settled = bets_df[bets_df["result"].isin(["WIN", "LOSS", "PUSH"])].copy()
        pending = bets_df[bets_df["result"] == "PENDING"].copy()

        wins = (settled["result"] == "WIN").sum()
        losses = (settled["result"] == "LOSS").sum()
        pushes = (settled["result"] == "PUSH").sum()
        decided = wins + losses
        win_rate = wins / decided if decided > 0 else 0

        settled["profit_num"] = pd.to_numeric(settled["profit"], errors="coerce")
        total_profit = settled["profit_num"].sum()
        total_wagered = settled["amount"].sum()
        roi = (total_profit / total_wagered) if total_wagered > 0 else 0
        pending_wagered = pending["amount"].sum() if len(pending) else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("Record", f"{wins}-{losses}-{pushes}")
        with c2: st.metric("Win Rate", f"{win_rate:.1%}" if decided > 0 else "—")
        with c3: st.metric("Total P/L", f"${total_profit:,.0f}")
        with c4: st.metric("ROI", f"{roi:.1%}")
        with c5: st.metric("Pending", f"${pending_wagered:,.0f}",
                            delta=f"{len(pending)} bets" if len(pending) else None)

        st.markdown("---")

        tab_p, tab_all, tab_brk, tab_bnk = st.tabs([
            "⏳ Pending Bets", "📋 All Bets", "📊 Breakdowns", "📈 Bankroll"
        ])

        with tab_p:
            if len(pending) == 0:
                st.info("No pending bets.")
            else:
                st.markdown(f"### {len(pending)} Bets Awaiting Result")
                for _, bet in pending.iterrows():
                    bet_id = int(bet["bet_id"])
                    st.markdown(f"""
                    <div class="pick-card">
                        <h3>{bet['sharp_side']} {bet['spread']:+.1f} {bet['location']} {bet['opponent']}</h3>
                        <p>{bet.get('game_date', '')} · <strong>${bet['amount']:.0f}</strong> @ {int(bet['odds'])}
                        · {bet['book']} · Source: <em>{bet['bet_source']}</em></p>
                    </div>
                    """, unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                    with c1:
                        if st.button("✅ WIN", key=f"win_{bet_id}", width="stretch"):
                            df = load_bets()
                            df.loc[df["bet_id"] == bet_id, "result"] = "WIN"
                            df.loc[df["bet_id"] == bet_id, "profit"] = calc_bet_profit(
                                float(bet["amount"]), int(bet["odds"]), "WIN")
                            save_bets(df)
                            st.rerun()
                    with c2:
                        if st.button("❌ LOSS", key=f"loss_{bet_id}", width="stretch"):
                            df = load_bets()
                            df.loc[df["bet_id"] == bet_id, "result"] = "LOSS"
                            df.loc[df["bet_id"] == bet_id, "profit"] = calc_bet_profit(
                                float(bet["amount"]), int(bet["odds"]), "LOSS")
                            save_bets(df)
                            st.rerun()
                    with c3:
                        if st.button("⚖️ PUSH", key=f"push_{bet_id}", width="stretch"):
                            df = load_bets()
                            df.loc[df["bet_id"] == bet_id, "result"] = "PUSH"
                            df.loc[df["bet_id"] == bet_id, "profit"] = 0
                            save_bets(df)
                            st.rerun()
                    with c4:
                        if st.button("🗑️ Delete", key=f"del_{bet_id}", width="stretch"):
                            df = load_bets()
                            df = df[df["bet_id"] != bet_id]
                            save_bets(df)
                            st.rerun()

        with tab_all:
            st.markdown(f"### All {len(bets_df)} Bets")
            display_cols = ["logged_at", "season", "week", "game_date",
                            "sharp_side", "opponent", "spread",
                            "amount", "odds", "book", "bet_source",
                            "factor_score", "result", "profit"]
            show = bets_df[[c for c in display_cols if c in bets_df.columns]].copy()
            show = show.sort_values("logged_at", ascending=False)
            st.dataframe(show, width="stretch", hide_index=True, height=400)

            c1, c2 = st.columns(2)
            with c1:
                csv = bets_df.to_csv(index=False)
                st.download_button("📥 Export bets to CSV", csv,
                                   f"sirron_bets_{datetime.now():%Y%m%d}.csv",
                                   "text/csv", width="stretch")
            with c2:
                if st.button("⚠️ Clear all bets", width="stretch"):
                    if BETS_FILE.exists():
                        BETS_FILE.unlink()
                    st.rerun()

        with tab_brk:
            if len(settled) == 0:
                st.info("Log and settle some bets to see breakdowns.")
            else:
                st.markdown("### Performance Breakdowns")

                st.markdown("#### 📌 By Bet Source")
                by_src = settled.groupby("bet_source").agg(
                    Bets=("bet_id", "count"),
                    Wins=("result", lambda x: (x == "WIN").sum()),
                    Losses=("result", lambda x: (x == "LOSS").sum()),
                    Pushes=("result", lambda x: (x == "PUSH").sum()),
                    Wagered=("amount", "sum"),
                    Profit=("profit_num", "sum"),
                ).reset_index()
                by_src["Win Rate"] = by_src.apply(
                    lambda r: f"{r['Wins']/(r['Wins']+r['Losses']):.1%}"
                    if (r['Wins']+r['Losses']) > 0 else "—", axis=1)
                by_src["ROI"] = by_src.apply(
                    lambda r: f"{r['Profit']/r['Wagered']:.1%}" if r['Wagered'] > 0 else "—", axis=1)
                by_src["Profit"] = by_src["Profit"].apply(lambda x: f"${x:,.0f}")
                by_src["Wagered"] = by_src["Wagered"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(by_src, width="stretch", hide_index=True)

                st.markdown("#### 🏛️ By Sportsbook")
                by_book = settled.groupby("book").agg(
                    Bets=("bet_id", "count"),
                    Wins=("result", lambda x: (x == "WIN").sum()),
                    Losses=("result", lambda x: (x == "LOSS").sum()),
                    Wagered=("amount", "sum"),
                    Profit=("profit_num", "sum"),
                ).reset_index()
                by_book["Win Rate"] = by_book.apply(
                    lambda r: f"{r['Wins']/(r['Wins']+r['Losses']):.1%}"
                    if (r['Wins']+r['Losses']) > 0 else "—", axis=1)
                by_book["ROI"] = by_book.apply(
                    lambda r: f"{r['Profit']/r['Wagered']:.1%}" if r['Wagered'] > 0 else "—", axis=1)
                by_book["Profit"] = by_book["Profit"].apply(lambda x: f"${x:,.0f}")
                by_book["Wagered"] = by_book["Wagered"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(by_book, width="stretch", hide_index=True)

                st.markdown("#### 📅 By Week")
                by_wk = settled.groupby(["season", "week"]).agg(
                    Bets=("bet_id", "count"),
                    Wins=("result", lambda x: (x == "WIN").sum()),
                    Losses=("result", lambda x: (x == "LOSS").sum()),
                    Profit=("profit_num", "sum"),
                ).reset_index()
                by_wk["Profit"] = by_wk["Profit"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(by_wk.sort_values(["season", "week"], ascending=[False, False]),
                             width="stretch", hide_index=True)

        with tab_bnk:
            if len(settled) == 0:
                st.info("Settle some bets to see the bankroll curve.")
            else:
                st.markdown("### Bankroll Growth")
                settled_sorted = settled.sort_values("logged_at").copy()
                settled_sorted["cum_profit"] = settled_sorted["profit_num"].cumsum()
                settled_sorted["bet_number"] = range(1, len(settled_sorted) + 1)
                chart_data = pd.DataFrame({
                    "Bet #": settled_sorted["bet_number"],
                    "Cumulative P/L": settled_sorted["cum_profit"],
                })
                st.line_chart(chart_data.set_index("Bet #"))

                if decided >= 20 and win_rate > 0.52:
                    avg_odds = settled["odds"].mean()
                    b = (abs(avg_odds) / 100) if avg_odds > 0 else (100 / abs(avg_odds))
                    p = win_rate
                    q = 1 - p
                    kelly = (b * p - q) / b
                    kelly_half = kelly / 2
                    st.markdown("### 🎲 Kelly Criterion Bet Sizing")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("Full Kelly", f"{kelly*100:.1f}%")
                    with c2: st.metric("Half Kelly (recommended)", f"{kelly_half*100:.1f}%")
                    with c3: st.metric("Sample size", f"{decided} settled bets")
                    st.caption(
                        f"Based on {win_rate:.1%} win rate at avg odds {avg_odds:.0f}. "
                        f"Half-Kelly reduces variance."
                    )
                else:
                    st.info(f"Kelly sizing appears after 20+ settled bets. Currently: {decided} settled.")


# ═══════════════════════════════════════════════════════════════════════════
# MODE 3 — HISTORICAL BACKTEST
# ═══════════════════════════════════════════════════════════════════════════
with mode_bt:
    st.markdown(f"""
    <div class="info-banner">
        <strong>⚠️ Backtest integrity:</strong> EPA is LAGGED (uses only prior games).
        Baseline should sit near 50%.
    </div>
    """, unsafe_allow_html=True)

    bt_seasons = st.multiselect(
        "Seasons to backtest:",
        options=[2020, 2021, 2022, 2023, 2024, 2025],
        default=[2022, 2023, 2024],
        key="backtest_seasons"
    )

    if not bt_seasons:
        st.warning("Select at least one season.")
        st.stop()

    with st.spinner(f"Loading data for {bt_seasons}..."):
        try:
            for s in bt_seasons:
                load_play_by_play(s)
            all_sched = load_schedules()
            bt_sched = all_sched[all_sched["season"].isin(bt_seasons)].copy()
        except Exception as e:
            st.error(f"❌ Data load: {e}")
            st.stop()

    with st.spinner("Computing LAGGED EPA..."):
        bt_weekly = compute_lagged_epa(tuple(sorted(bt_seasons)))

    with st.spinner("Scoring games..."):
        bt_results = score_games(
            bt_sched, bt_weekly,
            epa_threshold, spread_min, spread_max, rest_days, late_week, min_games_seen,
            require_result=True
        )
    bt_results = bt_results[bt_results["ats_result"] != "NO_DATA"].copy()
    bt_triggered = bt_results[bt_results["trigger_fired"] == 1].copy()

    tc = (bt_triggered["ats_result"] == "COVER").sum()
    tnc = (bt_triggered["ats_result"] == "NO_COVER").sum()
    tp = (bt_triggered["ats_result"] == "PUSH").sum()
    tdec = tc + tnc
    trate = tc / tdec if tdec > 0 else 0

    bc = (bt_results["ats_result"] == "COVER").sum()
    bnc = (bt_results["ats_result"] == "NO_COVER").sum()
    bp = (bt_results["ats_result"] == "PUSH").sum()
    bdec = bc + bnc
    brate = bc / bdec if bdec > 0 else 0

    hit_pct = f"{trate:.1%}" if tdec > 0 else "—"

    if trate >= 0.80:
        bg = f"linear-gradient(135deg, {POOL_DEEP} 0%, {POOL_CYAN} 100%)"
    elif trate >= 0.65:
        bg = f"linear-gradient(135deg, {POOL_DEEP} 0%, {TWILIGHT_MID} 100%)"
    elif trate >= 0.55:
        bg = f"linear-gradient(135deg, {AMBER_DEEP} 0%, {AMBER_GOLD} 100%)"
    else:
        bg = f"linear-gradient(135deg, {CORAL_DEEP} 0%, {SUNSET_CORAL} 100%)"

    st.markdown(f"""
    <div class="callout" style="background: {bg};">
        <h2>⭐ 3/3 TRIGGER RESULTS</h2>
        <p style="font-size: 2.8rem; margin: 0; font-weight: 800; color: {NIGHT_BLACK}; font-family: 'Bebas Neue';">
            {tc}–{tnc}–{tp}
            <span style="font-size: 2rem; margin-left: 1.5rem;">{hit_pct} COVER</span>
        </p>
        <p style="margin: 0.5rem 0 0 0; color: {NIGHT_BLACK}; font-weight: 600;">
            {tdec + tp} qualifying · Baseline: {brate:.1%} · Edge: <strong>{(trate - brate)*100:+.1f} pts</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_sum, tab_trg, tab_fac = st.tabs(["📊 Summary", "🎯 Triggered Games", "🔬 Factor Breakdown"])

    with tab_sum:
        st.markdown("### Hit Rate by Factor Score")
        cols = st.columns(4)
        for i, col in enumerate(cols):
            subset = bt_results[bt_results["factor_score"] == i]
            c = (subset["ats_result"] == "COVER").sum()
            nc = (subset["ats_result"] == "NO_COVER").sum()
            dec = c + nc
            rate = c / dec if dec > 0 else 0
            with col:
                st.metric(
                    label=f"Score {i}/3",
                    value=f"{rate:.1%}" if dec > 0 else "—",
                    delta=f"{c}-{nc} ({len(subset)})",
                    delta_color="off",
                )

        st.markdown("---")
        st.markdown("### Per-Season Trigger Performance")
        rows = []
        for s in sorted(bt_seasons):
            st_trig = bt_triggered[bt_triggered["season"] == s]
            c = (st_trig["ats_result"] == "COVER").sum()
            nc = (st_trig["ats_result"] == "NO_COVER").sum()
            p = (st_trig["ats_result"] == "PUSH").sum()
            dec = c + nc
            rate = c / dec if dec > 0 else np.nan
            rows.append({
                "Season": s, "Triggered": len(st_trig),
                "Covers": c, "No Covers": nc, "Pushes": p,
                "Hit Rate": f"{rate:.1%}" if not pd.isna(rate) else "—"
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with tab_trg:
        st.markdown(f"### {len(bt_triggered)} Triggered Games")
        if len(bt_triggered) == 0:
            st.info("No games triggered.")
        else:
            cols = ["season", "week", "sharp_side", "opponent", "location",
                    "sharp_spread", "home_score", "away_score",
                    "epa_gap_abs", "sharp_margin", "ats_result"]
            disp = bt_triggered[[c for c in cols if c in bt_triggered.columns]].copy()
            disp = disp.sort_values(["season", "week"])
            if "epa_gap_abs" in disp.columns:
                disp["epa_gap_abs"] = disp["epa_gap_abs"].round(3)
            if "sharp_spread" in disp.columns:
                disp["sharp_spread"] = disp["sharp_spread"].round(1)
            st.dataframe(disp, width="stretch", hide_index=True, height=500)

    with tab_fac:
        st.markdown("### Standalone Factor Hit Rates")
        rows = []
        for col, name in [
            ("F1_epa", "F1: EPA gap ≥ threshold"),
            ("F2_line_proxy", "F2: Line movement proxy"),
            ("F3_situational", "F3: Any situational edge"),
            ("F3_rest", "  • F3a: Rest advantage"),
            ("F3_div_dog", "  • F3b: Divisional underdog"),
            ("F3_late", "  • F3c: Late season + EPA"),
        ]:
            subset = bt_results[bt_results[col] == 1]
            c = (subset["ats_result"] == "COVER").sum()
            nc = (subset["ats_result"] == "NO_COVER").sum()
            dec = c + nc
            rate = c / dec if dec > 0 else np.nan
            rows.append({
                "Factor": name, "Games": len(subset),
                "Covers": c, "No Covers": nc,
                "Hit Rate": f"{rate:.1%}" if not pd.isna(rate) else "—"
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


st.markdown("---")
st.markdown(f"""
<p style="text-align: center; color: {CLOUD_GRAY}; font-size: 0.8rem;">
    🌊 Sir Ron's Sharp Signal · Circa Stadium Swim Edition · Live: The Odds API · Historical: nflverse · {datetime.now():%Y-%m-%d %H:%M}
</p>
""", unsafe_allow_html=True)

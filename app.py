"""
MARGIN OF VICTORY — v6
========================
Companion app to Ron Zellers' book on NFL ATS analytics.
Book-cover header + ESPN broadcast body layout.
Deep forest green / cream / mustard gold palette.

Features preserved from v5:
- LIVE ODDS via The Odds API (env var: ODDS_API_KEY)
- Auto-detects current NFL week
- Top 4 books side-by-side line shopping
- Bet tracking with Railway persistent volume
- Historical backtest for validation
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
    page_title="Margin of Victory",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# BOOK COVER + BROADCAST COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════════════
FOREST_DEEP   = "#0F2818"   # Deepest field green — page background
FOREST_MID    = "#1B3A26"   # Card backgrounds
FOREST_LIGHT  = "#2C5138"   # Borders, dividers
CREAM         = "#F5F1E8"   # Primary text (book paper)
CREAM_MUTED   = "#D4CDB8"   # Secondary text
SAGE          = "#8FB89A"   # Tertiary text, muted labels
MUSTARD       = "#D4A537"   # Accent gold (triggers, best lines, headings)
MUSTARD_DEEP  = "#B58A28"   # Deeper mustard
BRIGHT_GREEN  = "#5CB85C"   # LIVE indicator, F1/F2/F3 confirmations, EPA edge
BLOOD_RED     = "#8B2635"   # Losses, warnings, no-cover
NIGHT_BLACK   = "#050D08"   # Deepest shadow

# ═══════════════════════════════════════════════════════════════════════════
# STYLING
# ═══════════════════════════════════════════════════════════════════════════
import base64

def _load_banner_b64() -> str:
    """Load book banner image and return base64-encoded string for embedding."""
    candidates = [
        Path(__file__).parent / "assets" / "book_banner.jpg",
        Path(__file__).parent / "book_banner.jpg",
        Path("/app/assets/book_banner.jpg"),
    ]
    for p in candidates:
        if p.exists():
            try:
                return base64.b64encode(p.read_bytes()).decode("ascii")
            except Exception:
                pass
    return ""

_BANNER_B64 = _load_banner_b64()

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Barlow+Condensed:wght@400;600;700;800&family=Cormorant+Garamond:ital,wght@0,600;1,400&display=swap');

    .stApp {{
        background: {FOREST_DEEP};
        color: {CREAM};
    }}
    p, div, span, label {{ color: {CREAM}; font-family: 'Barlow Condensed', Arial, sans-serif; }}
    h1, h2, h3, h4, h5, h6 {{ color: {CREAM}; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }}

    /* ── BOOK-COVER HEADER (with banner image background) ────────────── */
    .book-header {{
        background-image: url("data:image/jpeg;base64,{_BANNER_B64}");
        background-size: cover;
        background-position: center;
        border: 2px solid {MUSTARD};
        border-radius: 8px;
        padding: 48px 40px 40px 40px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
        min-height: 220px;
    }}
    .book-header::before {{
        content: '';
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg,
            rgba(15,40,24,0.85) 0%,
            rgba(15,40,24,0.55) 45%,
            rgba(15,40,24,0.25) 100%);
        pointer-events: none;
    }}
    .book-header .tagline {{
        color: {MUSTARD};
        font-size: 12px;
        letter-spacing: 4px;
        margin-bottom: 10px;
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        position: relative;
        z-index: 2;
        text-shadow: 0 2px 6px rgba(0,0,0,0.9);
    }}
    .book-header h1 {{
        color: {CREAM};
        margin: 0;
        font-family: 'Playfair Display', Georgia, serif !important;
        font-size: 56px;
        font-weight: 700;
        letter-spacing: 2px;
        line-height: 1;
        text-transform: none;
        position: relative;
        z-index: 2;
        text-shadow: 0 3px 12px rgba(0,0,0,0.9), 0 0 30px rgba(212,165,55,0.3);
    }}
    .book-header .byline {{
        color: {MUSTARD};
        font-size: 16px;
        font-style: italic;
        margin-top: 14px;
        letter-spacing: 0.5px;
        font-family: 'Cormorant Garamond', Georgia, serif;
        position: relative;
        z-index: 2;
        text-shadow: 0 2px 6px rgba(0,0,0,0.9);
    }}
    .book-header .live-pill {{
        position: absolute;
        top: 20px;
        right: 24px;
        background: {BRIGHT_GREEN};
        color: {FOREST_DEEP};
        padding: 5px 14px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 2px;
        font-family: 'Barlow Condensed', sans-serif;
        border-radius: 2px;
        z-index: 3;
        box-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }}
    .book-header .live-pill.warn {{ background: {MUSTARD}; }}
    .book-header .live-pill.off {{ background: {BLOOD_RED}; color: {CREAM}; }}

    /* ── METRIC CARDS ────────────────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: {FOREST_MID};
        padding: 1rem 1.2rem;
        border-radius: 4px;
        border-left: 4px solid {MUSTARD};
        border-top: 1px solid {FOREST_LIGHT};
        border-right: 1px solid {FOREST_LIGHT};
        border-bottom: 1px solid {FOREST_LIGHT};
    }}
    [data-testid="stMetricValue"] {{
        color: {MUSTARD};
        font-weight: 800;
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 2.2rem;
        letter-spacing: 1px;
    }}
    [data-testid="stMetricLabel"] {{
        color: {SAGE};
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 2px;
        font-family: 'Barlow Condensed', sans-serif;
    }}
    [data-testid="stMetricDelta"] {{ color: {CREAM_MUTED}; }}

    /* ── SIDEBAR — the almanac's index ──────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background: {NIGHT_BLACK};
        border-right: 1px solid {FOREST_LIGHT};
    }}
    section[data-testid="stSidebar"] * {{ color: {CREAM} !important; font-family: 'Barlow Condensed', sans-serif; }}
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {MUSTARD} !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 700;
    }}
    .stSlider [data-baseweb="slider"] > div > div > div {{ background: {MUSTARD}; }}

    /* ── BUTTONS ─────────────────────────────────────────────────────── */
    .stButton > button {{
        background: {MUSTARD};
        color: {FOREST_DEEP};
        border: 2px solid {MUSTARD};
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        border-radius: 2px;
        transition: all 0.15s;
    }}
    .stButton > button:hover {{
        background: {MUSTARD_DEEP};
        border-color: {MUSTARD_DEEP};
        transform: translateY(-1px);
    }}

    /* ── TABS — the angled broadcast tab ────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: transparent;
        padding: 0;
        border-bottom: 2px solid {FOREST_LIGHT};
        border-radius: 0;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: 0;
        padding: 12px 22px;
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        color: {SAGE};
        letter-spacing: 2px;
        text-transform: uppercase;
        border: none;
        font-size: 13px;
    }}
    .stTabs [aria-selected="true"] {{
        background: {MUSTARD} !important;
        color: {FOREST_DEEP} !important;
        font-weight: 800 !important;
        clip-path: polygon(0 0, 100% 0, 94% 100%, 0 100%);
        padding-right: 32px !important;
    }}

    /* ── CALLOUTS — the scoreboard bar ──────────────────────────────── */
    .callout {{
        color: {CREAM};
        padding: 14px 22px;
        border-left: 6px solid {MUSTARD};
        margin: 1rem 0;
        background: linear-gradient(90deg, {FOREST_MID} 0%, {FOREST_DEEP} 100%);
        font-family: 'Barlow Condensed', sans-serif;
    }}
    .callout h2 {{
        color: {CREAM};
        margin: 0 0 4px 0;
        font-family: 'Barlow Condensed', sans-serif !important;
        letter-spacing: 2px;
        font-size: 1.8rem;
        font-weight: 800;
    }}
    .callout p {{
        margin: 0;
        color: {MUSTARD};
        font-weight: 700;
        letter-spacing: 2px;
        font-size: 12px;
    }}

    /* ── INFO BANNERS ────────────────────────────────────────────────── */
    .info-banner {{
        background: {FOREST_MID};
        border-left: 4px solid {MUSTARD};
        padding: 12px 18px;
        border-radius: 4px;
        margin: 0.75rem 0 1.25rem 0;
        color: {CREAM};
        font-size: 13px;
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-style: italic;
    }}
    .live-banner {{
        background: {FOREST_MID};
        border-left: 4px solid {BRIGHT_GREEN};
        padding: 12px 18px;
        border-radius: 4px;
        margin: 0.75rem 0 1.25rem 0;
        color: {BRIGHT_GREEN};
        font-size: 13px;
        font-family: 'Barlow Condensed', sans-serif;
        letter-spacing: 1px;
    }}
    .warn-banner {{
        background: {FOREST_MID};
        border-left: 4px solid {BLOOD_RED};
        padding: 12px 18px;
        border-radius: 4px;
        margin: 0.75rem 0 1.25rem 0;
        color: {CREAM};
        font-size: 13px;
        font-family: 'Barlow Condensed', sans-serif;
    }}

    /* ── PICK CARDS — the game entry ─────────────────────────────────── */
    .pick-card {{
        background: {FOREST_MID};
        border: 2px solid {FOREST_LIGHT};
        margin-bottom: 12px;
        font-family: 'Barlow Condensed', sans-serif;
        border-radius: 2px;
    }}
    .pick-card .card-header {{
        background: {FOREST_DEEP};
        border-bottom: 2px solid {MUSTARD};
        padding: 12px 20px;
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .pick-card.watch .card-header {{ border-bottom-color: {SAGE}; }}
    .pick-card.no .card-header {{ border-bottom-color: {FOREST_LIGHT}; }}
    .pick-card .helmet-logo {{
        width: 48px;
        height: 48px;
        object-fit: contain;
        flex-shrink: 0;
        filter: drop-shadow(0 2px 6px rgba(0,0,0,0.5));
    }}
    .pick-card .pick-title-block {{
        flex: 1;
        min-width: 0;
    }}
    .pick-card .pick-title {{
        color: {CREAM};
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 1px;
        margin: 0;
    }}
    .pick-card .pick-spread {{ color: {MUSTARD}; }}
    .pick-card.watch .pick-spread {{ color: {SAGE}; }}
    .pick-card.no .pick-spread {{ color: {CREAM_MUTED}; }}
    .pick-card .pick-time {{
        color: {SAGE};
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-top: 2px;
    }}
    .pick-card .trigger-badge {{
        padding: 6px 12px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.5px;
        border-radius: 2px;
        font-family: 'Barlow Condensed', sans-serif;
        flex-shrink: 0;
        white-space: nowrap;
    }}
    .pick-card .trigger-badge.fired {{
        background: {MUSTARD};
        color: {FOREST_DEEP};
        box-shadow: 0 0 12px rgba(212,165,55,0.4);
    }}
    .pick-card .trigger-badge.watch {{
        background: {SAGE};
        color: {FOREST_DEEP};
    }}
    .pick-card .trigger-badge.miss {{
        background: transparent;
        color: {CREAM_MUTED};
        border: 1px solid {FOREST_LIGHT};
    }}
    .pick-card .trigger-badge.unscored {{
        background: transparent;
        color: {SAGE};
        border: 1px dashed {SAGE};
    }}

    /* ── QB INJURY BADGES ───────────────────────────────────────────── */
    .qb-status-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 10px 0 4px 0;
    }}
    .qb-badge {{
        padding: 5px 10px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        border-radius: 2px;
        font-family: 'Barlow Condensed', sans-serif;
        text-transform: uppercase;
    }}
    .qb-badge.dq {{
        background: {BLOOD_RED};
        color: {CREAM};
    }}
    .qb-badge.warn {{
        background: {MUSTARD};
        color: {FOREST_DEEP};
    }}
    .pick-card.dq-override {{
        border-color: {BLOOD_RED};
    }}
    .pick-card.dq-override .card-header {{
        border-bottom-color: {BLOOD_RED};
    }}
    .pick-card .card-body {{ padding: 14px 20px; }}
    .pick-card .metric-row {{
        display: flex;
        gap: 28px;
        margin-bottom: 14px;
        padding-bottom: 12px;
        border-bottom: 1px solid {FOREST_LIGHT};
    }}
    .pick-card .metric {{ }}
    .pick-card .metric-label {{
        color: {SAGE};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
    }}
    .pick-card .metric-value {{
        font-size: 22px;
        font-weight: 800;
        font-family: 'Barlow Condensed', sans-serif;
    }}
    .pick-card .metric-value.edge {{ color: {BRIGHT_GREEN}; }}
    .pick-card .metric-value.gold {{ color: {MUSTARD}; }}
    .pick-card .metric-value.cream {{ color: {CREAM}; }}

    /* ── GAME LINE ROW (spread/total/weather) ────────────────────────── */
    .game-line-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 14px;
        padding-bottom: 12px;
        border-bottom: 1px solid {FOREST_LIGHT};
    }}
    .line-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: {FOREST_DEEP};
        border: 1px solid {FOREST_LIGHT};
        border-radius: 2px;
        padding: 6px 12px;
        font-family: 'Barlow Condensed', sans-serif;
    }}
    .line-chip .line-label {{
        color: {SAGE};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
    }}
    .line-chip .line-value {{
        color: {CREAM};
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    .line-chip.weather .line-value {{ color: {MUSTARD}; }}

    /* ── ODDS BOARD ──────────────────────────────────────────────────── */
    .odds-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 6px;
        margin-bottom: 14px;
    }}
    .odds-tile {{
        background: {FOREST_DEEP};
        color: {CREAM};
        padding: 10px;
        text-align: center;
        border: 2px solid {FOREST_LIGHT};
        border-radius: 2px;
    }}
    .odds-tile.best {{
        background: {MUSTARD};
        color: {FOREST_DEEP};
        border-color: {MUSTARD};
    }}
    .odds-book {{
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1px;
        color: {SAGE};
    }}
    .odds-tile.best .odds-book {{ color: {FOREST_DEEP}; }}
    .odds-line {{
        font-size: 22px;
        font-weight: 800;
        margin-top: 2px;
        font-family: 'Barlow Condensed', sans-serif;
    }}
    .odds-price {{
        font-size: 11px;
        color: {SAGE};
    }}
    .odds-tile.best .odds-price {{ color: {FOREST_DEEP}; font-weight: 700; }}

    /* ── FACTOR CHIPS ────────────────────────────────────────────────── */
    .factor-row {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .factor-chip {{
        padding: 5px 12px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
        font-family: 'Barlow Condensed', sans-serif;
        border-radius: 2px;
    }}
    .factor-chip.on {{ background: {BRIGHT_GREEN}; color: {FOREST_DEEP}; }}
    .factor-chip.off {{ background: {BLOOD_RED}; color: {CREAM}; }}

    /* ── DATAFRAMES ──────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        background: {FOREST_MID};
        border-radius: 4px;
        border: 1px solid {FOREST_LIGHT};
    }}
    .stTextInput input, .stNumberInput input, .stDateInput input {{
        background: {FOREST_MID};
        color: {CREAM};
        border: 1px solid {FOREST_LIGHT};
        font-family: 'Barlow Condensed', sans-serif;
    }}
    .stSelectbox > div > div {{
        background: {FOREST_MID};
        color: {CREAM};
        border: 1px solid {FOREST_LIGHT};
        font-family: 'Barlow Condensed', sans-serif;
    }}
    div[data-baseweb="notification"] {{
        background: {FOREST_MID};
        border-radius: 4px;
    }}
    .streamlit-expanderHeader {{
        background: {FOREST_MID};
        color: {MUSTARD};
        border-radius: 4px;
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        letter-spacing: 1px;
    }}
    hr {{ border-color: {FOREST_LIGHT}; opacity: 0.6; }}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# BOOK-COVER HEADER
# ═══════════════════════════════════════════════════════════════════════════
def header_banner(live_status: str = "live"):
    """live | warn | off"""
    if live_status == "live":
        pill_class, pill_text = "", "● LIVE"
    elif live_status == "warn":
        pill_class, pill_text = "warn", "● HISTORICAL"
    else:
        pill_class, pill_text = "off", "● OFFLINE"

    st.markdown(
        '<div class="book-header">'
        '<div class="tagline">A DATA-DRIVEN NFL ATS SYSTEM</div>'
        '<h1>MARGIN of VICTORY</h1>'
        '<div class="byline">by Ron Zellers · Companion App to the Book</div>'
        f'<div class="live-pill {pill_class}">{pill_text}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "").strip()
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# ═══════════════════════════════════════════════════════════════════════════
# AUTHENTICATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════
import json
import hashlib
import secrets

USERS_FILE = Path(os.environ.get("USERS_FILE_PATH", "/data/users.json"))
if not USERS_FILE.parent.exists():
    USERS_FILE = Path("users.json")
else:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Email leads (marketing list) — separate from authenticated users
LEADS_FILE = USERS_FILE.parent / "leads.csv"

LEAD_COLUMNS = ["email", "name", "source", "captured_at", "converted_to_user"]


def load_leads() -> pd.DataFrame:
    if LEADS_FILE.exists():
        try:
            df = pd.read_csv(LEADS_FILE)
            for col in LEAD_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df[LEAD_COLUMNS]
        except Exception:
            pass
    return pd.DataFrame(columns=LEAD_COLUMNS)


def add_lead(email: str, name: str = "", source: str = "") -> tuple:
    """Store an email lead. Returns (success, message)."""
    email = email.strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return False, "Please enter a valid email address."
    df = load_leads()
    if len(df) > 0 and (df["email"] == email).any():
        return True, "You're already on the list — welcome back!"
    new_row = pd.DataFrame([{
        "email": email,
        "name": name.strip(),
        "source": source.strip(),
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "converted_to_user": "",
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    try:
        df.to_csv(LEADS_FILE, index=False)
        return True, "You're in — check your inbox for weekly picks."
    except Exception as e:
        return False, f"Save failed: {e}"


def _hash_password(password: str, salt: str = None) -> tuple:
    """
    Hash password using PBKDF2-HMAC-SHA256 with random salt.
    Returns (hash_hex, salt_hex). If bcrypt is available we'd use that, but
    PBKDF2 is stdlib and secure enough for a small user base.
    """
    if salt is None:
        salt = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt)
    # 200,000 iterations is 2024-2026 recommended baseline
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, 200_000
    )
    return hash_bytes.hex(), salt


def _verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    try:
        candidate, _ = _hash_password(password, salt_hex)
        return secrets.compare_digest(candidate, hash_hex)
    except Exception:
        return False


def load_users() -> dict:
    """Load users from disk. Auto-creates admin from env vars on first run."""
    users = {}
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        except Exception:
            users = {}

    # First-run bootstrap: create admin from environment variables
    admin_username = os.environ.get("ADMIN_USERNAME", "").strip()
    admin_password = os.environ.get("ADMIN_INITIAL_PASSWORD", "").strip()
    if admin_username and admin_password and admin_username not in users:
        h, s = _hash_password(admin_password)
        users[admin_username] = {
            "password_hash": h,
            "salt": s,
            "role": "admin",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "last_login": None,
        }
        save_users(users)
    return users


def save_users(users: dict):
    """Persist users to disk."""
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save users: {e}")


def add_user(username: str, password: str, role: str = "subscriber") -> tuple:
    """Add a new user. Returns (success, message)."""
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if role not in ("admin", "subscriber"):
        return False, "Invalid role."
    users = load_users()
    if username in users:
        return False, f"User '{username}' already exists."
    h, s = _hash_password(password)
    users[username] = {
        "password_hash": h,
        "salt": s,
        "role": role,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "last_login": None,
    }
    save_users(users)
    return True, f"User '{username}' created as {role}."


def remove_user(username: str) -> tuple:
    """Remove a user. Returns (success, message)."""
    username = username.strip().lower()
    users = load_users()
    if username not in users:
        return False, f"User '{username}' does not exist."
    if users[username]["role"] == "admin":
        # Prevent removing the last admin
        admin_count = sum(1 for u in users.values() if u["role"] == "admin")
        if admin_count <= 1:
            return False, "Cannot remove the last admin."
    del users[username]
    save_users(users)
    return True, f"User '{username}' removed."


def reset_password(username: str, new_password: str) -> tuple:
    """Reset a user's password. Returns (success, message)."""
    username = username.strip().lower()
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    users = load_users()
    if username not in users:
        return False, f"User '{username}' does not exist."
    h, s = _hash_password(new_password)
    users[username]["password_hash"] = h
    users[username]["salt"] = s
    save_users(users)
    return True, f"Password reset for '{username}'."


def authenticate(username: str, password: str) -> dict:
    """Return user dict on success, empty dict on failure."""
    username = username.strip().lower()
    users = load_users()
    if username not in users:
        return {}
    user = users[username]
    if not _verify_password(password, user["password_hash"], user["salt"]):
        return {}
    # Update last login
    users[username]["last_login"] = datetime.now().isoformat(timespec="seconds")
    save_users(users)
    return {
        "username": username,
        "role": user["role"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, ttl=86400)  # 24-hour cache
def get_marquee_stats() -> dict:
    """
    Compute the headline stats (backtest 2022-2024 + current season live if available)
    for display on the public landing page.
    """
    # Use the known validated backtest numbers as the marquee.
    # These come from our 3/3 trigger backtest with min_games=2, 2022-2024.
    marquee = {
        "backtest_wins": 186,
        "backtest_losses": 35,
        "backtest_pushes": 3,
        "backtest_cover_rate": 0.842,
        "backtest_seasons": "2022–2024",
        "live_wins": 0,
        "live_losses": 0,
        "live_pushes": 0,
        "live_cover_rate": None,
        "live_season": "2026",
    }
    # Try to update from real picks_history if it exists
    try:
        picks = load_picks_history()
        settled = picks[
            (picks["trigger_fired"] == 1)
            & (picks["ats_result"].isin(["COVER", "NO_COVER", "PUSH"]))
        ]
        if len(settled) > 0:
            w = (settled["ats_result"] == "COVER").sum()
            l = (settled["ats_result"] == "NO_COVER").sum()
            p = (settled["ats_result"] == "PUSH").sum()
            marquee["live_wins"] = int(w)
            marquee["live_losses"] = int(l)
            marquee["live_pushes"] = int(p)
            dec = w + l
            marquee["live_cover_rate"] = (w / dec) if dec > 0 else None
    except Exception:
        pass
    return marquee


AMAZON_BOOK_URL = "https://www.amazon.com/Margin-Victory-Practical-Playbook-Football/dp/B0FC7J7KPV/ref=tmm_pap_swatch_0"


def render_landing_page():
    """Public marketing landing page — email capture, teaser stats, sign-in link."""
    st.markdown(
        f'<style>'
        f'.landing-hero {{ text-align: center; padding: 20px 0 32px 0; }}'
        f'.landing-hero .kicker {{ color: {MUSTARD}; font-size: 12px;'
        f'                        letter-spacing: 4px; font-family: "Barlow Condensed", sans-serif;'
        f'                        font-weight: 700; }}'
        f'.landing-hero h1 {{ color: {CREAM}; font-family: "Playfair Display", Georgia, serif !important;'
        f'                   font-size: 64px; margin: 12px 0 0 0; letter-spacing: 2px;'
        f'                   text-shadow: 0 0 30px rgba(212,165,55,0.4); text-transform: none;'
        f'                   line-height: 1; }}'
        f'.landing-hero .sub {{ color: {SAGE}; font-size: 16px; letter-spacing: 2px;'
        f'                     font-family: "Barlow Condensed", sans-serif; font-weight: 600;'
        f'                     margin-top: 14px; }}'
        f'.marquee-card {{ background: {FOREST_MID}; border: 2px solid {MUSTARD};'
        f'                border-radius: 8px; padding: 28px 32px; margin: 24px 0;'
        f'                box-shadow: 0 0 40px rgba(212,165,55,0.25); text-align: center; }}'
        f'.marquee-card .headline {{ color: {MUSTARD}; font-family: "Playfair Display", serif !important;'
        f'                          font-size: 48px; font-weight: 700; margin: 0;'
        f'                          text-transform: none; letter-spacing: 1px; }}'
        f'.marquee-card .record {{ color: {CREAM}; font-family: "Barlow Condensed", sans-serif;'
        f'                        font-size: 22px; letter-spacing: 3px; margin-top: 8px; font-weight: 700; }}'
        f'.marquee-card .footnote {{ color: {SAGE}; font-family: "Cormorant Garamond", serif;'
        f'                          font-style: italic; margin-top: 12px; font-size: 14px; }}'
        f'.landing-section {{ background: {FOREST_MID}; border: 1px solid {FOREST_LIGHT};'
        f'                   border-radius: 8px; padding: 24px 28px; margin: 20px 0; }}'
        f'.landing-section h3 {{ color: {MUSTARD}; font-family: "Playfair Display", serif !important;'
        f'                      margin-top: 0; text-transform: none; letter-spacing: 1px; }}'
        f'.landing-section p {{ color: {CREAM}; font-family: "Cormorant Garamond", serif;'
        f'                     font-size: 16px; line-height: 1.6; }}'
        f'.perk-row {{ display: flex; gap: 24px; flex-wrap: wrap; margin-top: 16px; }}'
        f'.perk {{ flex: 1; min-width: 180px; padding: 16px; background: {FOREST_DEEP};'
        f'        border-left: 3px solid {MUSTARD}; border-radius: 4px; }}'
        f'.perk .perk-num {{ color: {MUSTARD}; font-family: "Barlow Condensed", sans-serif;'
        f'                  font-size: 32px; font-weight: 800; }}'
        f'.perk .perk-label {{ color: {CREAM}; font-family: "Barlow Condensed", sans-serif;'
        f'                    letter-spacing: 1.5px; margin-top: 4px; font-size: 13px; font-weight: 700; }}'
        f'.perk .perk-desc {{ color: {SAGE}; font-family: "Cormorant Garamond", serif;'
        f'                   font-style: italic; margin-top: 8px; font-size: 13px; }}'
        f'.book-link {{ display: inline-block; margin-top: 12px; color: {MUSTARD};'
        f'             text-decoration: none; font-family: "Barlow Condensed", sans-serif;'
        f'             font-weight: 700; letter-spacing: 1.5px; border-bottom: 2px solid {MUSTARD};'
        f'             padding-bottom: 2px; }}'
        f'.book-link:hover {{ color: {CREAM}; border-bottom-color: {CREAM}; }}'
        f'</style>',
        unsafe_allow_html=True,
    )

    header_banner("live" if ODDS_API_KEY else "warn")

    # Hero
    st.markdown(
        '<div class="landing-hero">'
        '<div class="kicker">A DATA-DRIVEN NFL ATS SYSTEM</div>'
        '<h1>Margin of Victory</h1>'
        '<div class="sub">3-FACTOR TRIGGER MODEL · LIVE ODDS · SHARP EDGE</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Marquee stat
    stats = get_marquee_stats()
    bw, bl, bp = stats["backtest_wins"], stats["backtest_losses"], stats["backtest_pushes"]
    rate_pct = f"{stats['backtest_cover_rate']*100:.1f}%"
    st.markdown(
        f'<div class="marquee-card">'
        f'<div class="headline">{rate_pct} ATS on Triggered Picks</div>'
        f'<div class="record">{bw}–{bl}–{bp} · SEASONS {stats["backtest_seasons"]}</div>'
        f'<div class="footnote">Validated backtest. Full transparency inside — every pick, every result.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Two-column layout: email capture (left, wider) + sign-in (right)
    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            f'<div class="landing-section">'
            f'<h3>Get Free Weekly Picks</h3>'
            f'<p>Every Sunday morning — that week\'s triggered picks, watch list, and last week\'s '
            f'results delivered to your inbox. No spam. Unsubscribe anytime.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.form("lead_form", clear_on_submit=True):
            email = st.text_input("Email address *", placeholder="you@example.com", key="lead_email")

            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("First name (optional)", placeholder="Your name", key="lead_name")
            with c2:
                source = st.selectbox(
                    "How'd you find us? (optional)",
                    ["", "Twitter/X", "YouTube", "Reddit", "The book", "A friend", "Google", "Other"],
                    key="lead_source",
                )

            submitted = st.form_submit_button("GET FREE WEEKLY PICKS", width="stretch")

        if submitted:
            ok, msg = add_lead(email, name, source)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    with right:
        st.markdown(
            f'<div class="landing-section" style="height:100%;">'
            f'<h3>Already a Member?</h3>'
            f'<p>Sign in to access this week\'s live picks, bet tracking, and the full track record.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("SIGN IN", width="stretch", key="goto_login"):
            st.session_state["show_login"] = True
            st.rerun()

    # Why It Works
    st.markdown(
        f'<div class="landing-section">'
        f'<h3>The 3-Factor Trigger</h3>'
        f'<p>Every game runs through three independent filters. When all three align — and only then — '
        f'the system fires a trigger.</p>'
        f'<div class="perk-row">'
        f'<div class="perk">'
        f'<div class="perk-num">F1</div>'
        f'<div class="perk-label">PERFORMANCE</div>'
        f'<div class="perk-desc">Net EPA gap over rolling 4-week window identifies the sharper team.</div>'
        f'</div>'
        f'<div class="perk">'
        f'<div class="perk-num">F2</div>'
        f'<div class="perk-label">MARKET</div>'
        f'<div class="perk-desc">Line-movement proxy catches when public money and sharp money diverge.</div>'
        f'</div>'
        f'<div class="perk">'
        f'<div class="perk-num">F3</div>'
        f'<div class="perk-label">SITUATIONAL</div>'
        f'<div class="perk-desc">Rest advantage, divisional dog spots, and late-season motivation edges.</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # About the book + Amazon link
    st.markdown(
        f'<div class="landing-section">'
        f'<h3>Companion App to the Book</h3>'
        f'<p><em>MARGIN of VICTORY: A Practical Playbook for Sports Betting Success</em> — the framework '
        f'behind this system, written by Ron Zellers (Vinny Marchetti). This app puts the book\'s method '
        f'to work with live 2026 data, real-time odds, and full transparency on every pick.</p>'
        f'<a href="{AMAZON_BOOK_URL}" target="_blank" class="book-link">BUY THE BOOK ON AMAZON →</a>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<p style="text-align: center; color: {SAGE}; font-size: 11px;'
        f'letter-spacing: 2px; font-family: \'Barlow Condensed\', sans-serif; margin-top: 32px;">'
        f'© MARGIN OF VICTORY · MOVPLAYBOOK.COM · '
        f'<a href="{AMAZON_BOOK_URL}" target="_blank" style="color:{MUSTARD}; text-decoration: none;">GET THE BOOK</a>'
        f'</p>',
        unsafe_allow_html=True,
    )


def render_login_page():
    """Render the sign-in page. Sets st.session_state on success."""
    st.markdown(
        f'<style>'
        f'.login-card {{ background: {FOREST_MID}; border: 2px solid {MUSTARD};'
        f'               border-radius: 8px; padding: 32px 36px; margin-top: 20px;'
        f'               box-shadow: 0 0 40px rgba(212,165,55,0.25); }}'
        f'.login-card h2 {{ color: {CREAM}; font-family: "Barlow Condensed", sans-serif;'
        f'                  font-size: 18px; letter-spacing: 3px; text-align: center;'
        f'                  margin: 0 0 20px 0; }}'
        f'.login-footer {{ text-align: center; margin-top: 24px; color: {CREAM};'
        f'                 font-family: "Cormorant Garamond", serif; font-style: italic;'
        f'                 font-size: 14px; }}'
        f'.login-footer a {{ color: {MUSTARD}; text-decoration: none; font-weight: 700; }}'
        f'</style>',
        unsafe_allow_html=True,
    )

    header_banner("live" if ODDS_API_KEY else "warn")

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<h2>SIGN IN TO YOUR ACCOUNT</h2>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            submitted = st.form_submit_button("SIGN IN", width="stretch")

        if submitted:
            result = authenticate(username, password)
            if result:
                st.session_state["auth_user"] = result["username"]
                st.session_state["auth_role"] = result["role"]
                # Clear the show_login flag so we don't bounce back
                if "show_login" in st.session_state:
                    del st.session_state["show_login"]
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("← Back to Home", width="stretch", key="back_home"):
            if "show_login" in st.session_state:
                del st.session_state["show_login"]
            st.rerun()

        st.markdown(
            f'<p class="login-footer">'
            f'Don\'t have an account? Contact <strong style="color:{MUSTARD};">Ron Zellers</strong> for access.<br>'
            f'<a href="{AMAZON_BOOK_URL}" target="_blank">Buy the book on Amazon →</a>'
            f'</p>',
            unsafe_allow_html=True,
        )


PREFERRED_BOOKS = ["draftkings", "fanduel", "betmgm", "caesars"]
BOOK_DISPLAY = {
    "draftkings": "DK", "fanduel": "FD",
    "betmgm": "MGM", "caesars": "CZR",
    "pointsbetus": "PB", "wynnbet": "WYNN",
    "betrivers": "BR", "unibet_us": "UB",
}

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

# ESPN team abbreviations differ slightly from nflverse for a few teams
ESPN_TEAM_MAP = {
    "LA":  "lar",   # LA Rams
    "LAC": "lac",
    "LV":  "lv",
    "WAS": "wsh",
    "JAX": "jax",
}


def team_helmet_url(team_abbr: str) -> str:
    """Return ESPN CDN URL for a team's helmet logo."""
    if not team_abbr:
        return ""
    espn = ESPN_TEAM_MAP.get(team_abbr, team_abbr.lower())
    return f"https://a.espncdn.com/i/teamlogos/nfl/500/{espn}.png"

# Home stadium coordinates and dome status (for weather lookup)
# Format: team_abbr -> (lat, lon, is_dome_or_retractable_closed)
STADIUM_INFO = {
    "ARI": (33.5276, -112.2626, True),   # State Farm — retractable, usually closed
    "ATL": (33.7554, -84.4009, True),    # Mercedes-Benz — retractable
    "BAL": (39.2780, -76.6227, False),
    "BUF": (42.7738, -78.7870, False),
    "CAR": (35.2258, -80.8528, False),
    "CHI": (41.8623, -87.6167, False),
    "CIN": (39.0955, -84.5161, False),
    "CLE": (41.5061, -81.6995, False),
    "DAL": (32.7473, -97.0945, True),    # AT&T — retractable
    "DEN": (39.7439, -105.0201, False),
    "DET": (42.3400, -83.0456, True),    # Ford Field — dome
    "GB":  (44.5013, -88.0622, False),
    "HOU": (29.6847, -95.4107, True),    # NRG — retractable
    "IND": (39.7601, -86.1639, True),    # Lucas Oil — retractable
    "JAX": (30.3239, -81.6373, False),
    "KC":  (39.0489, -94.4839, False),
    "LV":  (36.0908, -115.1830, True),   # Allegiant — dome
    "LAC": (33.9535, -118.3392, False),  # SoFi — open concourse
    "LA":  (33.9535, -118.3392, False),  # SoFi — open concourse
    "MIA": (25.9580, -80.2389, False),
    "MIN": (44.9738, -93.2577, True),    # US Bank — dome
    "NE":  (42.0909, -71.2643, False),
    "NO":  (29.9509, -90.0812, True),    # Superdome — dome
    "NYG": (40.8135, -74.0745, False),
    "NYJ": (40.8135, -74.0745, False),
    "PHI": (39.9008, -75.1675, False),
    "PIT": (40.4468, -80.0158, False),
    "SF":  (37.4032, -121.9698, False),
    "SEA": (47.5952, -122.3316, False),
    "TB":  (27.9759, -82.5033, False),
    "TEN": (36.1665, -86.7713, False),
    "WAS": (38.9077, -76.8645, False),
}

# ═══════════════════════════════════════════════════════════════════════════
# BET LOG PERSISTENCE (Railway volume)
# ═══════════════════════════════════════════════════════════════════════════
BETS_FILE = Path(os.environ.get("BETS_FILE_PATH", "/data/bets.csv"))
if not BETS_FILE.parent.exists():
    BETS_FILE = Path("bets.csv")
else:
    BETS_FILE.parent.mkdir(parents=True, exist_ok=True)

BET_COLUMNS = [
    "bet_id", "user", "logged_at", "season", "week", "game_date",
    "sharp_side", "opponent", "location", "spread", "amount",
    "odds", "book", "bet_source",
    "factor_score", "epa_gap", "result", "profit"
]

# Weekly picks history — auto-logged every time the picks tab runs.
# Lives next to bets.csv on the Railway volume so it survives restarts and
# builds a real track record over time.
PICKS_FILE = BETS_FILE.parent / "picks_history.csv"

PICKS_COLUMNS = [
    "logged_at", "season", "week", "game_date",
    "home_team", "away_team", "sharp_side", "opponent", "location",
    "sharp_spread", "consensus_total", "epa_gap",
    "rest_advantage", "is_divisional",
    "F1_epa", "F2_line_proxy", "F3_situational",
    "factor_score", "trigger_fired",
    "sharp_qb_starter", "sharp_qb_status", "qb_disqualified",
    "ats_result", "cover_margin",  # filled in later once games are settled
]


def load_picks_history() -> pd.DataFrame:
    if PICKS_FILE.exists():
        try:
            df = pd.read_csv(PICKS_FILE)
            for col in PICKS_COLUMNS:
                if col not in df.columns:
                    df[col] = np.nan
            return df[PICKS_COLUMNS]
        except Exception:
            pass
    return pd.DataFrame(columns=PICKS_COLUMNS)


def log_picks_snapshot(scored_df: pd.DataFrame, season: int, week: int):
    """Save this week's scored games to picks_history.csv if not already logged."""
    if len(scored_df) == 0:
        return
    existing = load_picks_history()
    # Skip if this season+week already logged
    if len(existing) > 0:
        already = (
            (existing["season"] == season) & (existing["week"] == week)
        ).any()
        if already:
            return

    rows = []
    now = datetime.now().isoformat(timespec="seconds")
    for _, row in scored_df.iterrows():
        sqb = row.get("sharp_qb_info", {}) or {}
        rows.append({
            "logged_at": now,
            "season": season,
            "week": week,
            "game_date": row.get("gameday", pd.NaT),
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "sharp_side": row.get("sharp_side"),
            "opponent": row.get("opponent"),
            "location": row.get("location"),
            "sharp_spread": row.get("sharp_spread"),
            "consensus_total": row.get("consensus_total"),
            "epa_gap": row.get("epa_gap_abs"),
            "rest_advantage": row.get("rest_advantage"),
            "is_divisional": row.get("is_divisional"),
            "F1_epa": row.get("F1_epa"),
            "F2_line_proxy": row.get("F2_line_proxy"),
            "F3_situational": row.get("F3_situational"),
            "factor_score": row.get("factor_score"),
            "trigger_fired": row.get("trigger_fired"),
            "sharp_qb_starter": sqb.get("starter"),
            "sharp_qb_status": sqb.get("status"),
            "qb_disqualified": row.get("qb_disqualified", 0),
            "ats_result": np.nan,
            "cover_margin": np.nan,
        })
    new_df = pd.DataFrame(rows)
    combined = pd.concat([existing, new_df], ignore_index=True)
    # Dedupe on game identity to prevent old duplicates from piling up
    if {"season", "week", "home_team", "away_team"}.issubset(combined.columns):
        combined = combined.drop_duplicates(
            subset=["season", "week", "home_team", "away_team"], keep="last"
        ).reset_index(drop=True)
    try:
        combined.to_csv(PICKS_FILE, index=False)
    except Exception:
        pass  # non-fatal — don't break the app if writing fails


@st.cache_data(show_spinner=False, ttl=1800)
def settle_picks_history(season: int) -> pd.DataFrame:
    """
    Auto-settle unresolved picks in picks_history.csv by joining against
    nflverse final scores for the given season. Fills in ats_result and
    cover_margin for any pick whose game is final. Returns the full
    picks_history dataframe with the latest settlement applied, and
    persists it back to disk so future reads already have it.
    """
    picks = load_picks_history()
    if len(picks) == 0:
        return picks

    # Force ats_result to object dtype so we can write string results into it.
    # The column was created with NaN values which pandas inferred as float64,
    # and writing "COVER"/"NO_COVER"/"PUSH" into a float column raises
    # "Invalid value 'NO_COVER' for dtype 'float64'".
    picks["ats_result"] = picks["ats_result"].astype(object)
    picks["cover_margin"] = pd.to_numeric(picks["cover_margin"], errors="coerce")

    # Only touch rows for the given season
    season_mask = picks["season"] == season
    unsettled_mask = season_mask & ~picks["ats_result"].isin(["COVER", "NO_COVER", "PUSH"])
    unsettled = picks[unsettled_mask].copy()
    if len(unsettled) == 0:
        return picks

    # Pull nflverse schedule — has home_score, away_score for completed games
    try:
        sched = load_schedules()
    except Exception:
        return picks

    sched = sched[sched["season"] == season].copy()
    # Keep only completed games (both scores non-null)
    sched = sched[sched["home_score"].notna() & sched["away_score"].notna()].copy()
    if len(sched) == 0:
        return picks  # no completed games yet this season

    sched = sched[["week", "home_team", "away_team", "home_score", "away_score"]].copy()

    # Merge: our pick row has home_team + away_team + week; schedule has final scores
    merged = unsettled.merge(sched, on=["week", "home_team", "away_team"], how="left")
    newly_resolved = merged[merged["home_score"].notna()].copy()
    if len(newly_resolved) == 0:
        return picks  # none of the unsettled games have finished yet

    # Compute ATS result from sharp side's perspective
    # sharp_spread is signed from sharp side's POV: negative = sharp lays points, positive = sharp gets points
    # home_margin = home_score - away_score
    # sharp_margin = home_margin if sharp is home, else -home_margin
    # ATS covered when sharp_margin + sharp_spread > 0 (dog) or sharp_margin > |spread| (fav)
    def compute_ats(row):
        try:
            home_s = float(row["home_score"])
            away_s = float(row["away_score"])
            sharp_side = row["sharp_side"]
            home_t = row["home_team"]
            sharp_is_home = (sharp_side == home_t)
            sharp_margin = (home_s - away_s) if sharp_is_home else (away_s - home_s)
            sharp_spread = float(row["sharp_spread"])
            # sharp_spread is from sharp's POV: fav is negative (lays points), dog is positive (gets points)
            # ATS diff = sharp_margin - |sharp_spread| if fav, sharp_margin + |sharp_spread| if dog
            # Simpler: sharp_margin + sharp_spread > 0 → COVER (works for both fav and dog by sign)
            # Example: Sharp lays -3.5, wins by 7 → margin=7, spread=-3.5, 7+(-3.5)=3.5 > 0 → COVER ✓
            # Example: Sharp gets +3.5, loses by 2 → margin=-2, spread=+3.5, -2+3.5=1.5 > 0 → COVER ✓
            ats_diff = sharp_margin + sharp_spread
            if ats_diff > 0:
                return "COVER", ats_diff
            elif ats_diff < 0:
                return "NO_COVER", ats_diff
            else:
                return "PUSH", 0.0
        except Exception:
            return np.nan, np.nan

    for idx, row in newly_resolved.iterrows():
        result, margin = compute_ats(row)
        # Update the original picks row (match by home/away/week/season)
        update_mask = (
            (picks["season"] == row["season"])
            & (picks["week"] == row["week"])
            & (picks["home_team"] == row["home_team"])
            & (picks["away_team"] == row["away_team"])
        )
        picks.loc[update_mask, "ats_result"] = result
        picks.loc[update_mask, "cover_margin"] = margin

    # Persist settled picks back to disk
    try:
        picks.to_csv(PICKS_FILE, index=False)
    except Exception:
        pass

    return picks


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
# LIVE ODDS
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_live_odds() -> pd.DataFrame:
    if not ODDS_API_KEY:
        return pd.DataFrame()

    url = f"{ODDS_API_BASE}/sports/americanfootball_nfl/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ",".join(PREFERRED_BOOKS + ["betrivers", "pointsbetus"]),
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
    except Exception as e:
        st.session_state["odds_error"] = str(e)
        return pd.DataFrame()

    st.session_state["odds_api_remaining"] = r.headers.get("x-requests-remaining", "?")
    st.session_state["odds_api_used"] = r.headers.get("x-requests-used", "?")

    games = r.json()
    if not games:
        return pd.DataFrame()

    rows = []
    for g in games:
        home = g.get("home_team")
        away = g.get("away_team")
        home_abbr = TEAM_NAME_TO_ABBR.get(home, home)
        away_abbr = TEAM_NAME_TO_ABBR.get(away, away)
        row = {
            "game_id": g.get("id"),
            "home_team": home_abbr, "away_team": away_abbr,
            "home_full": home, "away_full": away,
            "commence_time": g.get("commence_time"),
        }
        for bm in g.get("bookmakers", []):
            book_key = bm.get("key")
            if book_key not in BOOK_DISPLAY:
                continue
            for market in bm.get("markets", []):
                mkey = market.get("key")
                if mkey == "spreads":
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
                elif mkey == "totals":
                    for outcome in market.get("outcomes", []):
                        name = outcome.get("name")  # "Over" or "Under"
                        point = outcome.get("point")
                        price = outcome.get("price")
                        if name == "Over":
                            row[f"{book_key}_total"] = point
                            row[f"{book_key}_over_price"] = price
                        elif name == "Under":
                            row[f"{book_key}_under_price"] = price
        rows.append(row)

    df = pd.DataFrame(rows)
    if len(df) > 0:
        df["commence_time"] = pd.to_datetime(df["commence_time"], errors="coerce")
    return df


def consensus_home_spread(row: pd.Series) -> float:
    vals = []
    for book in PREFERRED_BOOKS:
        col = f"{book}_home_spread"
        if col in row and pd.notna(row[col]):
            vals.append(row[col])
    return np.median(vals) if vals else np.nan


def consensus_total(row: pd.Series) -> float:
    vals = []
    for book in PREFERRED_BOOKS:
        col = f"{book}_total"
        if col in row and pd.notna(row[col]):
            vals.append(row[col])
    return np.median(vals) if vals else np.nan


def filter_odds_to_week(live_odds: pd.DataFrame, schedules_df: pd.DataFrame,
                        season: int, week: int) -> pd.DataFrame:
    """
    Restrict live odds to the games scheduled for the given season+week.
    The Odds API returns ALL upcoming games it knows about (often several weeks
    of futures), so we join against the nflverse schedule to keep only the ones
    that match this week's home/away pairing.
    """
    if len(live_odds) == 0:
        return live_odds

    wk_sched = schedules_df[
        (schedules_df["season"] == season) & (schedules_df["week"] == week)
    ][["home_team", "away_team"]].copy()

    if len(wk_sched) == 0:
        # No schedule to match against — fall back to date-window filter
        today = pd.Timestamp.now().normalize()
        cutoff_start = today - pd.Timedelta(days=1)
        cutoff_end = today + pd.Timedelta(days=8)
        odds = live_odds.copy()
        odds["commence_time"] = pd.to_datetime(odds["commence_time"], errors="coerce")
        return odds[
            (odds["commence_time"] >= cutoff_start)
            & (odds["commence_time"] <= cutoff_end)
        ]

    # Match on home/away abbreviations
    wk_sched["_key"] = wk_sched["home_team"] + "|" + wk_sched["away_team"]
    live_odds = live_odds.copy()
    live_odds["_key"] = live_odds["home_team"] + "|" + live_odds["away_team"]
    return live_odds[live_odds["_key"].isin(wk_sched["_key"])].drop(columns="_key")


# ═══════════════════════════════════════════════════════════════════════════
# WEATHER FETCH — Open-Meteo (free, no key required)
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, ttl=3600)
def fetch_weather_for_game(home_abbr: str, kickoff_iso: str) -> dict:
    """
    Fetch weather forecast for a game's kickoff time at home stadium.
    Returns dict with: temp_f, wind_mph, precip_pct, condition, is_dome, or
    {"error": "reason"} for debuggability.
    """
    if not home_abbr:
        return {"error": "no_team"}
    if home_abbr not in STADIUM_INFO:
        return {"error": f"unknown_team:{home_abbr}"}
    lat, lon, is_dome = STADIUM_INFO[home_abbr]
    if is_dome:
        return {"is_dome": True, "condition": "Indoor"}
    if not kickoff_iso:
        return {"error": "no_kickoff"}

    try:
        # Parse kickoff — could be naive OR tz-aware
        kickoff = pd.to_datetime(kickoff_iso, utc=True, errors="coerce")
        if pd.isna(kickoff):
            return {"error": "bad_kickoff"}
        # Convert to ET so it matches Open-Meteo's timezone param
        kickoff_et = kickoff.tz_convert("America/New_York").tz_localize(None)

        days_out = (kickoff_et.normalize() - pd.Timestamp.now().normalize()).days
        if days_out < -1:
            return {"error": f"past_game:{days_out}d"}
        if days_out > 15:
            return {"error": f"too_far:{days_out}d"}

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,weather_code",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "America/New_York",
            "forecast_days": max(2, min(16, days_out + 2)),
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        hourly = data.get("hourly", {})
        time_strings = hourly.get("time", [])
        if not time_strings:
            return {"error": "no_hourly_data"}

        # Open-Meteo returns local-time strings like "2026-09-21T13:00"
        times = pd.to_datetime(time_strings)  # naive local time (ET)

        # Find closest hour to kickoff (both are ET-naive now)
        deltas = np.abs((times - kickoff_et).total_seconds())
        idx = int(np.argmin(deltas))

        temp = hourly.get("temperature_2m", [None])[idx]
        wind = hourly.get("wind_speed_10m", [None])[idx]
        precip = hourly.get("precipitation_probability", [None])[idx]
        wcode = hourly.get("weather_code", [None])[idx]

        # WMO code → simple label
        if wcode == 0: condition = "Clear"
        elif wcode in (1, 2, 3): condition = "Partly Cloudy"
        elif wcode in (45, 48): condition = "Fog"
        elif wcode in (51, 53, 55, 56, 57): condition = "Drizzle"
        elif wcode in (61, 63, 65, 66, 67): condition = "Rain"
        elif wcode in (71, 73, 75, 77): condition = "Snow"
        elif wcode in (80, 81, 82): condition = "Showers"
        elif wcode in (85, 86): condition = "Snow Showers"
        elif wcode in (95, 96, 99): condition = "Thunder"
        else: condition = "—"

        return {
            "is_dome": False,
            "temp_f": round(temp) if temp is not None else None,
            "wind_mph": round(wind) if wind is not None else None,
            "precip_pct": int(precip) if precip is not None else 0,
            "condition": condition,
        }
    except Exception as e:
        return {"error": f"fetch_failed:{type(e).__name__}"}


def weather_summary(w: dict) -> str:
    """Compact one-line weather summary for card display."""
    if not w:
        return "—"
    if w.get("error"):
        # Surface the error briefly so we can see what's wrong
        return f"(no fx: {w['error']})"
    if w.get("is_dome"):
        return "🏟️ Indoor"
    parts = []
    if w.get("temp_f") is not None:
        parts.append(f"{w['temp_f']}°F")
    if w.get("condition"):
        parts.append(w["condition"])
    if w.get("wind_mph") is not None and w["wind_mph"] >= 1:
        parts.append(f"💨 {w['wind_mph']} mph")
    if w.get("precip_pct", 0) >= 10:
        parts.append(f"☔ {w['precip_pct']}%")
    return " · ".join(parts) if parts else "—"


# ═══════════════════════════════════════════════════════════════════════════
# QB INJURY STATUS — ESPN public API
# ═══════════════════════════════════════════════════════════════════════════
# ESPN team IDs (needed for their roster/injury endpoint)
ESPN_TEAM_IDS = {
    "ARI": 22, "ATL": 1,  "BAL": 33, "BUF": 2,  "CAR": 29,
    "CHI": 3,  "CIN": 4,  "CLE": 5,  "DAL": 6,  "DEN": 7,
    "DET": 8,  "GB":  9,  "HOU": 34, "IND": 11, "JAX": 30,
    "KC":  12, "LV":  13, "LAC": 24, "LA":  14, "MIA": 15,
    "MIN": 16, "NE":  17, "NO":  18, "NYG": 19, "NYJ": 20,
    "PHI": 21, "PIT": 23, "SF":  25, "SEA": 26, "TB":  27,
    "TEN": 10, "WAS": 28,
}

# Statuses that DISQUALIFY a trigger (starter can't play or is very unlikely to)
DQ_STATUSES = {"Out", "Doubtful", "Injured Reserve", "Suspended", "Physically Unable to Perform"}
# Statuses to flag for visibility but not disqualify
FLAG_STATUSES = {"Questionable"}


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_team_qb_status(team_abbr: str) -> dict:
    """
    Return {'starter': name, 'status': designation, 'flag': 'dq'|'warn'|None}
    for a team's starting QB using ESPN's public depth chart + injuries endpoints.
    """
    tid = ESPN_TEAM_IDS.get(team_abbr)
    if not tid:
        return {}
    try:
        # Get roster; look for QB position
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{tid}/roster"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        qbs = []
        for group in data.get("athletes", []):
            if group.get("position") == "offense":
                for a in group.get("items", []):
                    pos = a.get("position", {}).get("abbreviation", "")
                    if pos == "QB":
                        qbs.append(a)
        if not qbs:
            return {}

        # Get injuries for this team
        inj_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{tid}/injuries"
        try:
            ir = requests.get(inj_url, timeout=15)
            ir.raise_for_status()
            injuries = ir.json().get("injuries", [])
        except Exception:
            injuries = []

        # Build a lookup: athlete id -> status
        inj_lookup = {}
        for inj_group in injuries:
            for item in inj_group.get("injuries", []):
                athlete_id = str(item.get("athlete", {}).get("id", ""))
                status = item.get("status", "")
                inj_lookup[athlete_id] = status

        # Starter QB = first in roster listing (ESPN orders by depth chart)
        starter = qbs[0]
        starter_id = str(starter.get("id", ""))
        starter_name = starter.get("displayName", "Unknown")
        status = inj_lookup.get(starter_id, "")

        # Classify
        flag = None
        if status in DQ_STATUSES:
            flag = "dq"
        elif status in FLAG_STATUSES:
            flag = "warn"

        return {
            "starter": starter_name,
            "status": status if status else "Healthy",
            "flag": flag,
        }
    except Exception:
        return {}


def qb_status_badge_html(qb_info: dict, side_label: str) -> str:
    """Return small HTML badge if there's a concern; empty string otherwise."""
    if not qb_info or not qb_info.get("flag"):
        return ""
    flag = qb_info["flag"]
    status = qb_info.get("status", "")
    starter = qb_info.get("starter", "QB")
    if flag == "dq":
        cls = "qb-badge dq"
        icon = "❌"
        label = f"{starter.split()[-1]} {status.upper()}"
    else:
        cls = "qb-badge warn"
        icon = "⚠️"
        label = f"{starter.split()[-1]} Q"
    return f'<span class="{cls}">{icon} {side_label}: {label}</span>'


# ═══════════════════════════════════════════════════════════════════════════
# nflverse LOADERS
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


@st.cache_data(show_spinner=False)
def compute_smart_epa_for_week(target_season: int, target_week: int,
                                min_games: int) -> pd.DataFrame:
    """
    Return a per-team EPA snapshot appropriate for scoring the target week.

    Logic:
      - Try current-season PBP first.
      - If current-season PBP is unavailable (common early in season — nflverse
        hasn't posted the file yet), fall back entirely to prior season's late
        EPA (weeks 15-18 avg) tagged with target (season, week).
      - For weeks 1-2 with min_games >= 2, blend prior season's late EPA for
        any teams that don't yet have the required current-season games.
    """
    # Try current-season EPA — may fail with 404 if nflverse hasn't posted yet
    current_snapshot = pd.DataFrame()
    current_available = True
    try:
        current_epa = compute_lagged_epa((target_season,))
        current_snapshot = current_epa[
            (current_epa["season"] == target_season)
            & (current_epa["week"] == target_week)
        ].copy()
    except Exception:
        current_available = False

    # Full fallback: current-season PBP doesn't exist → use prior season entirely
    if not current_available or len(current_snapshot) == 0:
        try:
            prior_epa = compute_lagged_epa((target_season - 1,))
            prior_late = prior_epa[
                (prior_epa["season"] == target_season - 1)
                & (prior_epa["week"] >= 15)
            ]
            if len(prior_late) == 0:
                # Fall back further: use any week we have
                prior_late = prior_epa[prior_epa["season"] == target_season - 1]
            if len(prior_late) == 0:
                return pd.DataFrame()
            prior_snap = (
                prior_late.groupby("team")
                .agg({"net_epa": "mean", "off_epa": "mean", "def_epa": "mean"})
                .reset_index()
                .rename(columns={"net_epa": "rolling_net_epa"})
            )
            prior_snap["season"] = target_season
            prior_snap["week"] = target_week
            prior_snap["prior_games_played"] = 4
            return prior_snap
        except Exception:
            return pd.DataFrame()

    # Week 3+ or min_games < 2 → current-season only
    if target_week >= 3 or min_games < 2:
        return current_snapshot

    # Weeks 1-2 with min_games >= 2 — blend prior season for missing teams
    try:
        prior_epa = compute_lagged_epa((target_season - 1,))
    except Exception:
        return current_snapshot

    prior_late = prior_epa[
        (prior_epa["season"] == target_season - 1)
        & (prior_epa["week"] >= 15)
    ]
    if len(prior_late) == 0:
        return current_snapshot

    prior_snap = (
        prior_late.groupby("team")
        .agg({"net_epa": "mean", "off_epa": "mean", "def_epa": "mean"})
        .reset_index()
        .rename(columns={"net_epa": "rolling_net_epa"})
    )
    prior_snap["season"] = target_season
    prior_snap["week"] = target_week
    prior_snap["prior_games_played"] = 4

    have_current = set(current_snapshot["team"].tolist())
    prior_only = prior_snap[~prior_snap["team"].isin(have_current)]

    combined = pd.concat([current_snapshot, prior_only], ignore_index=True)
    return combined


def get_current_nfl_context(schedules_df: pd.DataFrame) -> tuple:
    today = pd.Timestamp.now().normalize()
    if "gameday" in schedules_df.columns:
        sd = schedules_df.copy()
        sd["gameday"] = pd.to_datetime(sd["gameday"], errors="coerce")
        upcoming = sd[sd["gameday"] >= today - pd.Timedelta(days=1)]
        if len(upcoming) > 0:
            next_game = upcoming.sort_values("gameday").iloc[0]
            return int(next_game["season"]), int(next_game["week"])
    return int(schedules_df["season"].max()), int(schedules_df["week"].max())


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
    g["location"] = np.where(g["sharp_is_home"], "VS." if True else "@", "@")

    return g


def render_odds_board(row: pd.Series, sharp_team_abbr: str, sharp_is_home: bool) -> str:
    side_suffix = "home" if sharp_is_home else "away"
    prices = []
    for book in PREFERRED_BOOKS:
        sp = row.get(f"{book}_{side_suffix}_spread")
        pr = row.get(f"{book}_{side_suffix}_price")
        if pd.notna(sp) and pd.notna(pr):
            prices.append((book, sp, pr))

    if not prices:
        return f'<p style="color:{SAGE}; font-style:italic; margin:0.5rem 0;">No live odds available.</p>'

    best_spread = max(p[1] for p in prices)
    tiles = []
    for book, sp, pr in prices:
        is_best = (sp == best_spread)
        cls = "odds-tile best" if is_best else "odds-tile"
        book_disp = BOOK_DISPLAY.get(book, book.upper())
        star = ' ★ BEST' if is_best else ''
        tile = (
            f'<div class="{cls}">'
                f'<div class="odds-book">{book_disp}{star}</div>'
                f'<div class="odds-line">{sp:+.1f}</div>'
                f'<div class="odds-price">{int(pr):+d}</div>'
            '</div>'
        )
        tiles.append(tile)
    return f'<div class="odds-grid">{"".join(tiles)}</div>'


# ═══════════════════════════════════════════════════════════════════════════
# AUTH GATE
# ═══════════════════════════════════════════════════════════════════════════
if "auth_user" not in st.session_state:
    # Not signed in — show landing page by default; login when requested
    if st.session_state.get("show_login"):
        render_login_page()
    else:
        render_landing_page()
    st.stop()

# Identify current user
current_user = st.session_state["auth_user"]
current_role = st.session_state["auth_role"]
is_admin = (current_role == "admin")

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR — admin sees full controls; subscriber sees minimal info
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # Everyone sees this — user info + logout
    st.markdown(
        f'<div style="font-family: \'Playfair Display\', Georgia, serif; color: {MUSTARD};'
        f'font-size: 22px; font-weight: 700; letter-spacing: 1px;'
        f'border-bottom: 2px solid {FOREST_LIGHT}; padding-bottom: 12px; margin-bottom: 16px;">'
        f'The Almanac'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
        f'letter-spacing:1px; margin-bottom:8px;">'
        f'SIGNED IN: <strong style="color:{MUSTARD};">{current_user.upper()}</strong><br>'
        f'ROLE: <strong style="color:{BRIGHT_GREEN if is_admin else SAGE};">{current_role.upper()}</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("SIGN OUT", width="stretch"):
        for key in ["auth_user", "auth_role"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.markdown("---")

    if is_admin:
        # ADMIN-ONLY: threshold sliders + API status + refresh button
        st.markdown("### Factor Thresholds")
        epa_threshold = st.slider("F1: Net EPA Gap min", 0.05, 0.25, 0.12, 0.01)
        spread_min = st.slider("Spread band — min", 1.0, 7.0, 3.0, 0.5)
        spread_max = st.slider("Spread band — max", 6.0, 17.0, 10.0, 0.5)
        rest_days = st.slider("F3a: Rest advantage (days)", 1, 7, 3, 1)
        late_week = st.slider("F3c: Late season starts week", 10, 17, 14, 1)
        min_games_seen = st.slider("Min prior games / team", 1, 8, 1, 1)

        st.markdown("---")
        st.markdown("### Default Bet Config")
        default_amount = st.number_input("Bet amount ($)", value=100.0, step=10.0, min_value=1.0)
        default_odds = st.number_input("Odds (American)", value=-110, step=5)
        default_book = st.text_input("Sportsbook", value="DraftKings")

        st.markdown("---")
        st.markdown("### API Status")
        if ODDS_API_KEY:
            remaining = st.session_state.get("odds_api_remaining", "?")
            used = st.session_state.get("odds_api_used", "?")
            st.markdown(
                f'<div style="color:{BRIGHT_GREEN}; font-size:0.85rem;'
                f'font-family: \'Barlow Condensed\', sans-serif; letter-spacing:1px;">'
                f'✓ ODDS API ACTIVE<br>'
                f'USED: {used} / REMAINING: {remaining}'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="color:{BLOOD_RED}; font-size:0.85rem;'
                f'font-family: \'Barlow Condensed\', sans-serif; letter-spacing:1px;">'
                f'⚠ ODDS API DISABLED<br>SET ODDS_API_KEY'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        if st.button("REFRESH LIVE ODDS", width="stretch"):
            st.cache_data.clear()
            st.rerun()
    else:
        # SUBSCRIBER: fixed system config, minimal display
        # Use the SAME defaults the admin sliders default to
        epa_threshold = 0.12
        spread_min = 3.0
        spread_max = 10.0
        rest_days = 3
        late_week = 14
        min_games_seen = 1

        st.markdown("### Default Bet Config")
        default_amount = st.number_input("Bet amount ($)", value=100.0, step=10.0, min_value=1.0)
        default_odds = st.number_input("Odds (American)", value=-110, step=5)
        default_book = st.text_input("Sportsbook", value="DraftKings")

        st.markdown("---")
        st.markdown(
            f'<div style="color:{SAGE}; font-family: \'Cormorant Garamond\', serif;'
            f'font-style: italic; font-size: 13px;">'
            f'System settings and odds refresh are controlled by admin.'
            f'</div>',
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════
# HEADER + TABS
# ═══════════════════════════════════════════════════════════════════════════
has_odds_key = bool(ODDS_API_KEY)
header_banner("live" if has_odds_key else "warn")

# Build tabs list — admin gets an extra Admin panel tab
tab_labels = ["THIS WEEK'S PICKS", "🏆 2026 LIVE RESULTS", "📊 TRACK RECORD", "BET TRACKING", "HISTORICAL BACKTEST"]
if is_admin:
    tab_labels.append("⚙️ ADMIN")

_tabs = st.tabs(tab_labels)
mode_picks = _tabs[0]
mode_results = _tabs[1]
mode_record = _tabs[2]
mode_track = _tabs[3]
mode_bt = _tabs[4]
mode_admin = _tabs[5] if is_admin else None


# ═══════════════════════════════════════════════════════════════════════════
# MODE 1 — THIS WEEK'S PICKS
# ═══════════════════════════════════════════════════════════════════════════
with mode_picks:
    with st.spinner("Loading schedule..."):
        try:
            schedules_all = load_schedules()
            schedules_all["gameday"] = pd.to_datetime(schedules_all["gameday"], errors="coerce")
        except Exception as e:
            st.error(f"Schedule load: {e}")
            st.stop()

    with st.spinner("Fetching live odds..."):
        live_odds = fetch_live_odds()

    current_season, current_week = get_current_nfl_context(schedules_all)

    if len(live_odds) > 0 and ODDS_API_KEY:
        st.markdown(f"""
        <div class="live-banner">
            <strong>● LIVE:</strong> {len(live_odds)} upcoming NFL games with real-time odds
            from {len(PREFERRED_BOOKS)} sportsbooks. Season {current_season}, Week {current_week}.
            Best line shown with ★ and gold highlight.
        </div>
        """, unsafe_allow_html=True)
    elif not ODDS_API_KEY:
        st.markdown(f"""
        <div class="warn-banner">
            <strong>Live odds disabled.</strong> Set ODDS_API_KEY environment variable
            in Railway to enable. Using historical closing lines.
        </div>
        """, unsafe_allow_html=True)
    else:
        err = st.session_state.get("odds_error", "unknown")
        st.markdown(f"""
        <div class="warn-banner">
            <strong>Live odds unavailable:</strong> {err}. Using historical closing lines.
        </div>
        """, unsafe_allow_html=True)

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

    if is_current_week and len(live_odds) > 0:
        # Filter to just this week's games (Odds API returns all upcoming)
        live = filter_odds_to_week(live_odds, schedules_all, selected_season, selected_week)
        if len(live) == 0:
            # Fallback: if no schedule match, take date window +/- 8 days
            live = live_odds.copy()
            live["commence_time"] = pd.to_datetime(live["commence_time"], errors="coerce")
            today_ts = pd.Timestamp.now().normalize()
            live = live[
                (live["commence_time"] >= today_ts - pd.Timedelta(days=1))
                & (live["commence_time"] <= today_ts + pd.Timedelta(days=8))
            ]

        live["spread_line"] = live.apply(consensus_home_spread, axis=1)
        live["consensus_total"] = live.apply(consensus_total, axis=1)
        live["season"] = selected_season
        live["week"] = selected_week
        live["gameday"] = live["commence_time"]
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
        week_games = schedules_all[
            (schedules_all["season"] == selected_season)
            & (schedules_all["week"] == selected_week)
        ].copy()
        # Fall back — no total available historically in nflverse schedule
        if "total_line" in week_games.columns:
            week_games["consensus_total"] = week_games["total_line"]
        else:
            week_games["consensus_total"] = np.nan
        odds_by_gameid = {}

    if len(week_games) == 0:
        st.info(f"No games for Season {selected_season}, Week {selected_week}.")
        st.stop()

    seasons_needed = [selected_season]
    if selected_week <= 4 and selected_season > 2020:
        seasons_needed.append(selected_season - 1)
    seasons_needed = tuple(sorted(set(seasons_needed)))

    with st.spinner(f"Computing EPA for Week {selected_week}..."):
        try:
            weekly_epa = compute_smart_epa_for_week(
                selected_season, selected_week, min_games_seen
            )
        except Exception as e:
            weekly_epa = pd.DataFrame()
            st.warning(f"EPA computation hit an error — falling back to raw slate view. ({e})")

        if len(weekly_epa) == 0:
            st.markdown(
                f'<div class="warn-banner">'
                f'<strong>No {selected_season} EPA data available yet.</strong> '
                f'nflverse hasn\'t posted {selected_season} play-by-play, or no team has enough prior games. '
                f'Showing raw slate below with lines + weather so you can still read the board.'
                f'</div>',
                unsafe_allow_html=True,
            )

    scored = score_games(
        week_games, weekly_epa,
        epa_threshold, spread_min, spread_max, rest_days, late_week, min_games_seen,
        require_result=False
    )

    # Dedupe by game identity and reset index — merges from live odds + schedule
    # can leave duplicate rows or stale indexes, which cause widget-key collisions
    # that render the same card over and over as the user scrolls.
    if len(scored) > 0 and "home_team" in scored.columns and "away_team" in scored.columns:
        scored = scored.drop_duplicates(subset=["home_team", "away_team"], keep="first").reset_index(drop=True)

    # QB injury filter — current-week live only (don't disturb backtest)
    scored["sharp_qb_info"] = [{} for _ in range(len(scored))]
    scored["opp_qb_info"] = [{} for _ in range(len(scored))]
    scored["qb_disqualified"] = 0

    if is_current_week and len(scored) > 0:
        with st.spinner("Checking QB injury status..."):
            # Only fetch QB info for teams that could be triggers or watch (2+ factors)
            teams_to_check = set()
            candidates = scored[scored["factor_score"] >= 2]
            for _, r in candidates.iterrows():
                teams_to_check.add(r["sharp_side"])
                teams_to_check.add(r["opponent"])
            qb_cache = {t: fetch_team_qb_status(t) for t in teams_to_check}

        for idx, r in scored.iterrows():
            sharp_qb = qb_cache.get(r["sharp_side"], {})
            opp_qb = qb_cache.get(r["opponent"], {})
            scored.at[idx, "sharp_qb_info"] = sharp_qb
            scored.at[idx, "opp_qb_info"] = opp_qb
            # DQ only when sharp side has starter Out/Doubtful/etc AND it was a trigger
            if sharp_qb.get("flag") == "dq" and r["trigger_fired"] == 1:
                scored.at[idx, "qb_disqualified"] = 1
                scored.at[idx, "trigger_fired"] = 0  # remove from triggers

    # Auto-log this week's snapshot for track-record persistence.
    # Guard with session state so we only write ONCE per session per week —
    # otherwise repeated writes on every rerun can trigger Streamlit's
    # file watcher and cause an infinite reload loop.
    _snap_key = f"snapshot_logged_{selected_season}_{selected_week}"
    if len(scored) > 0 and is_current_week and not st.session_state.get(_snap_key):
        try:
            log_picks_snapshot(scored, selected_season, selected_week)
        except Exception:
            pass
        st.session_state[_snap_key] = True

    # If no games could be scored (e.g. no prior EPA data yet), show a fallback
    # view of the raw slate so the user still sees matchups + lines + weather.
    if len(scored) == 0:
        st.markdown(
            '<div class="warn-banner">'
            '<strong>EPA data unavailable</strong> — showing raw slate. Factor scoring will begin '
            'once teams have played prior games this season.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<h3 style="color:{MUSTARD}; font-family: \'Playfair Display\', Georgia, serif; '
            f'font-weight: 700; text-transform: none; font-size: 24px; margin-top: 1.5rem;">'
            f'Week {selected_week} Slate ({len(week_games)} games)'
            f'</h3>',
            unsafe_allow_html=True,
        )

        # Dedupe to avoid rendering the same game twice (merge artifacts)
        _fb = week_games.copy()
        if "home_team" in _fb.columns and "away_team" in _fb.columns:
            _fb = _fb.drop_duplicates(subset=["home_team", "away_team"], keep="first").reset_index(drop=True)

        for _, row in _fb.iterrows():
            home = row.get("home_team", "?")
            away = row.get("away_team", "?")
            spread = row.get("spread_line", np.nan)
            total = row.get("consensus_total", np.nan)
            gd = row.get("gameday", pd.NaT)
            gd_str = gd.strftime("%a %m/%d %I:%M %p ET").upper() if pd.notna(gd) else "TBD"
            spread_txt = f"{spread:+.1f}" if pd.notna(spread) else "—"
            total_txt = f"O/U {total:.1f}" if pd.notna(total) else "O/U —"

            kickoff_iso = gd.isoformat() if pd.notna(gd) and hasattr(gd, "isoformat") else ""
            weather = fetch_weather_for_game(home, kickoff_iso)
            wx = weather_summary(weather)

            game_key = f"{home}_{away}"
            odds_html = ""
            if game_key in odds_by_gameid:
                odds_row_data = pd.Series(odds_by_gameid[game_key])
                odds_html = render_odds_board(odds_row_data, home, True)

            # Helmet — show home team helmet in fallback view
            helmet_url = team_helmet_url(home)
            helmet_html = (
                f'<img src="{helmet_url}" class="helmet-logo" alt="{home}"/>'
                if helmet_url else ""
            )

            card_html = (
                '<div class="pick-card no">'
                    '<div class="card-header">'
                        f'{helmet_html}'
                        '<div class="pick-title-block">'
                            f'<div class="pick-title">{away} @ {home} <span class="pick-spread">{spread_txt}</span></div>'
                            f'<div class="pick-time">{gd_str}</div>'
                        '</div>'
                        '<div class="trigger-badge unscored">UNSCORED</div>'
                    '</div>'
                    '<div class="card-body">'
                        '<div class="game-line-row">'
                            f'<span class="line-chip"><span class="line-label">SPREAD (HOME)</span> <span class="line-value">{spread_txt}</span></span>'
                            f'<span class="line-chip"><span class="line-label">TOTAL</span> <span class="line-value">{total_txt}</span></span>'
                            f'<span class="line-chip weather"><span class="line-label">WEATHER</span> <span class="line-value">{wx}</span></span>'
                        '</div>'
                        f'{odds_html}'
                    '</div>'
                '</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

        st.stop()

    triggers = scored[scored["trigger_fired"] == 1]
    dq_triggers = scored[scored.get("qb_disqualified", 0) == 1] if "qb_disqualified" in scored.columns else pd.DataFrame()
    n_triggers = len(triggers)
    n_dq = len(dq_triggers)

    if n_triggers > 0:
        msg = f"★ {n_triggers} TRIGGER{'S' if n_triggers != 1 else ''} FIRED"
    else:
        msg = "NO FULL TRIGGERS — CHECK WATCH LIST"

    st.markdown(f"""
    <div class="callout">
        <h2>{msg}</h2>
        <p>SEASON {selected_season} · WK {selected_week} · {len(scored)} GAMES SCORED</p>
    </div>
    """, unsafe_allow_html=True)

    def render_pick_card(row, is_watch=False, is_not_triggered=False):
        game_date = row.get('gameday', pd.NaT)
        game_date_str = game_date.strftime("%a %m/%d %I:%M %p ET").upper() if pd.notna(game_date) else "TBD"
        spread_txt = f"{row['sharp_spread']:+.1f}"
        opp_prefix = "VS." if row['sharp_is_home'] else "@"
        total_val = row.get("consensus_total", np.nan)
        total_txt = f"O/U {total_val:.1f}" if pd.notna(total_val) else "O/U —"

        kickoff_iso = ""
        if pd.notna(game_date):
            kickoff_iso = game_date.isoformat() if hasattr(game_date, "isoformat") else str(game_date)
        weather = fetch_weather_for_game(row['home_team'], kickoff_iso)
        wx = weather_summary(weather)

        if is_not_triggered:
            card_class = "pick-card no"
            badge_class = "trigger-badge miss"
            badge_text = f"{int(row['factor_score'])}/3 · NO TRIGGER"
        elif is_watch:
            card_class = "pick-card watch"
            badge_class = "trigger-badge watch"
            badge_text = "2/3 · WATCH"
        else:
            card_class = "pick-card"
            badge_class = "trigger-badge fired"
            badge_text = "★ 3/3 · TRIGGERED"

        game_key = f"{row['home_team']}_{row['away_team']}"
        odds_html = ""
        if game_key in odds_by_gameid:
            odds_row = pd.Series(odds_by_gameid[game_key])
            odds_html = render_odds_board(odds_row, row['sharp_side'], row['sharp_is_home'])

        # Helmet — sharp side only
        helmet_url = team_helmet_url(row['sharp_side'])
        helmet_html = f'<img src="{helmet_url}" class="helmet-logo" alt="{row["sharp_side"]}"/>' if helmet_url else ""

        # QB status badges (sharp side + opponent)
        sharp_qb = row.get("sharp_qb_info", {}) or {}
        opp_qb = row.get("opp_qb_info", {}) or {}
        qb_badges = []
        sharp_badge = qb_status_badge_html(sharp_qb, row["sharp_side"])
        opp_badge = qb_status_badge_html(opp_qb, row["opponent"])
        if sharp_badge:
            qb_badges.append(sharp_badge)
        if opp_badge:
            qb_badges.append(opp_badge)
        qb_row_html = ""
        if qb_badges:
            qb_row_html = '<div class="qb-status-row">' + "".join(qb_badges) + '</div>'

        # Card class — apply dq-override styling if QB knocked out a trigger
        was_dq = row.get("qb_disqualified", 0) == 1
        if was_dq:
            card_class = "pick-card no dq-override"
            badge_class = "trigger-badge miss"
            badge_text = "❌ QB OUT · DQ"
        # Factor chips
        f1_c = "on" if row['F1_epa'] else "off"
        f2_c = "on" if row['F2_line_proxy'] else "off"
        f3_c = "on" if row['F3_situational'] else "off"
        f1_s = "✓" if row['F1_epa'] else "✗"
        f2_s = "✓" if row['F2_line_proxy'] else "✗"
        f3_s = "✓" if row['F3_situational'] else "✗"

        card_html = (
            f'<div class="{card_class}">'
                '<div class="card-header">'
                    f'{helmet_html}'
                    '<div class="pick-title-block">'
                        f'<div class="pick-title">{row["sharp_side"]} <span class="pick-spread">{spread_txt}</span> {opp_prefix} {row["opponent"]}</div>'
                        f'<div class="pick-time">{game_date_str}</div>'
                    '</div>'
                    f'<div class="{badge_class}">{badge_text}</div>'
                '</div>'
                '<div class="card-body">'
                    f'{qb_row_html}'
                    '<div class="game-line-row">'
                        f'<span class="line-chip"><span class="line-label">SPREAD</span> <span class="line-value">{spread_txt}</span></span>'
                        f'<span class="line-chip"><span class="line-label">TOTAL</span> <span class="line-value">{total_txt}</span></span>'
                        f'<span class="line-chip weather"><span class="line-label">WEATHER</span> <span class="line-value">{wx}</span></span>'
                    '</div>'
                    '<div class="metric-row">'
                        '<div class="metric">'
                            '<div class="metric-label">EPA EDGE</div>'
                            f'<div class="metric-value edge">+{row["epa_gap_abs"]:.3f}</div>'
                        '</div>'
                        '<div class="metric">'
                            '<div class="metric-label">REST ADV</div>'
                            f'<div class="metric-value gold">{int(row["rest_advantage"]):+d} DAYS</div>'
                        '</div>'
                        '<div class="metric">'
                            '<div class="metric-label">DIV GAME</div>'
                            f'<div class="metric-value cream">{"YES" if row["is_divisional"] else "NO"}</div>'
                        '</div>'
                    '</div>'
                    f'{odds_html}'
                    '<div class="factor-row">'
                        f'<span class="factor-chip {f1_c}">F1 EPA {f1_s}</span>'
                        f'<span class="factor-chip {f2_c}">F2 LINE {f2_s}</span>'
                        f'<span class="factor-chip {f3_c}">F3 SIT {f3_s}</span>'
                    '</div>'
                '</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

    def render_bet_form(row, source, key_prefix):
        # Build STABLE unique key from game identity, not DataFrame index
        # (indexes duplicate after merges, causing Streamlit widget collisions
        # that render the same card over and over)
        home = str(row.get("home_team", "?"))
        away = str(row.get("away_team", "?"))
        uid = f"{key_prefix}_{selected_season}_{selected_week}_{home}_{away}"

        with st.expander(f"LOG BET ON {row['sharp_side']}"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                bet_amount = st.number_input(
                    "Amount ($)", value=default_amount, step=10.0, min_value=1.0,
                    key=f"amt_{uid}"
                )
            with c2:
                bet_odds = st.number_input(
                    "Odds", value=default_odds, step=5,
                    key=f"odds_{uid}"
                )
            with c3:
                bet_book = st.text_input(
                    "Book", value=default_book,
                    key=f"book_{uid}"
                )
            with c4:
                st.write("")
                st.write("")
                if st.button("LOG BET", key=f"log_{uid}", width="stretch"):
                    game_date = row.get('gameday', pd.NaT)
                    game_date_str = game_date.strftime("%a %m/%d") if pd.notna(game_date) else "TBD"
                    add_bet({
                        "user": current_user,
                        "season": selected_season,
                        "week": selected_week,
                        "game_date": game_date_str,
                        "sharp_side": row['sharp_side'],
                        "opponent": row['opponent'],
                        "location": "vs." if row['sharp_is_home'] else "@",
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
        st.markdown(f"""
        <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', Georgia, serif;
                   font-weight: 700; letter-spacing: 1px; text-transform: none;
                   font-size: 24px; margin-top: 1.5rem;">
            ★ All 3 Triggered — Full Alignment ({n_triggers} games)
        </h3>
        """, unsafe_allow_html=True)
        for _, row in triggers.iterrows():
            render_pick_card(row, is_watch=False, is_not_triggered=False)
            render_bet_form(row, "trigger", "trig")
    else:
        st.markdown(f"""
        <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', Georgia, serif;
                   font-weight: 700; letter-spacing: 1px; text-transform: none;
                   font-size: 24px; margin-top: 1.5rem;">
            ★ All 3 Triggered — Full Alignment (0 games)
        </h3>
        <p style="color:{CREAM_MUTED}; font-family: 'Cormorant Garamond', Georgia, serif;
                  font-style: italic;">
            No games fired all three factors this week within the spread band.
        </p>
        """, unsafe_allow_html=True)

    # DQ'd triggers — full alignment but QB scratched
    if n_dq > 0:
        st.markdown(f"""
        <h3 style="color:{BLOOD_RED}; font-family: 'Playfair Display', Georgia, serif;
                   font-weight: 700; letter-spacing: 1px; text-transform: none;
                   font-size: 22px; margin-top: 1.5rem;">
            ❌ Disqualified by QB Injury ({n_dq} games)
        </h3>
        <p style="color:{CREAM_MUTED}; font-family: 'Cormorant Garamond', Georgia, serif;
                  font-style: italic; margin-top: -0.5rem;">
            These games hit all 3 factors but the sharp side's starting QB is Out or Doubtful — EPA data is stale, do not bet.
        </p>
        """, unsafe_allow_html=True)
        for _, row in dq_triggers.iterrows():
            render_pick_card(row, is_watch=False, is_not_triggered=True)
            render_bet_form(row, "manual", "dq")

    two_of_three = scored[(scored["factor_score"] == 2) & (scored["trigger_fired"] == 0) & (scored.get("qb_disqualified", 0) == 0)]
    st.markdown(f"""
    <h3 style="color:{SAGE}; font-family: 'Playfair Display', Georgia, serif;
               font-weight: 700; letter-spacing: 1px; text-transform: none;
               font-size: 22px; margin-top: 1.5rem;">
        2 of 3 Triggered — Watch List ({len(two_of_three)} games)
    </h3>
    <p style="color:{CREAM_MUTED}; font-family: 'Cormorant Garamond', Georgia, serif;
              font-style: italic; margin-top: -0.5rem;">
        Historical hit rate around 71% — worth logging if you like the spot.
    </p>
    """, unsafe_allow_html=True)
    if len(two_of_three) > 0:
        for _, row in two_of_three.iterrows():
            render_pick_card(row, is_watch=True, is_not_triggered=False)
            render_bet_form(row, "watch_list", "watch")
    else:
        st.markdown(f"""
        <p style="color:{CREAM_MUTED}; font-family: 'Cormorant Garamond', Georgia, serif;
                  font-style: italic;">
            No 2-of-3 games this week.
        </p>
        """, unsafe_allow_html=True)

    not_triggered = scored[
        (scored["factor_score"] < 2)
        & (scored.get("qb_disqualified", 0) == 0)
    ]
    st.markdown(f"""
    <h3 style="color:{CREAM_MUTED}; font-family: 'Playfair Display', Georgia, serif;
               font-weight: 700; letter-spacing: 1px; text-transform: none;
               font-size: 22px; margin-top: 1.5rem;">
        Not Triggered ({len(not_triggered)} games)
    </h3>
    <p style="color:{CREAM_MUTED}; font-family: 'Cormorant Garamond', Georgia, serif;
              font-style: italic; margin-top: -0.5rem;">
        Full slate for reference — factor scores 0 or 1.
    </p>
    """, unsafe_allow_html=True)
    if len(not_triggered) > 0:
        for _, row in not_triggered.sort_values("factor_score", ascending=False).iterrows():
            render_pick_card(row, is_watch=False, is_not_triggered=True)
            render_bet_form(row, "manual", "not")


# ═══════════════════════════════════════════════════════════════════════════
# MODE 1.4 — 2026 LIVE RESULTS (auto-settled from nflverse)
# ═══════════════════════════════════════════════════════════════════════════
with mode_results:
    st.markdown(
        f'<h3 style="color:{MUSTARD}; font-family: \'Playfair Display\', serif; text-transform: none;">'
        f'2026 Season — Live Results by Factor Score'
        f'</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:{CREAM}; font-family: \'Cormorant Garamond\', serif; font-size: 15px;">'
        f'Every logged pick, auto-settled against the final box score. See how each factor-score tier is '
        f'actually performing in real time — exactly like the backtest, but on live games.'
        f'</p>',
        unsafe_allow_html=True,
    )

    # Settle picks against nflverse scores
    with st.spinner("Settling results from nflverse scores..."):
        try:
            picks_2026 = settle_picks_history(2026)
        except Exception as e:
            st.error(f"Settlement failed: {e}")
            picks_2026 = load_picks_history()

    if len(picks_2026) == 0:
        st.markdown(
            f'<div class="info-banner">'
            f'<strong>No 2026 picks logged yet.</strong> Head to THIS WEEK\'S PICKS and let the system '
            f'score the slate — picks are auto-logged. Results will populate here as games finish.'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        p26 = picks_2026[picks_2026["season"] == 2026].copy()

        # Dedupe — repeated snapshot writes can leave duplicate rows
        if "home_team" in p26.columns and "away_team" in p26.columns and "week" in p26.columns:
            p26 = p26.drop_duplicates(
                subset=["season", "week", "home_team", "away_team"], keep="last"
            ).reset_index(drop=True)

        # Normalize factor_score to int (it may come back as float from CSV)
        p26["factor_score"] = pd.to_numeric(p26["factor_score"], errors="coerce").fillna(-1).astype(int)

        settled = p26[p26["ats_result"].isin(["COVER", "NO_COVER", "PUSH"])].copy()
        pending = p26[~p26["ats_result"].isin(["COVER", "NO_COVER", "PUSH"])].copy()

        # ── TOP SUMMARY STRIP
        total_logged = len(p26)
        total_settled = len(settled)
        total_pending = len(pending)

        if total_settled == 0:
            st.markdown(
                f'<div class="info-banner">'
                f'<strong>{total_logged} picks logged, 0 settled yet.</strong> Results populate every '
                f'Tuesday after Monday Night Football wraps and nflverse pushes the week\'s box scores.'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            all_c = int((settled["ats_result"] == "COVER").sum())
            all_nc = int((settled["ats_result"] == "NO_COVER").sum())
            all_p = int((settled["ats_result"] == "PUSH").sum())
            all_dec = all_c + all_nc
            all_rate = (all_c / all_dec) if all_dec > 0 else 0
            all_units = all_c * 1.0 - all_nc * 1.1

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("PICKS SETTLED", f"{total_settled}")
            with c2: st.metric("OVERALL RECORD", f"{all_c}–{all_nc}–{all_p}")
            with c3: st.metric("OVERALL COVER", f"{all_rate:.1%}" if all_dec > 0 else "—")
            with c4: st.metric("UNITS (@ -110)", f"{all_units:+.1f}u")

        st.markdown("---")

        # ── BY FACTOR SCORE — 4 tiles (0/3, 1/3, 2/3, 3/3)
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px; margin-top: 16px;">BREAKDOWN BY FACTOR SCORE</h4>',
            unsafe_allow_html=True,
        )

        tier_cols = st.columns(4)
        for i, col in enumerate(tier_cols):
            tier = i  # 0, 1, 2, 3
            tier_df = settled[settled["factor_score"] == tier]
            t_c = int((tier_df["ats_result"] == "COVER").sum())
            t_nc = int((tier_df["ats_result"] == "NO_COVER").sum())
            t_p = int((tier_df["ats_result"] == "PUSH").sum())
            t_dec = t_c + t_nc
            t_rate = (t_c / t_dec) if t_dec > 0 else 0
            t_units = t_c * 1.0 - t_nc * 1.1
            tier_pending = int((p26[p26["factor_score"] == tier]["ats_result"].isna()
                                | ~p26[p26["factor_score"] == tier]["ats_result"].isin(["COVER", "NO_COVER", "PUSH"])).sum())

            label_suffix = " ★" if tier == 3 else ""
            with col:
                st.metric(
                    label=f"SCORE {tier}/3{label_suffix}",
                    value=f"{t_rate:.1%}" if t_dec > 0 else "—",
                    delta=f"{t_c}-{t_nc}-{t_p} ({len(tier_df)} settled)",
                    delta_color="off",
                )

        # Compact table underneath the tiles
        tier_rows = []
        for tier in [3, 2, 1, 0]:
            tier_all = p26[p26["factor_score"] == tier]
            tier_set = settled[settled["factor_score"] == tier]
            t_c = int((tier_set["ats_result"] == "COVER").sum())
            t_nc = int((tier_set["ats_result"] == "NO_COVER").sum())
            t_p = int((tier_set["ats_result"] == "PUSH").sum())
            t_dec = t_c + t_nc
            t_rate = (t_c / t_dec) if t_dec > 0 else np.nan
            t_units = t_c * 1.0 - t_nc * 1.1
            tier_rows.append({
                "Tier": f"{tier}/3" + (" ★ TRIGGER" if tier == 3 else (" WATCH" if tier == 2 else "")),
                "Logged": len(tier_all),
                "Settled": len(tier_set),
                "Pending": len(tier_all) - len(tier_set),
                "Record": f"{t_c}–{t_nc}–{t_p}",
                "Cover Rate": f"{t_rate:.1%}" if not pd.isna(t_rate) else "—",
                "Units": f"{t_units:+.1f}u" if t_dec > 0 else "—",
            })
        st.dataframe(pd.DataFrame(tier_rows), width="stretch", hide_index=True)

        st.markdown("---")

        # ── CUMULATIVE UNITS CHART (3/3 Triggers only — the actionable tier)
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">★ 3/3 TRIGGERS — CUMULATIVE UNITS</h4>',
            unsafe_allow_html=True,
        )
        trig_settled = settled[settled["factor_score"] == 3].copy()
        if len(trig_settled) > 0:
            trig_settled = trig_settled.sort_values(["week"]).copy()
            trig_settled["unit_result"] = trig_settled["ats_result"].map({
                "COVER": 1.0, "NO_COVER": -1.1, "PUSH": 0.0
            })
            trig_settled["cum_units"] = trig_settled["unit_result"].cumsum()
            trig_settled["pick_num"] = range(1, len(trig_settled) + 1)
            chart_df = pd.DataFrame({
                "Pick #": trig_settled["pick_num"],
                "Cumulative Units": trig_settled["cum_units"],
            })
            st.line_chart(chart_df.set_index("Pick #"))
        else:
            st.info("No 3/3 triggers settled yet. Chart will populate as triggered picks resolve.")

        # ── WEEK-BY-WEEK BREAKDOWN
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">WEEK-BY-WEEK (3/3 TRIGGERS)</h4>',
            unsafe_allow_html=True,
        )
        if len(trig_settled) > 0:
            wk_rows = []
            for wk in sorted(trig_settled["week"].unique()):
                wk_df = trig_settled[trig_settled["week"] == wk]
                w_c = int((wk_df["ats_result"] == "COVER").sum())
                w_nc = int((wk_df["ats_result"] == "NO_COVER").sum())
                w_p = int((wk_df["ats_result"] == "PUSH").sum())
                w_units = w_c * 1.0 - w_nc * 1.1
                wk_rows.append({
                    "Week": int(wk),
                    "Triggers": len(wk_df),
                    "Record": f"{w_c}–{w_nc}–{w_p}",
                    "Units": f"{w_units:+.1f}u",
                })
            st.dataframe(pd.DataFrame(wk_rows), width="stretch", hide_index=True)
        else:
            st.caption("Weekly breakdown appears once 3/3 triggered picks settle.")

        st.markdown("---")

        # ── FULL PICK LIST
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">EVERY 2026 PICK</h4>',
            unsafe_allow_html=True,
        )
        # Admin sees factor scores; subscriber doesn't
        if is_admin:
            cols = ["week", "sharp_side", "opponent", "location", "sharp_spread",
                    "F1_epa", "F2_line_proxy", "F3_situational", "factor_score",
                    "trigger_fired", "qb_disqualified",
                    "ats_result", "cover_margin"]
        else:
            cols = ["week", "sharp_side", "opponent", "location", "sharp_spread",
                    "factor_score", "ats_result", "cover_margin"]
        disp = p26[[c for c in cols if c in p26.columns]].copy()
        disp = disp.sort_values(["week", "factor_score"], ascending=[False, False])
        if "sharp_spread" in disp.columns:
            disp["sharp_spread"] = pd.to_numeric(disp["sharp_spread"], errors="coerce").round(1)
        if "cover_margin" in disp.columns:
            disp["cover_margin"] = pd.to_numeric(disp["cover_margin"], errors="coerce").round(1)
        rename_map = {
            "week": "Wk", "sharp_side": "Pick", "opponent": "Opp", "location": "Loc",
            "sharp_spread": "Spread",
            "F1_epa": "F1", "F2_line_proxy": "F2", "F3_situational": "F3",
            "factor_score": "Score", "trigger_fired": "Trig",
            "qb_disqualified": "QB DQ",
            "ats_result": "Result", "cover_margin": "Margin",
        }
        disp = disp.rename(columns=rename_map)
        st.dataframe(disp, width="stretch", hide_index=True, height=400)

        # Export + admin re-settle
        c1, c2 = st.columns(2)
        with c1:
            csv_out = p26.to_csv(index=False)
            st.download_button(
                "📥 EXPORT 2026 PICKS",
                csv_out,
                f"mov_2026_picks_{datetime.now():%Y%m%d}.csv",
                "text/csv",
                width="stretch",
            )
        if is_admin:
            with c2:
                if st.button("🔄 FORCE RE-SETTLE", width="stretch",
                             help="Clear the settlement cache and re-pull nflverse scores"):
                    st.cache_data.clear()
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# MODE 1.5 — TRACK RECORD (full transparency)
# ═══════════════════════════════════════════════════════════════════════════
with mode_record:
    st.markdown(
        f'<h3 style="color:{MUSTARD}; font-family: \'Playfair Display\', serif; text-transform: none;">'
        f'Full Track Record — Every Pick, Every Result'
        f'</h3>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<p style="color:{CREAM}; font-family: \'Cormorant Garamond\', serif; font-size: 15px;">'
        f'Transparency is the entire point. Every triggered pick is logged in advance. Every result is here — '
        f'wins, losses, and pushes. Nothing is hidden after the fact.</p>',
        unsafe_allow_html=True,
    )

    # ── SECTION 1: Backtest 2022-2024 (validated)
    st.markdown(
        f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif; letter-spacing: 2px;'
        f'margin-top: 24px;">VALIDATED BACKTEST · 2022–2024</h4>',
        unsafe_allow_html=True,
    )

    # Load backtest data with default thresholds
    try:
        with st.spinner("Loading historical backtest..."):
            _bt_seasons = (2022, 2023, 2024)
            _bt_weekly = compute_lagged_epa(_bt_seasons)
            _bt_sched = load_schedules()
            _bt_sched = _bt_sched[_bt_sched["season"].isin(_bt_seasons)].copy()
            _bt_results = score_games(
                _bt_sched, _bt_weekly,
                0.12, 3.0, 10.0, 3, 14, 2,
                require_result=True
            )
            _bt_results = _bt_results[_bt_results["ats_result"] != "NO_DATA"].copy()
            _bt_triggered = _bt_results[_bt_results["trigger_fired"] == 1].copy()

        _tc = int((_bt_triggered["ats_result"] == "COVER").sum())
        _tnc = int((_bt_triggered["ats_result"] == "NO_COVER").sum())
        _tp = int((_bt_triggered["ats_result"] == "PUSH").sum())
        _tdec = _tc + _tnc
        _trate = _tc / _tdec if _tdec > 0 else 0

        # Marquee stats
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("COVER RATE", f"{_trate:.1%}" if _tdec > 0 else "—")
        with c2: st.metric("RECORD", f"{_tc}–{_tnc}–{_tp}")
        with c3: st.metric("QUALIFYING PICKS", f"{_tdec + _tp}")
        # Units won at -110 (each loss = -1.1u, each win = +1u)
        _units = _tc * 1.0 - _tnc * 1.1
        with c4: st.metric("UNITS (@ -110)", f"{_units:+.1f}u")

        # Running P/L chart
        _bt_triggered_sorted = _bt_triggered.sort_values(["season", "week"]).copy()
        _bt_triggered_sorted["unit_result"] = _bt_triggered_sorted["ats_result"].map({
            "COVER": 1.0, "NO_COVER": -1.1, "PUSH": 0.0
        })
        _bt_triggered_sorted["cum_units"] = _bt_triggered_sorted["unit_result"].cumsum()
        _bt_triggered_sorted["pick_num"] = range(1, len(_bt_triggered_sorted) + 1)

        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif; letter-spacing: 2px;'
            f'margin-top: 24px;">CUMULATIVE UNITS OVER TIME</h4>',
            unsafe_allow_html=True,
        )
        _chart = pd.DataFrame({
            "Pick #": _bt_triggered_sorted["pick_num"],
            "Cumulative Units": _bt_triggered_sorted["cum_units"],
        })
        st.line_chart(_chart.set_index("Pick #"))

        # Per-season table
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif; letter-spacing: 2px;'
            f'margin-top: 24px;">BY SEASON</h4>',
            unsafe_allow_html=True,
        )
        _rows = []
        for _s in sorted(_bt_seasons):
            _st = _bt_triggered[_bt_triggered["season"] == _s]
            _sc = (_st["ats_result"] == "COVER").sum()
            _snc = (_st["ats_result"] == "NO_COVER").sum()
            _sp = (_st["ats_result"] == "PUSH").sum()
            _sdec = _sc + _snc
            _srate = _sc / _sdec if _sdec > 0 else np.nan
            _rows.append({
                "Season": _s,
                "Triggered": len(_st),
                "Record": f"{_sc}–{_snc}–{_sp}",
                "Cover Rate": f"{_srate:.1%}" if not pd.isna(_srate) else "—",
                "Units": f"{_sc * 1.0 - _snc * 1.1:+.1f}u",
            })
        st.dataframe(pd.DataFrame(_rows), width="stretch", hide_index=True)

        # Individual pick list
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif; letter-spacing: 2px;'
            f'margin-top: 24px;">EVERY TRIGGERED PICK</h4>',
            unsafe_allow_html=True,
        )
        if is_admin:
            _cols = ["season", "week", "sharp_side", "opponent", "location",
                     "sharp_spread", "home_score", "away_score",
                     "epa_gap_abs", "F1_epa", "F2_line_proxy", "F3_situational",
                     "sharp_margin", "ats_result"]
            _admin_note = (
                f'<p style="color:{SAGE}; font-family: \'Cormorant Garamond\', serif;'
                f'font-style: italic; font-size: 13px;">Admin view — factor scores visible.</p>'
            )
            st.markdown(_admin_note, unsafe_allow_html=True)
        else:
            # Subscriber view — hide factor scores/why-it-fired columns
            _cols = ["season", "week", "sharp_side", "opponent", "location",
                     "sharp_spread", "home_score", "away_score",
                     "sharp_margin", "ats_result"]
        _disp = _bt_triggered[[c for c in _cols if c in _bt_triggered.columns]].copy()
        _disp = _disp.sort_values(["season", "week"], ascending=[False, True])
        if "epa_gap_abs" in _disp.columns:
            _disp["epa_gap_abs"] = _disp["epa_gap_abs"].round(3)
        if "sharp_spread" in _disp.columns:
            _disp["sharp_spread"] = _disp["sharp_spread"].round(1)
        # Rename cols to nicer labels
        _rename = {
            "season": "Season", "week": "Wk", "sharp_side": "Pick",
            "opponent": "Opp", "location": "Loc",
            "sharp_spread": "Spread",
            "home_score": "Home Pts", "away_score": "Away Pts",
            "epa_gap_abs": "EPA Gap",
            "F1_epa": "F1", "F2_line_proxy": "F2", "F3_situational": "F3",
            "sharp_margin": "ATS Margin", "ats_result": "Result",
        }
        _disp = _disp.rename(columns=_rename)
        st.dataframe(_disp, width="stretch", hide_index=True, height=500)
    except Exception as e:
        st.warning(f"Historical backtest unavailable: {e}")

    # ── SECTION 2: Live 2026 Season
    st.markdown("---")
    st.markdown(
        f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif; letter-spacing: 2px;'
        f'margin-top: 24px;">LIVE 2026 SEASON</h4>',
        unsafe_allow_html=True,
    )

    _picks_hist = load_picks_history()
    _live_triggered = _picks_hist[_picks_hist["trigger_fired"] == 1] if len(_picks_hist) > 0 else pd.DataFrame()
    _live_settled = _live_triggered[
        _live_triggered["ats_result"].isin(["COVER", "NO_COVER", "PUSH"])
    ] if len(_live_triggered) > 0 else pd.DataFrame()

    if len(_live_settled) == 0:
        st.markdown(
            f'<div class="info-banner">No settled live picks yet for 2026. Track record populates '
            f'as games resolve. Check back after Week 1 Sunday.</div>',
            unsafe_allow_html=True,
        )
        # Still show pending live triggers if any
        _live_pending = _live_triggered[
            ~_live_triggered["ats_result"].isin(["COVER", "NO_COVER", "PUSH"])
        ] if len(_live_triggered) > 0 else pd.DataFrame()
        if len(_live_pending) > 0:
            st.markdown(
                f'<p style="color:{CREAM};">{len(_live_pending)} pending picks awaiting results.</p>',
                unsafe_allow_html=True,
            )
    else:
        _lc = int((_live_settled["ats_result"] == "COVER").sum())
        _lnc = int((_live_settled["ats_result"] == "NO_COVER").sum())
        _lp = int((_live_settled["ats_result"] == "PUSH").sum())
        _ldec = _lc + _lnc
        _lrate = _lc / _ldec if _ldec > 0 else 0
        _lunits = _lc * 1.0 - _lnc * 1.1

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("2026 COVER RATE", f"{_lrate:.1%}" if _ldec > 0 else "—")
        with c2: st.metric("2026 RECORD", f"{_lc}–{_lnc}–{_lp}")
        with c3: st.metric("2026 PICKS", f"{_ldec + _lp}")
        with c4: st.metric("2026 UNITS", f"{_lunits:+.1f}u")

        # Live pick table
        if is_admin:
            _live_cols = ["week", "sharp_side", "opponent", "sharp_spread",
                          "F1_epa", "F2_line_proxy", "F3_situational",
                          "ats_result"]
        else:
            _live_cols = ["week", "sharp_side", "opponent", "sharp_spread", "ats_result"]
        _live_disp = _live_triggered[[c for c in _live_cols if c in _live_triggered.columns]].copy()
        _live_disp = _live_disp.sort_values("week", ascending=False)
        _live_disp = _live_disp.rename(columns=_rename)
        st.dataframe(_live_disp, width="stretch", hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# MODE 2 — BET TRACKING
# ═══════════════════════════════════════════════════════════════════════════
with mode_track:
    bets_df = load_bets()

    # Scope: subscribers only see their own bets; admin sees everyone's
    if not is_admin:
        bets_df = bets_df[bets_df["user"] == current_user].copy()

    # Show scope banner
    if is_admin and len(bets_df) > 0:
        all_users = bets_df["user"].dropna().unique().tolist()
        st.markdown(
            f'<div class="info-banner">'
            f'<strong>ADMIN VIEW:</strong> Showing bets across {len(all_users)} user(s): '
            f'{", ".join(sorted(all_users))}'
            f'</div>',
            unsafe_allow_html=True,
        )

    if len(bets_df) == 0:
        st.markdown(f"""
        <div class="info-banner">
            <strong>No bets logged yet.</strong> Head to THIS WEEK'S PICKS and click
            "LOG BET" on any triggered pick or watch-list game.
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
        with c1: st.metric("RECORD", f"{wins}-{losses}-{pushes}")
        with c2: st.metric("WIN RATE", f"{win_rate:.1%}" if decided > 0 else "—")
        with c3: st.metric("TOTAL P/L", f"${total_profit:,.0f}")
        with c4: st.metric("ROI", f"{roi:.1%}")
        with c5: st.metric("PENDING", f"${pending_wagered:,.0f}",
                            delta=f"{len(pending)} bets" if len(pending) else None)

        st.markdown("---")

        tab_p, tab_all, tab_brk, tab_bnk = st.tabs([
            "PENDING BETS", "ALL BETS", "BREAKDOWNS", "BANKROLL"
        ])

        with tab_p:
            if len(pending) == 0:
                st.info("No pending bets.")
            else:
                st.markdown(f"""
                <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                           text-transform: none; margin-top:1rem;">
                    {len(pending)} Bets Awaiting Result
                </h3>
                """, unsafe_allow_html=True)
                for _, bet in pending.iterrows():
                    bet_id = int(bet["bet_id"])
                    pending_card = (
                        '<div class="pick-card">'
                            '<div class="card-header">'
                                '<div class="pick-title-block">'
                                    f'<div class="pick-title">{bet["sharp_side"]} <span class="pick-spread">{bet["spread"]:+.1f}</span> {bet["location"]} {bet["opponent"]}</div>'
                                    f'<div class="pick-time">{bet.get("game_date", "")}</div>'
                                '</div>'
                                '<div class="trigger-badge miss">PENDING</div>'
                            '</div>'
                            '<div class="card-body">'
                                f'<p style="color:{CREAM}; margin:0;">'
                                    f'<strong style="color:{MUSTARD};">${bet["amount"]:.0f}</strong> @ {int(bet["odds"])} · {bet["book"]} · Source: <em style="color:{SAGE}; font-family:\'Cormorant Garamond\',serif;">{bet["bet_source"]}</em>'
                                '</p>'
                            '</div>'
                        '</div>'
                    )
                    st.markdown(pending_card, unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                    with c1:
                        if st.button("✓ WIN", key=f"win_{bet_id}", width="stretch"):
                            df = load_bets()
                            df.loc[df["bet_id"] == bet_id, "result"] = "WIN"
                            df.loc[df["bet_id"] == bet_id, "profit"] = calc_bet_profit(
                                float(bet["amount"]), int(bet["odds"]), "WIN")
                            save_bets(df)
                            st.rerun()
                    with c2:
                        if st.button("✗ LOSS", key=f"loss_{bet_id}", width="stretch"):
                            df = load_bets()
                            df.loc[df["bet_id"] == bet_id, "result"] = "LOSS"
                            df.loc[df["bet_id"] == bet_id, "profit"] = calc_bet_profit(
                                float(bet["amount"]), int(bet["odds"]), "LOSS")
                            save_bets(df)
                            st.rerun()
                    with c3:
                        if st.button("= PUSH", key=f"push_{bet_id}", width="stretch"):
                            df = load_bets()
                            df.loc[df["bet_id"] == bet_id, "result"] = "PUSH"
                            df.loc[df["bet_id"] == bet_id, "profit"] = 0
                            save_bets(df)
                            st.rerun()
                    with c4:
                        if st.button("DELETE", key=f"del_{bet_id}", width="stretch"):
                            df = load_bets()
                            df = df[df["bet_id"] != bet_id]
                            save_bets(df)
                            st.rerun()

        with tab_all:
            st.markdown(f"""
            <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                       text-transform: none; margin-top:1rem;">
                All {len(bets_df)} Bets
            </h3>
            """, unsafe_allow_html=True)
            if is_admin:
                display_cols = ["logged_at", "user", "season", "week", "game_date",
                                "sharp_side", "opponent", "spread",
                                "amount", "odds", "book", "bet_source",
                                "factor_score", "result", "profit"]
            else:
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
                st.download_button("EXPORT TO CSV", csv,
                                   f"margin_of_victory_bets_{datetime.now():%Y%m%d}.csv",
                                   "text/csv", width="stretch")
            with c2:
                if st.button("CLEAR ALL BETS", width="stretch"):
                    if BETS_FILE.exists():
                        BETS_FILE.unlink()
                    st.rerun()

        with tab_brk:
            if len(settled) == 0:
                st.info("Log and settle some bets to see breakdowns.")
            else:
                st.markdown(f"""
                <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                           text-transform: none; margin-top:1rem;">Performance Breakdowns</h3>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <h4 style="color:{CREAM}; font-family: 'Barlow Condensed', sans-serif;
                           letter-spacing: 2px; margin-top: 1rem;">BY BET SOURCE</h4>
                """, unsafe_allow_html=True)
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

                st.markdown(f"""
                <h4 style="color:{CREAM}; font-family: 'Barlow Condensed', sans-serif;
                           letter-spacing: 2px; margin-top: 1rem;">BY SPORTSBOOK</h4>
                """, unsafe_allow_html=True)
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

                st.markdown(f"""
                <h4 style="color:{CREAM}; font-family: 'Barlow Condensed', sans-serif;
                           letter-spacing: 2px; margin-top: 1rem;">BY WEEK</h4>
                """, unsafe_allow_html=True)
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
                st.markdown(f"""
                <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                           text-transform: none; margin-top:1rem;">Bankroll Growth</h3>
                """, unsafe_allow_html=True)
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
                    st.markdown(f"""
                    <h4 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                               text-transform: none; margin-top: 1.5rem;">Kelly Criterion Bet Sizing</h4>
                    """, unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("FULL KELLY", f"{kelly*100:.1f}%")
                    with c2: st.metric("HALF KELLY (RECOMMENDED)", f"{kelly_half*100:.1f}%")
                    with c3: st.metric("SAMPLE", f"{decided} SETTLED")
                    st.markdown(f"""
                    <p style="color:{CREAM_MUTED}; font-family: 'Cormorant Garamond', serif;
                              font-style: italic; margin-top: 0.5rem;">
                        Based on {win_rate:.1%} win rate at avg odds {avg_odds:.0f}. Half-Kelly reduces variance.
                    </p>
                    """, unsafe_allow_html=True)
                else:
                    st.info(f"Kelly sizing appears after 20+ settled bets. Currently: {decided} settled.")


# ═══════════════════════════════════════════════════════════════════════════
# MODE 3 — HISTORICAL BACKTEST
# ═══════════════════════════════════════════════════════════════════════════
with mode_bt:
    st.markdown(f"""
    <div class="info-banner">
        <strong>Backtest integrity:</strong> EPA is LAGGED (uses only prior games).
        A healthy baseline sits near 50% — that's the sign the ATS math is honest.
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
            st.error(f"Data load: {e}")
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

    st.markdown(f"""
    <div class="callout">
        <h2>★ 3/3 TRIGGER RESULTS</h2>
        <p style="font-size: 2.4rem; margin: 0; font-weight: 800; color: {MUSTARD}; font-family: 'Barlow Condensed', sans-serif; letter-spacing: 2px;">
            {tc}–{tnc}–{tp}
            <span style="font-size: 1.6rem; margin-left: 1rem; color: {CREAM};">{hit_pct} COVER</span>
        </p>
        <p style="margin: 0.5rem 0 0 0; color: {SAGE}; font-weight: 600; letter-spacing: 1px;">
            {tdec + tp} QUALIFYING · BASELINE: {brate:.1%} · EDGE: <strong style="color:{BRIGHT_GREEN};">{(trate - brate)*100:+.1f} PTS</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_sum, tab_trg, tab_fac = st.tabs(["SUMMARY", "TRIGGERED GAMES", "FACTOR BREAKDOWN"])

    with tab_sum:
        st.markdown(f"""
        <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                   text-transform: none; margin-top:1rem;">Hit Rate by Factor Score</h3>
        """, unsafe_allow_html=True)
        cols = st.columns(4)
        for i, col in enumerate(cols):
            subset = bt_results[bt_results["factor_score"] == i]
            c = (subset["ats_result"] == "COVER").sum()
            nc = (subset["ats_result"] == "NO_COVER").sum()
            dec = c + nc
            rate = c / dec if dec > 0 else 0
            with col:
                st.metric(
                    label=f"SCORE {i}/3",
                    value=f"{rate:.1%}" if dec > 0 else "—",
                    delta=f"{c}-{nc} ({len(subset)})",
                    delta_color="off",
                )

        st.markdown("---")
        st.markdown(f"""
        <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                   text-transform: none; margin-top:1rem;">Per-Season Trigger Performance</h3>
        """, unsafe_allow_html=True)
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
        st.markdown(f"""
        <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                   text-transform: none; margin-top:1rem;">{len(bt_triggered)} Triggered Games</h3>
        """, unsafe_allow_html=True)
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
        st.markdown(f"""
        <h3 style="color:{MUSTARD}; font-family: 'Playfair Display', serif;
                   text-transform: none; margin-top:1rem;">Standalone Factor Hit Rates</h3>
        """, unsafe_allow_html=True)
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


# ═══════════════════════════════════════════════════════════════════════════
# MODE 4 — ADMIN PANEL (admin only)
# ═══════════════════════════════════════════════════════════════════════════
if is_admin and mode_admin is not None:
    with mode_admin:
        st.markdown(
            f'<h3 style="color:{MUSTARD}; font-family: \'Playfair Display\', serif; text-transform: none;">'
            f'User Management'
            f'</h3>',
            unsafe_allow_html=True,
        )

        users = load_users()

        # ── User list
        if users:
            user_rows = []
            for uname, u in users.items():
                user_rows.append({
                    "Username": uname,
                    "Role": u.get("role", ""),
                    "Created": u.get("created_at", "—")[:10] if u.get("created_at") else "—",
                    "Last Login": u.get("last_login", "—")[:16] if u.get("last_login") else "Never",
                })
            st.dataframe(pd.DataFrame(user_rows), width="stretch", hide_index=True)

        st.markdown("---")

        # ── Add new user
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">ADD NEW USER</h4>',
            unsafe_allow_html=True,
        )
        with st.form("add_user_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                new_username = st.text_input("Username", key="new_username")
            with c2:
                new_password = st.text_input("Password (min 8 chars)", type="password", key="new_password")
            with c3:
                new_role = st.selectbox("Role", ["subscriber", "admin"], key="new_role")
            if st.form_submit_button("ADD USER", width="stretch"):
                ok, msg = add_user(new_username, new_password, new_role)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("---")

        # ── Reset password
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">RESET USER PASSWORD</h4>',
            unsafe_allow_html=True,
        )
        with st.form("reset_pw_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                reset_user = st.selectbox("User", sorted(users.keys()) if users else [], key="reset_user")
            with c2:
                reset_pw = st.text_input("New password", type="password", key="reset_pw")
            with c3:
                st.write("")
                st.write("")
                if st.form_submit_button("RESET", width="stretch"):
                    ok, msg = reset_password(reset_user, reset_pw)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        st.markdown("---")

        # ── Remove user
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">REMOVE USER</h4>',
            unsafe_allow_html=True,
        )
        removable = [u for u in users if u != current_user]  # can't remove self
        with st.form("remove_user_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                remove_target = st.selectbox("User to remove", sorted(removable) if removable else [],
                                              key="remove_target")
            with c2:
                st.write("")
                st.write("")
                if st.form_submit_button("REMOVE", width="stretch"):
                    if remove_target:
                        ok, msg = remove_user(remove_target)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        st.markdown("---")

        # ── User activity: bets per user
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">USER ACTIVITY</h4>',
            unsafe_allow_html=True,
        )
        all_bets = load_bets()
        if len(all_bets) > 0 and "user" in all_bets.columns:
            all_bets["profit_num"] = pd.to_numeric(all_bets["profit"], errors="coerce")
            activity = all_bets.groupby("user", dropna=False).agg(
                Bets=("bet_id", "count"),
                Wins=("result", lambda x: (x == "WIN").sum()),
                Losses=("result", lambda x: (x == "LOSS").sum()),
                Wagered=("amount", "sum"),
                Profit=("profit_num", "sum"),
            ).reset_index()
            activity["Profit"] = activity["Profit"].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
            )
            activity["Wagered"] = activity["Wagered"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(activity, width="stretch", hide_index=True)
        else:
            st.info("No bet activity yet.")

        # ── Email leads
        st.markdown("---")
        st.markdown(
            f'<h4 style="color:{CREAM}; font-family: \'Barlow Condensed\', sans-serif;'
            f'letter-spacing: 2px;">EMAIL LEADS ({len(load_leads())})</h4>',
            unsafe_allow_html=True,
        )
        leads_df = load_leads()
        if len(leads_df) == 0:
            st.info("No leads captured yet. Once visitors sign up on the landing page, they'll appear here.")
        else:
            # Summary metrics
            _by_source = leads_df["source"].fillna("(none)").replace("", "(none)").value_counts()
            lc1, lc2, lc3 = st.columns(3)
            with lc1: st.metric("TOTAL LEADS", f"{len(leads_df)}")
            with lc2:
                _week_ago = (datetime.now() - pd.Timedelta(days=7)).isoformat()
                _recent = leads_df[leads_df["captured_at"] >= _week_ago]
                st.metric("LAST 7 DAYS", f"{len(_recent)}")
            with lc3:
                _top_source = _by_source.index[0] if len(_by_source) > 0 else "—"
                st.metric("TOP SOURCE", _top_source)

            # Full lead table
            _leads_display = leads_df.sort_values("captured_at", ascending=False).copy()
            st.dataframe(_leads_display, width="stretch", hide_index=True, height=300)

            # Export
            _leads_csv = leads_df.to_csv(index=False)
            st.download_button(
                "📥 EXPORT LEADS TO CSV",
                _leads_csv,
                f"movplaybook_leads_{datetime.now():%Y%m%d}.csv",
                "text/csv",
                width="stretch",
            )


st.markdown("---")
st.markdown(f"""
<p style="text-align: center; color: {SAGE}; font-size: 11px;
          letter-spacing: 2px; font-family: 'Barlow Condensed', sans-serif;">
    MARGIN OF VICTORY · BY RON ZELLERS · LIVE: THE ODDS API · HISTORICAL: NFLVERSE ·
    <a href="{AMAZON_BOOK_URL}" target="_blank" style="color:{MUSTARD}; text-decoration:none; font-weight:700;">
        GET THE BOOK ON AMAZON →
    </a>
    · {datetime.now():%Y-%m-%d %H:%M}
</p>
""", unsafe_allow_html=True)

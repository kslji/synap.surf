#!/usr/bin/env python3
"""
synap/config.py — Central configuration for the AI Brain trading system.
All settings, API keys, risk parameters, and tuning knobs live here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Project paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAIN_DIR = Path(__file__).resolve().parent
LOGS_DIR = BRAIN_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ─── Load .env ───────────────────────────────────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env", override=True)

# ═══════════════════════════════════════════════════════════════════════════════
# API KEYS
# ═══════════════════════════════════════════════════════════════════════════════
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NANSEN_API_KEY = os.getenv("NANSEN_API_KEY", "")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")  # Free demo key
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_token_here")

# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE AI SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
CLAUDE_MAX_TOKENS = 2000
CLAUDE_TEMPERATURE = 0.3  # Low temperature for consistent, analytical responses

# ═══════════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
INITIAL_CAPITAL = float(os.getenv("BRAIN_CAPITAL", "50"))  # Paper trading capital
MAX_OPEN_POSITIONS = 2  # 1 AI bot + 1 strategy engine
MAX_CAPITAL_PER_TRADE_PCT = 0.15  # 15% of capital per trade
MAX_TOTAL_DEPLOYED_PCT = 0.40  # Max 40% capital deployed
MAX_LEVERAGE = 10  # Max leverage allowed
DEFAULT_LEVERAGE = 10  # Default leverage
RISK_PER_TRADE_PCT = 0.02  # 2% risk per trade
MAX_HOLD_HOURS = 72  # Force close after 72h
MIN_ROE_EXIT_PCT = 5.0  # Auto-exit if ROE reaches 5%
# ═══════════════════════════════════════════════════════════════════════════════
# POLLING & TIMING
# ═══════════════════════════════════════════════════════════════════════════════
MAIN_LOOP_INTERVAL_SECONDS = int(
    os.getenv("BRAIN_POLL_INTERVAL", "3600")
)  # Check every 1 hours (no positions — full AI + API scan)
POSITION_MONITOR_INTERVAL_SECONDS = int(
    os.getenv("BRAIN_POSITION_INTERVAL", "60")
)  # Check every 1 min (positions open — SL/TP monitoring only)
TELEGRAM_REPORT_INTERVAL_SECONDS = 1 * 3600  # Report every 1 hours
NANSEN_CACHE_TTL_SECONDS = int(4 * 3600)  # Cache Nansen data for 4 hours
NEWS_CACHE_TTL_SECONDS = 40 * 60  # Cache news data for 40 min
COINGECKO_CACHE_TTL_SECONDS = 10 * 60  # CoinGecko trending updates every 10 min

# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-TIMEFRAME ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
FAST_INTERVAL = "1m"  # For quick 1-5 min reactions
SLOW_INTERVAL = "30m"  # For 1-2 day swing trends
CANDLE_LOOKBACK = 100  # Number of candles per timeframe

# ═══════════════════════════════════════════════════════════════════════════════
# NANSEN CREDIT BUDGET
# ═══════════════════════════════════════════════════════════════════════════════
NANSEN_MONTHLY_BUDGET = 1000
NANSEN_BUDGET_WARNING_PCT = 0.80  # Warn at 80% usage
NANSEN_CREDITS_FILE = LOGS_DIR / "nansen_credits.json"

# ═══════════════════════════════════════════════════════════════════════════════
# HYPERLIQUID
# ═══════════════════════════════════════════════════════════════════════════════
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"
CANDLE_INTERVAL = "1m"  # Default (Fast) interval
CANDLE_LOOKBACK = 200  # Number of candles to fetch per coin

LIVE_TRADING = os.getenv("LIVE_TRADING", "False").lower() in ("true", "1", "yes")
LIVE_PORTFOLIO_STATE_FILE = LOGS_DIR / "portfolio_state_live.json"

# ─── Execution Cost Model (applied in paper trader to mirror live P&L) ────────
# Hyperliquid fee tiers (notional-based, as of 2025):
#   Taker (market orders / aggressive limit): 0.07%
#   Maker (passive limit orders):             0.040%
#   Referral rebate (maker):                 -0.004%  (if using a referral)
# We default to taker on both open & close since market orders are standard
# for algo execution. Switch to MAKER_FEE if you post limit orders.
HL_TAKER_FEE = 0.0007  # 0.07% of notional per leg
HL_MAKER_FEE = 0.00040  # 0.040% of notional per leg
HL_FEE_RATE = HL_TAKER_FEE  # Active rate used by the paper trader

# Slippage estimate — realistic for mid-cap perps on Hyperliquid:
#   BTC/ETH: ~1-2 bps, alts: ~3-5 bps, low-liquidity alts: up to 10 bps
# Applied as a one-way cost on both entry and exit.
HL_SLIPPAGE_BPS = float(
    os.getenv("HL_SLIPPAGE_BPS", "3")
)  # basis points (1 bp = 0.01%)
HL_SLIPPAGE_RATE = HL_SLIPPAGE_BPS / 10_000

# ═══════════════════════════════════════════════════════════════════════════════
# NEWS / SENTIMENT SOURCES (all free)
# ═══════════════════════════════════════════════════════════════════════════════
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL = "https://api.alternative.me/fng/"

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://cryptoslate.com/feed/",
    "https://cryptobriefing.com/feed/",
    "https://www.newsbtc.com/feed/",
    "https://ambcrypto.com/feed/",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://decrypt.co/feed",
]

# ─── NANSEN API ───────────────────────────────────────────────────────────────
NANSEN_BASE_URL = "https://api.nansen.ai/api/v1"

# ═══════════════════════════════════════════════════════════════════════════════
# AI ENGINE SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
BRAIN_TYPE = "CLAUDE"  # Direct Claude AI decision making (MiroFish removed)

# ═══════════════════════════════════════════════════════════════════════════════
# CORE ASSETS (Always watched regardless of volatility)
# ═══════════════════════════════════════════════════════════════════════════════
CORE_WATCHLIST = [
    "BTC",
    "ETH",
    "SOL",
    "SUI",
    "ARB",
    "TIA",
    "LINK",
    "HYPE",
    "ZEC",
    "BNB",
    "XRP",
    "AVAX",
    "TON",
]

# ═══════════════════════════════════════════════════════════════════════════════
# STATE PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════
PORTFOLIO_STATE_FILE = LOGS_DIR / "portfolio_state.json"
WATCHLIST_FILE = LOGS_DIR / "watchlist.json"

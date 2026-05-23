"""
synap/telegram_bot.py — Telegram signal broadcaster + subscriber bot.

Features:
  - /start        → Subscribe to signals
  - /stop         → Unsubscribe
  - /status       → Show bot portfolio stats
  - /watchlist    → Show current volatility leaders
  - /papertrade   → Toggle personal paper trading

Signal broadcasts are sent by TelegramNotifier (called from runner.py).
The polling bot runs in a background thread via run_bot().
"""

import json
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import requests

from hyperliquid.info import Info
from hyperliquid.utils import constants

from synap.config import TELEGRAM_BOT_TOKEN as CONFIG_TG_TOKEN
HL_WALLET = None
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.database import get_sync_db as get_db
logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = Path(__file__).parent.parent / "dashboard" / "users.json"
LOGS_DIR = Path(__file__).parent / "logs"

def get_tg_token():
    try:
        db = get_db()
        doc = db.market_data.find_one({"key": "telegram_settings"})
        if doc and doc.get("telegram_bot_token"):
            return doc["telegram_bot_token"]
    except Exception:
        pass
    # Fallback to config if not set in UI
    if CONFIG_TG_TOKEN and CONFIG_TG_TOKEN != "your_token_here":
        return CONFIG_TG_TOKEN
    return None

# Ensure directories exist on startup
SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_live_hl_portfolio() -> Optional[dict]:
    """
    Fetch balance and open positions directly from Hyperliquid mainnet API.
    Also returns query timestamp and cumulative fees.
    """
    if not HL_WALLET:
        return None

    try:
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        state = info.user_state(HL_WALLET)

        # 1. Parse time
        api_time_ms = state.get("time", int(time.time() * 1000))
        fetched_at = datetime.fromtimestamp(api_time_ms / 1000, tz=timezone.utc)
        fetched_at_str = fetched_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        # 2. Parse balances
        margin_summary = state.get("marginSummary", {})
        equity = float(margin_summary.get("accountValue", 0.0))
        cash = float(state.get("withdrawable", 0.0))

        # 3. Parse active positions
        positions = []
        unrealized_pnl = 0.0
        for entry in state.get("assetPositions", []):
            pos = entry.get("position", {})
            if pos and float(pos.get("szi", 0)) != 0:
                coin = pos["coin"]
                szi = float(pos["szi"])
                side = "LONG" if szi > 0 else "SHORT"
                entry_px = float(pos["entryPx"])
                upnl = float(pos["unrealizedPnl"])
                unrealized_pnl += upnl

                # Leverage info
                lev_val = pos.get("leverage", {})
                leverage = lev_val.get("value", 10) if isinstance(lev_val, dict) else 10
                lev_type = lev_val.get("type", "cross") if isinstance(lev_val, dict) else "cross"
                
                pos_value = float(pos.get("positionValue", abs(szi) * entry_px))
                mark_px = pos_value / abs(szi) if abs(szi) > 0 else entry_px
                liq_px = float(pos.get("liquidationPx", 0))
                margin = float(pos.get("marginUsed", pos_value / leverage if leverage > 0 else pos_value))

                roe_pct = (upnl / margin * 100) if margin > 0 else 0.0

                positions.append({
                    "coin": coin,
                    "side": side,
                    "size": abs(szi),
                    "size_usd": pos_value,
                    "entry_price": entry_px,
                    "mark_price": mark_px,
                    "liquidation_price": liq_px,
                    "margin_used": margin,
                    "leverage_type": lev_type,
                    "unrealized_pnl": upnl,
                    "unrealized_pnl_pct": roe_pct,
                    "leverage": leverage
                })

        # 4. Load cumulative fees from live state file
        cumulative_fees = 0.0

        # 5. Fetch last 20 trades for Realized PnL & Win Rate
        last_20_pnl = 0.0
        last_20_wr = 0.0
        try:
            fills = info.user_fills(HL_WALLET) or []
            closed_fills = [f for f in fills if float(f.get("closedPnl", 0)) != 0]
            # Sort chronologically, then take last 20
            closed_fills.sort(key=lambda x: x.get("time", 0))
            last_20 = closed_fills[-20:]
            if last_20:
                last_20_pnl = sum(float(f["closedPnl"]) for f in last_20)
                wins = sum(1 for f in last_20 if float(f["closedPnl"]) > 0)
                last_20_wr = (wins / len(last_20)) * 100
        except Exception as e:
            logger.error(f"Error fetching user fills: {e}")

        return {
            "cash": cash,
            "total_equity": equity,
            "unrealized_pnl": unrealized_pnl,
            "last_20_realized_pnl": last_20_pnl,
            "last_20_win_rate": last_20_wr,
            "positions": positions,
            "open_position_count": len(positions),
            "fetched_at": fetched_at_str,
            "cumulative_fees": cumulative_fees
        }
    except Exception as e:
        logger.error(f"Error fetching direct Hyperliquid portfolio for Telegram: {e}")
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_data() -> dict:
    if not SUBSCRIBERS_FILE.parent.exists():
        SUBSCRIBERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE) as f:
                return json.load(f)
        except Exception:
            return {"subscribers": [], "paper_traders": {}}

    # Initialize file if missing
    data = {"subscribers": [], "paper_traders": {}}
    _save_data(data)
    return data


def _save_data(data: dict) -> None:
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _tg_post(method: str, payload: dict) -> dict:
    """Low-level POST to Telegram API."""
    token = get_tg_token()
    if not token:
        return {}
    try:
        # Increased timeout to 45s to allow for Telegram Long Polling (30s)
        api_base = f"https://api.telegram.org/bot{token}"
        r = requests.post(f"{api_base}/{method}", json=payload, timeout=45)
        return r.json()
    except Exception as e:
        logger.warning(f"Telegram API error ({method}): {e}")
        return {}


def _send(chat_id: int, text: str, parse_mode: str = "HTML") -> None:
    _tg_post(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        },
    )


# ── TelegramNotifier: called from runner.py ───────────────────────────────────
class TelegramNotifier:
    """
    Broadcasts signals to all subscribers.
    Instantiate once at startup and pass to run_cycle().
    """

    def __init__(self):
        token = get_tg_token()
        if not token:
            logger.warning(
                "Telegram Bot Token not set — Telegram notifications disabled."
            )
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ Telegram notifier ready.")

    def _subscribers(self) -> list[int]:
        data = _load_data()
        return data.get("subscribers", [])

    def broadcast(self, message: str) -> None:
        if not self.enabled:
            return
        for chat_id in self._subscribers():
            _send(chat_id, message)

    def broadcast_trade(self, trade: dict) -> None:
        """Format and broadcast a new trade signal."""
        if not self.enabled:
            return

        action = trade.get("action", "OPEN")
        coin = trade.get("coin", "?")
        side = "📈 LONG" if "LONG" in action else "📉 SHORT"
        entry = trade.get("entry_price", 0)
        sl = trade.get("stop_loss", 0)
        tp1 = trade.get("take_profit_1", 0)
        tp2 = trade.get("take_profit_2", 0)
        conv = int((trade.get("conviction", 0)) * 100)
        lev = trade.get("leverage", 1)
        reason = (trade.get("reasoning", "") or "")[:120]

        # Compute % move to SL and TP1
        if entry > 0:
            sl_pct = abs((sl - entry) / entry * 100)
            tp1_pct = abs((tp1 - entry) / entry * 100)
        else:
            sl_pct = tp1_pct = 0

        msg = (
            f"🤖 <b>ALGO BRAIN SIGNAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{side} — <b>{coin}/USD</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Entry:      <code>${entry:,.4f}</code>\n"
            f"🛑 Stop Loss:  <code>${sl:,.4f}</code>  (-{sl_pct:.1f}%)\n"
            f"🎯 TP1:        <code>${tp1:,.4f}</code>  (+{tp1_pct:.1f}%)\n"
            f"🎯 TP2:        <code>${tp2:,.4f}</code>\n"
            f"⚡ Leverage:   {lev}x\n"
            f"🧠 Conviction: {conv}%\n\n"
            f"📝 {reason}\n\n"
            f"⚠️ <i>Paper trade only. Not financial advice.</i>"
        )
        self.broadcast(msg)

    def broadcast_close(self, update: dict) -> None:
        """Broadcast a position close signal."""
        if not self.enabled:
            return
        coin = update.get("coin", "?")
        reason = (update.get("reasoning", "") or "")[:100]
        msg = (
            f"🔴 <b>CLOSE POSITION — {coin}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 {reason}\n\n"
            f"⚠️ <i>Paper trade only. Not financial advice.</i>"
        )
        self.broadcast(msg)

    def broadcast_cycle_summary(self, stats: dict) -> None:
        """Send a brief end-of-cycle update (only when trades happened)."""
        if not self.enabled:
            return
        equity = stats.get("equity", 1000)
        win_rate = stats.get("win_rate", 0)
        trades = stats.get("total_trades", 0)
        watching = ", ".join(stats.get("watching", [])[:5]) or "—"

        msg = (
            f"📊 <b>Cycle Update</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💵 Equity:    <b>${equity:,.2f}</b>\n"
            f"🎯 Win Rate:  {win_rate}%\n"
            f"📈 Trades:    {trades}\n"
            f"👀 Watching:  {watching}"
        )
        self.broadcast(msg)

    def broadcast_portfolio_report(self, portfolio: dict) -> None:
        """Scheduled full portfolio status report."""
        if not self.enabled:
            return

        # Try to get live Hyperliquid stats
        live_data = get_live_hl_portfolio()
        if live_data:
            equity = live_data["total_equity"]
            cash = live_data["cash"]
            upnl = live_data["unrealized_pnl"]
            fees = live_data["cumulative_fees"]
            fetched_at = live_data["fetched_at"]
            count = live_data["open_position_count"]

            # Load wins/losses/rpnl from live state file
            rpnl = 0.0
            wr = 0.0
            trades = 0
            wins = 0
            losses = 0
            try:
                db = get_db()
                row = db.portfolios.find_one({"user_id": HL_WALLET, "portfolio_type": 'LIVE'})
                if row:
                    rpnl = row.get("realized_pnl", 0)
                    trades = row.get("total_trades", 0)
                    wins = row.get("winning_trades", 0)
                    losses = row.get("losing_trades", 0)
                    wr = round((wins / max(trades, 1)) * 100, 1)
            except Exception:
                pass
            sign = "+" if rpnl >= 0 else ""

            pos_str = ""
            for p in live_data["positions"]:
                side_icon = "📈" if p["side"] == "LONG" else "📉"
                roe = p.get("unrealized_pnl_pct", 0)
                pos_str += f"  • {side_icon} <b>{p['coin']}</b>: {roe:+.2f}% ROE\n"

            if not pos_str:
                pos_str = "  <i>No open positions.</i>"

            msg = (
                f"🔔 <b>PORTFOLIO STATUS REPORT (LIVE)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>Total Equity:  ${equity:,.2f}</b>\n"
                f"💵 Cash:          ${cash:,.2f}\n"
                f"📈 Unrealized:    {upnl:+.2f}\n"
                f"📉 Realized P&L:  {sign}${abs(rpnl):.2f}\n"
                f"💸 Total Fees:    ${fees:.2f}\n"
                f"🎯 Win Rate:      {wr}%\n"
                f"📊 Trades:        {wins}W / {losses}L ({trades} total)\n"
                f"🕒 Fetch Time:     {fetched_at}\n\n"
                f"📂 <b>Open Positions ({count}):</b>\n"
                f"{pos_str}"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🕒 <i>Next report in 2 hours.</i>"
            )
            self.broadcast(msg)
            return

        equity = portfolio.get("total_equity", 0)
        cash = portfolio.get("cash", 0)
        upnl = portfolio.get("unrealized_pnl", 0)
        rpnl = portfolio.get("realized_pnl", 0)
        count = portfolio.get("open_position_count", 0)
        wr = portfolio.get("win_rate", 0)

        # Build positions list
        pos_str = ""
        for p in portfolio.get("positions", []):
            side_icon = "📈" if p["side"] == "LONG" else "📉"
            roe = p.get("unrealized_pnl_pct", 0)
            pos_str += f"  • {side_icon} <b>{p['coin']}</b>: {roe:+.2f}% ROE\n"

        if not pos_str:
            pos_str = "  <i>No open positions.</i>"

        msg = (
            f"🔔 <b>PORTFOLIO STATUS REPORT (PAPER)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Total Equity:  ${equity:,.2f}</b>\n"
            f"💵 Cash:          ${cash:,.2f}\n"
            f"📈 Unrealized:    {upnl:+.2f}\n"
            f"📉 Realized:      {rpnl:+.2f}\n"
            f"🎯 Win Rate:      {wr}%\n\n"
            f"📂 <b>Open Positions ({count}):</b>\n"
            f"{pos_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🕒 <i>Next report in 2 hours.</i>"
        )
        self.broadcast(msg)

    def broadcast_skip(self, reason: str) -> None:
        """Optionally broadcast skip reasons (disabled by default to reduce noise)."""
        pass  # Keep it quiet — only signal on actual trades


# ── Command Handlers ──────────────────────────────────────────────────────────
def _handle_start(chat_id: int, username: str) -> None:
    data = _load_data()
    if chat_id not in data["subscribers"]:
        data["subscribers"].append(chat_id)
        _save_data(data)
        _send(
            chat_id,
            (
                "👋 <b>Welcome to AlgoBrain!</b>\n\n"
                "You are now subscribed to AI trading signals.\n\n"
                "<b>Commands:</b>\n"
                "/status — Bot performance stats\n"
                "/watchlist — Current volatility leaders\n"
                "/papertrade — Enable paper trading\n"
                "/stop — Unsubscribe\n\n"
                "⚠️ <i>Signals are for paper trading only. Not financial advice.</i>"
            ),
        )
    else:
        _send(chat_id, "✅ You are already subscribed!")


def _handle_stop(chat_id: int) -> None:
    data = _load_data()
    if chat_id in data["subscribers"]:
        data["subscribers"].remove(chat_id)
        _save_data(data)
        _send(chat_id, "👋 You have been unsubscribed from AlgoBrain signals.")
    else:
        _send(chat_id, "You were not subscribed.")


def _handle_status(chat_id: int) -> None:
    try:
        # If HL_WALLET is set, we strictly show the live wallet amount and NEVER show paper stats.
        if HL_WALLET:
            live_data = get_live_hl_portfolio()
            if live_data:
                equity = live_data["total_equity"]
                cash = live_data["cash"]
                upnl = live_data["unrealized_pnl"]
                fees = live_data["cumulative_fees"]
                fetched_at = live_data["fetched_at"]
                count = live_data["open_position_count"]

                # Load wins/losses/rpnl from live state file
                rpnl = 0.0
                wr = 0.0
                trades = 0
                wins = 0
                losses = 0
                try:
                    db = get_db()
                    row = db.portfolios.find_one({"user_id": HL_WALLET, "portfolio_type": 'LIVE'})
                    if row:
                        rpnl = row.get("realized_pnl", 0)
                        trades = row.get("total_trades", 0)
                        wins = row.get("winning_trades", 0)
                        losses = row.get("losing_trades", 0)
                        wr = round((wins / max(trades, 1)) * 100, 1)
                except Exception:
                    pass
                sign = "+" if rpnl >= 0 else ""

                pos_str = ""
                for p in live_data["positions"]:
                    side_icon = "📈" if p["side"] == "LONG" else "📉"
                    roe = p.get("unrealized_pnl_pct", 0)
                    pos_str += f"\n  • {side_icon} <b>{p['coin']}</b>: {roe:+.2f}% ROE"

                if not pos_str:
                    pos_str = "\n  <i>No open positions.</i>"

                _send(
                    chat_id,
                    (
                        f"📊 <b>Hyperliquid Live Status</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"💰 <b>Total Equity:  ${equity:,.2f}</b>\n"
                        f"💵 Cash:          ${cash:,.2f}\n"
                        f"📈 Unrealized:    {upnl:+.2f}\n"
                        f"📉 Realized P&L:  {sign}${abs(rpnl):.2f}\n"
                        f"💸 Total Fees:    ${fees:.2f}\n"
                        f"🎯 Win Rate:      {wr}%\n"
                        f"📊 Trades:        {wins}W / {losses}L ({trades} total)\n"
                        f"🕒 Fetch Time:     {fetched_at}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📂 <b>Open Positions ({count}):</b>{pos_str}"
                    ),
                )
            else:
                _send(
                    chat_id,
                    "⚠️ <b>Error fetching Hyperliquid state</b>\n"
                    "Direct API query to your wallet address failed. Please ensure your wallet address and internet connection are correct."
                )
            return

            return
    except Exception as e:
        _send(chat_id, f"⚠️ Error fetching status: {e}")


def _handle_watchlist(chat_id: int) -> None:
    try:
        db = get_db()
        row = db.market_data.find_one({"key": "watchlist"})
        if not row:
            _send(chat_id, "⚠️ No watchlist data yet. Start the bot first.")
            return
        data = json.loads(row.get("value_json", "{}"))
        coins = data.get("coins", [])
        _send(
            chat_id,
            (
                "🔥 <b>Volatility Leaders</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                + "\n".join(f"  • {c}" for c in coins)
                + "\n\n<i>Updated every cycle.</i>"
            ),
        )
    except Exception as e:
        _send(chat_id, f"⚠️ Error: {e}")


def _handle_help(chat_id: int) -> None:
    _send(
        chat_id,
        (
            "🤖 <b>AlgoBrain Commands</b>\n"
            "━━━━━━━━━━━━━━━━━\n"
            "/start      — Subscribe to signals\n"
            "/stop       — Unsubscribe\n"
            "/status     — Portfolio performance\n"
            "/watchlist  — Current focus coins\n"
            "/help       — Show this menu"
        ),
    )


# ── Polling Loop ──────────────────────────────────────────────────────────────
def run_bot() -> None:
    """
    Start the Telegram bot in a background thread.
    Polls for updates and handles commands.
    """
    token = get_tg_token()
    if not token:
        logger.warning("Telegram Bot Token not set — bot polling disabled.")
        return

    logger.info("🤖 Starting Telegram bot polling...")
    offset = 0

    while True:
        try:
            resp = _tg_post(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": ["message"],
                },
            )

            for update in resp.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat = msg.get("chat", {})
                chat_id = chat.get("id")
                text = msg.get("text", "").strip()
                username = msg.get("from", {}).get("username", "user")

                if not chat_id or not text:
                    continue

                cmd = text.split()[0].lower().replace("@algobrain_bot", "")
                if cmd == "/start":
                    _handle_start(chat_id, username)
                elif cmd == "/stop":
                    _handle_stop(chat_id)
                elif cmd == "/status":
                    _handle_status(chat_id)
                elif cmd == "/watchlist":
                    _handle_watchlist(chat_id)
                else:
                    _handle_help(chat_id)

        except Exception as e:
            logger.error(f"Telegram polling error: {e}")
            import time

            time.sleep(5)


def start_bot_thread() -> threading.Thread:
    """Launch the bot polling in a daemon thread."""
    t = threading.Thread(target=run_bot, daemon=True, name="TelegramBot")
    t.start()
    return t

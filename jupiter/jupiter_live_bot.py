"""
jupiter/jupiter_live_bot.py
════════════════════════════════════════════════════════════════════════════════
Jupiter Prediction Market — Live Crypto Token Price Bot
Powered by:  DeepSeek-R1 via Groq (free)
Data from:   Nansen (smart money) + CoinGecko (momentum) — via data_service.py
Storage:     MongoDB — all jupiter___ collections

Trading strategies:
  MOMENTUM  (default) — DeepSeek picks ONE side (YES = price goes UP, NO = DOWN).
                         Enter, poll every 30s, exit at +$0.20 profit or -$0.15 loss.

  STRANGLE  (optional) — Buy BOTH YES + NO simultaneously when market opens.
                          Exit the winning side when its sell price >= $0.78.
                          The loser side decays to ~$0.10 → net profit ~$0.28 per trade.
                          Only viable when combined_cost <= $0.98.

Continuous loop:
  • Spawns a new trade thread whenever open_trades < MAX_OPEN_TRADES
  • Each trade thread polls independently — no global blocking
  • All decisions and results written to MongoDB in real-time

.env requirements:
  JUPITER_API_KEY=...
  GROQ_API_KEY=...          # free at console.groq.com
  NANSEN_API_KEY=...        # you already have this
  COINGECKO_API_KEY=...     # you already have this
  MONGO_URL=...             # you already have this
  WALLET_PUBKEY=...         # Solana wallet public key (for live trading)
  WALLET_KEYPAIR=...        # base58 privkey OR path to keypair.json
  LIVE_TRADING=false        # set true to execute real Solana transactions
  STRANGLE_MODE=false       # set true for buy-both strategy
  BET_USD=5
  PROFIT_TARGET_USD=0.20
  STOP_LOSS_USD=0.15
  POLL_INTERVAL_SECONDS=30
  MAX_OPEN_TRADES=5
  STRANGLE_WINNER_EXIT=0.78  # sell winning side when its price hits this

Install (if not already):
  pip install groq pymongo requests python-dotenv
════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import datetime
import threading
import logging
from typing import Optional

import requests
from dotenv import load_dotenv
from groq import Groq

# ── ensure project root is importable ────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jupiter.data_service import DataService

load_dotenv(os.path.join(ROOT, ".env"), override=True)

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("jupiter_bot")

# ─── Config ───────────────────────────────────────────────────────────────────

GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
JUPITER_API_KEY     = os.getenv("JUPITER_API_KEY", "")
WALLET_PUBKEY       = os.getenv("WALLET_PUBKEY", "")
WALLET_KEYPAIR      = os.getenv("WALLET_KEYPAIR", "")
SOLANA_RPC_URL      = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

LIVE_TRADING        = os.getenv("LIVE_TRADING",  "false").lower() == "true"
STRANGLE_MODE       = os.getenv("STRANGLE_MODE", "false").lower() == "true"

BET_USD             = float(os.getenv("BET_USD",                 "5"))
PROFIT_TARGET_USD   = float(os.getenv("PROFIT_TARGET_USD",       "0.20"))
STOP_LOSS_USD       = float(os.getenv("STOP_LOSS_USD",           "0.15"))
POLL_INTERVAL       = int(os.getenv("POLL_INTERVAL_SECONDS",     "30"))
MAX_OPEN_TRADES     = int(os.getenv("MAX_OPEN_TRADES",           "5"))
MIN_VOLUME_USD      = float(os.getenv("MIN_VOLUME_USD",          "30"))
MAX_MINUTES_TO_CLOSE = int(os.getenv("MAX_MINUTES_TO_CLOSE",    "15"))   # only 5m and 15m markets
MIN_MINUTES_TO_CLOSE = int(os.getenv("MIN_MINUTES_TO_CLOSE",    "2"))    # don't enter with < 2m left
STRANGLE_EXIT_PRICE = float(os.getenv("STRANGLE_WINNER_EXIT",   "0.78"))
MAIN_LOOP_PAUSE     = int(os.getenv("MAIN_LOOP_PAUSE_SECONDS",   "5"))

JUPITER_BASE        = "https://api.jup.ag/prediction/v1"

# ─── Groq / DeepSeek-R1 client ───────────────────────────────────────────────

groq_client = Groq(api_key=GROQ_API_KEY)

# ─── Shared DataService (thread-safe — pymongo is thread-safe) ───────────────

_ds: Optional[DataService] = None

def ds() -> DataService:
    global _ds
    if _ds is None:
        _ds = DataService()
    return _ds

# ─── Helpers ─────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def _extract_json(text: str) -> dict:
    """Pull first JSON object out of DeepSeek-R1 response (strips <think> tags)."""
    # Remove <think>...</think> blocks
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError(f"No JSON object found in LLM response:\n{text[:400]}")
    return json.loads(match.group())

def _to_usd(native: int) -> float:
    return native / 1_000_000

def _close_time_seconds(obj: dict) -> Optional[float]:
    raw = obj.get("closeTime") or obj.get("close_time")
    if not raw:
        return None
    try:
        ct = float(raw)
        return ct / 1000.0 if ct > 1e11 else ct
    except (ValueError, TypeError):
        return None

# ─── Jupiter direct helpers (for live polling — no cache) ────────────────────

def _jup_get(path: str, params: dict = None) -> dict:
    r = requests.get(
        f"{JUPITER_BASE}{path}",
        params=params,
        headers={"x-api-key": JUPITER_API_KEY},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

def _jup_post(path: str, body: dict) -> dict:
    r = requests.post(
        f"{JUPITER_BASE}{path}",
        json=body,
        headers={"x-api-key": JUPITER_API_KEY, "Content-Type": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def get_live_pricing(market_id: str) -> dict:
    """Uncached direct call — used inside poll loop for real-time prices."""
    market = _jup_get(f"/markets/{market_id}")
    p      = market.get("pricing", {})
    ct     = _close_time_seconds(market)
    return {
        "yes_buy":    _to_usd(p.get("buyYesPriceUsd",  0)),
        "yes_sell":   _to_usd(p.get("sellYesPriceUsd", 0)),
        "no_buy":     _to_usd(p.get("buyNoPriceUsd",   0)),
        "no_sell":    _to_usd(p.get("sellNoPriceUsd",  0)),
        "volume_usd": _to_usd(p.get("volume",          0)),
        "close_time": ct,
        "mins_left":  round((ct - time.time()) / 60) if ct else None,
    }

# ─── DeepSeek-R1 Entry Decision ───────────────────────────────────────────────

_ENTRY_PROMPT = """\
You are a quantitative crypto prediction market scalper using DeepSeek-R1 reasoning.

Context:
  Date/time: {now}
  Bet size: ${bet} per side (${bet2} total for STRANGLE)
  Profit target: +${target}  |  Stop loss: -${stop}
  Poll interval: every {poll}s
  Strategy mode: {mode}
  Session stats: {stats}

AVAILABLE MARKETS ({n} markets):
{markets}

STRATEGY RULES:
{strat_rules}

SCORING CRITERIA (evaluate each market — SHORT DURATION ONLY):
1. DURATION PRIORITY — always prefer shorter markets:
     duration_label="5m"  → highest priority (resolves fastest, most trades/hour)
     duration_label="10m" → medium priority
     duration_label="15m" → lowest priority (only if 5m/10m signals are unclear)
   If a 5m market has even MEDIUM confidence, prefer it over a 15m HIGH confidence market.
2. Composite score > 0.30 → lean YES (price going UP)
   Composite score < -0.30 → lean NO (price going DOWN)
3. Nansen STRONG_BULLISH + CoinGecko STRONG_UP → HIGH confidence YES
4. Combined cost < $0.97 and minutes_to_close >= 4 → STRANGLE viable
5. Reject if: volume < $30, combined_cost > $1.02, minutes_to_close < 2
6. For MOMENTUM: avoid YES when implied_yes_pct > 72 (overbought) — bet NO instead
7. The markets list is already sorted shortest-first. Top entries = highest urgency.

Think step-by-step through the top 3 candidates (prefer 5m), then output BEST trade as JSON.

OUTPUT ONLY this JSON (no markdown fences, no extra text outside the JSON):
{{
  "action": "BET" | "SKIP",
  "strategy": "MOMENTUM" | "STRANGLE",
  "market_id": "<id or null>",
  "market_title": "<title or null>",
  "token": "<symbol or null>",
  "side": "YES" | "NO" | "BOTH",
  "entry_price_yes": <float or null>,
  "entry_price_no": <float or null>,
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "estimated_edge_pct": <float>,
  "composite_score": <float>,
  "nansen_signal": "<signal>",
  "coingecko_momentum": "<momentum>",
  "reasoning": "<2-3 sentences explaining the trade>",
  "skip_reason": "<why skipped or null>"
}}
"""

_MOMENTUM_RULES = """\
MOMENTUM MODE: Pick ONE side per trade.
  - YES = you predict token price will be HIGHER at close than price-to-beat
  - NO  = you predict token price will be LOWER at close than price-to-beat
  - Exit immediately when P&L >= +${target} (take profit)
  - Exit immediately when P&L <= -${stop} (stop loss)
  - DeepSeek checks every 2 polls to validate hold vs exit
""".format(target=PROFIT_TARGET_USD, stop=STOP_LOSS_USD)

_STRANGLE_RULES = """\
STRANGLE MODE: Buy BOTH YES and NO simultaneously.
  - Total cost = yes_buy + no_buy (must be <= $0.98 to have positive EV)
  - One side will approach $1.00 as market resolves
  - EXIT the winning side when its SELL price >= ${exit}
  - The losing side decays to near $0 — accept that loss
  - Net expected P&L per strangle: ~+$0.15 to +$0.30 depending on entry timing
  - Only enter if: strangle_viable=true AND minutes_to_close >= 4
""".format(exit=STRANGLE_EXIT_PRICE)


def deepseek_entry_decision(snapshots: list[dict], session_stats: dict) -> dict:
    mode_rules = _STRANGLE_RULES if STRANGLE_MODE else _MOMENTUM_RULES

    # Compact snapshot for LLM (strip raw nested data to save tokens)
    compact_snaps = []
    for s in snapshots:
        sent = s.get("sentiment", {})
        comps = sent.get("components", {})
        compact_snaps.append({
            "market_id":        s["market_id"],
            "market_title":     s["market_title"],
            "token":            s["token"],
            "duration_label":   s.get("duration_label", "?"),   # 5m / 10m / 15m
            "seconds_to_close": s.get("seconds_to_close"),
            "minutes_to_close": s.get("minutes_to_close"),
            "pricing": {
                "yes_buy":         s["pricing"]["yes_buy"],
                "no_buy":          s["pricing"]["no_buy"],
                "combined_cost":   s["pricing"]["combined_cost"],
                "implied_yes_pct": s["pricing"]["implied_yes_pct"],
                "implied_no_pct":  s["pricing"]["implied_no_pct"],
                "volume_usd":      s["pricing"]["volume_usd"],
                "yes_spread":      s["pricing"]["yes_spread"],
            },
            "sentiment": {
                "composite_score": sent.get("composite_score"),
                "direction":       sent.get("direction"),
                "confidence":      sent.get("confidence"),
                "nansen_signal":   (sent.get("raw_nansen") or {}).get("nansen_signal"),
                "cg_momentum":     (sent.get("raw_coingecko") or {}).get("momentum"),
                "cg_1h_pct":       (sent.get("raw_coingecko") or {}).get("change_1h_pct"),
                "nansen_netflow":  (sent.get("raw_nansen") or {}).get("netflow_usd_1h"),
                "dex_buy_sell_ratio": (sent.get("raw_nansen") or {}).get("dex_buy_sell_ratio"),
            },
            "strangle_viable": s.get("strangle_viable", False),
        })

    prompt = _ENTRY_PROMPT.format(
        now=now_iso(),
        bet=BET_USD,
        bet2=BET_USD * 2,
        target=PROFIT_TARGET_USD,
        stop=STOP_LOSS_USD,
        poll=POLL_INTERVAL,
        mode="STRANGLE (buy both sides)" if STRANGLE_MODE else "MOMENTUM (single side)",
        stats=json.dumps(session_stats, indent=None),
        n=len(compact_snaps),
        markets=json.dumps(compact_snaps, indent=2),
        strat_rules=mode_rules,
    )

    log.info("⚡ DeepSeek-R1 entry decision…")
    resp = groq_client.chat.completions.create(
        model="deepseek-r1-distill-llama-70b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=2048,
    )
    raw = resp.choices[0].message.content.strip()
    log.info(f"DeepSeek entry raw (first 300 chars):\n{raw[:300]}")

    decision = _extract_json(raw)
    decision["raw_response"]   = raw
    decision["decision_time"]  = now_iso()
    decision["type"]           = "entry"
    return decision


# ─── DeepSeek-R1 Exit Decision ────────────────────────────────────────────────

_EXIT_PROMPT = """\
You are monitoring an open prediction market position. Decide EXIT or HOLD.

Position snapshot:
{position}

Exit rules:
- EXIT immediately if combined_pnl >= {target} (take profit)
- EXIT immediately if combined_pnl <= -{stop} (stop loss)
- EXIT if minutes_to_close <= 1 (forced expiry close)
- EXIT if market has strongly reversed and recovery is unlikely
- For STRANGLE: EXIT_YES if yes_current_price >= {str_exit}
                EXIT_NO  if no_current_price  >= {str_exit}
- HOLD if thesis intact and P&L within acceptable range

Output ONLY JSON (no markdown):
{{
  "action": "EXIT" | "EXIT_YES" | "EXIT_NO" | "HOLD",
  "reason": "<one sentence>",
  "urgency": "IMMEDIATE" | "NEXT_POLL"
}}
"""


def deepseek_exit_decision(position: dict) -> dict:
    prompt = _EXIT_PROMPT.format(
        position=json.dumps(position, indent=2),
        target=PROFIT_TARGET_USD,
        stop=STOP_LOSS_USD,
        str_exit=STRANGLE_EXIT_PRICE,
    )
    resp = groq_client.chat.completions.create(
        model="deepseek-r1-distill-llama-70b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=256,
    )
    raw = resp.choices[0].message.content.strip()
    try:
        decision = _extract_json(raw)
    except Exception:
        decision = {"action": "HOLD", "reason": "JSON parse error", "urgency": "NEXT_POLL"}
    decision["decision_time"] = now_iso()
    decision["type"]          = "exit"
    return decision


# ─── P&L Calculator ───────────────────────────────────────────────────────────

def compute_pnl(trade: dict, live_prices: dict) -> dict:
    """
    Compute unrealised P&L for a trade.
    Returns dict with yes_pnl, no_pnl, combined_pnl, and current prices.
    """
    side    = trade["side"]
    entry   = trade["entry"]
    result  = {}

    if side in ("YES", "BOTH"):
        ep = entry.get("yes_entry_price") or 0
        ct = entry.get("yes_contracts")   or 0
        cur = live_prices.get("yes_sell", 0)
        result["yes_pnl"]          = round((cur - ep) * ct, 4)
        result["yes_current_price"] = cur

    if side in ("NO", "BOTH"):
        ep  = entry.get("no_entry_price") or 0
        ct  = entry.get("no_contracts")   or 0
        cur = live_prices.get("no_sell", 0)
        result["no_pnl"]           = round((cur - ep) * ct, 4)
        result["no_current_price"] = cur

    if side == "BOTH":
        result["combined_pnl"] = round(
            result.get("yes_pnl", 0) + result.get("no_pnl", 0), 4
        )
    elif side == "YES":
        result["combined_pnl"] = result.get("yes_pnl", 0)
    else:
        result["combined_pnl"] = result.get("no_pnl", 0)

    return result


# ─── Live Order Execution ─────────────────────────────────────────────────────

def execute_live_order(
    market_id: str,
    is_yes: bool,
    is_buy: bool,
    amount_usd: float = 0,
    contracts: float = 0,
) -> Optional[dict]:
    """
    Submit a real Jupiter order.
    Requires LIVE_TRADING=true, WALLET_PUBKEY, WALLET_KEYPAIR.
    """
    if not LIVE_TRADING:
        return None
    if not WALLET_PUBKEY or not WALLET_KEYPAIR:
        log.warning("⚠ LIVE_TRADING=true but WALLET_PUBKEY/WALLET_KEYPAIR missing. Paper mode.")
        return None

    try:
        # Dynamically import on-chain trading libraries to prevent startup crashes when in paper mode
        try:
            import base64
            import base58
            from solana.rpc.api import Client as SolanaClient
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction
        except ImportError:
            log.error(
                "❌ LIVE_TRADING=true but required packages (solana, solders, base58) are not installed. "
                "Run: pip install solana solders base58"
            )
            log.warning("Falling back to Paper Trading mode for this order.")
            return None

        body: dict = {
            "ownerPubkey": WALLET_PUBKEY,
            "marketId":    market_id,
            "isYes":       is_yes,
            "isBuy":       is_buy,
            "depositMint": "JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD",
        }
        if is_buy:
            body["depositAmount"] = str(int(round(amount_usd * 1_000_000)))
        else:
            body["contracts"] = str(contracts)

        order_res = _jup_post("/orders", body)
        tx_b64    = order_res.get("transaction")

        if not tx_b64:
            log.warning(f"No transaction in Jupiter response: {order_res}")
            return None

        # Connect to Solana RPC node
        rpc = SolanaClient(SOLANA_RPC_URL)

        # Load private keypair
        if os.path.isfile(WALLET_KEYPAIR):
            with open(WALLET_KEYPAIR) as f:
                kp_bytes = bytes(json.load(f))
        else:
            kp_bytes = base58.b58decode(WALLET_KEYPAIR)
        keypair = Keypair.from_bytes(kp_bytes)

        # Decode, sign, and broadcast transaction
        tx = VersionedTransaction.from_bytes(base64.b64decode(tx_b64))
        tx.sign([keypair])
        sig_resp = rpc.send_raw_transaction(bytes(tx))
        sig = str(sig_resp.value)
        log.info(f"✅ LIVE TX BROADCASTED: https://solscan.io/tx/{sig}")
        return {"signature": sig}

    except Exception as e:
        log.error(f"Live order failed: {e}")
        return None


# ─── Trade Record Helpers ─────────────────────────────────────────────────────

def open_trade_record(decision: dict, snap: dict) -> dict:
    """Build and persist a new OPEN trade record."""
    side     = decision.get("side", "YES")
    strategy = decision.get("strategy", "MOMENTUM")
    token    = decision.get("token", "?")
    yes_ep   = decision.get("entry_price_yes")
    no_ep    = decision.get("entry_price_no")

    trade = {
        "trade_id":     f"jup_{int(time.time())}_{token}",
        "status":       "OPEN",
        "strategy":     strategy,
        "token":        token,
        "market_id":    decision["market_id"],
        "market_title": decision["market_title"],
        "side":         side,
        "bet_usd":      BET_USD * (2 if side == "BOTH" else 1),
        "entry": {
            "time":            now_iso(),
            "yes_entry_price": yes_ep,
            "no_entry_price":  no_ep,
            "yes_contracts":   round(BET_USD / yes_ep, 4) if yes_ep else None,
            "no_contracts":    round(BET_USD / no_ep,  4) if no_ep  else None,
            "volume_usd":      snap["pricing"]["volume_usd"],
            "composite_score": snap.get("sentiment", {}).get("composite_score"),
            "nansen_signal":   (snap.get("sentiment", {}).get("raw_nansen") or {}).get("nansen_signal"),
            "cg_momentum":     (snap.get("sentiment", {}).get("raw_coingecko") or {}).get("momentum"),
        },
        "exit":                None,
        "pnl_usd":             None,
        "profit_target_usd":   PROFIT_TARGET_USD,
        "stop_loss_usd":       STOP_LOSS_USD,
        "llm_reasoning":       decision.get("reasoning"),
        "llm_confidence":      decision.get("confidence"),
        "estimated_edge_pct":  decision.get("estimated_edge_pct"),
    }
    ds().save_trade(trade)
    log.info(f"📝 Trade opened  id={trade['trade_id']}  {side} [{token}]")
    return trade


def close_trade_record(trade: dict, pnl_usd: float, exit_details: dict, reason: str) -> None:
    """Persist closed trade state to MongoDB."""
    updates = {
        "status":  "CLOSED",
        "pnl_usd": round(pnl_usd, 4),
        "exit": {
            **exit_details,
            "time":   now_iso(),
            "reason": reason,
        },
    }
    ds().update_trade(trade["trade_id"], updates)
    emoji = "🟢" if pnl_usd > 0 else "🔴"
    log.info(
        f"{emoji} Trade closed  id={trade['trade_id']}  "
        f"P&L=${pnl_usd:+.4f}  [{trade.get('token')}]  ({reason})"
    )


# ─── Trade Lifecycle (runs in its own thread) ─────────────────────────────────

def run_trade(entry_decision: dict, entry_snap: dict) -> None:
    """
    Full trade lifecycle: enter → poll → exit.
    Spawned as a daemon thread by the main loop.
    """
    market_id = entry_decision["market_id"]
    token     = entry_decision.get("token", "?")
    side      = entry_decision.get("side", "YES")
    strategy  = entry_decision.get("strategy", "MOMENTUM")
    title     = entry_decision.get("market_title", "")

    log.info(f"\n{'═'*60}")
    log.info(f"🚀 ENTER {strategy}/{side} on [{token}] '{title}'")
    log.info(f"   Confidence: {entry_decision.get('confidence')}  "
             f"Edge: {entry_decision.get('estimated_edge_pct')}%  "
             f"Score: {entry_decision.get('composite_score')}")
    log.info(f"   Nansen: {entry_decision.get('nansen_signal')}  "
             f"Momentum: {entry_decision.get('coingecko_momentum')}")
    log.info(f"   Reasoning: {entry_decision.get('reasoning')}")
    log.info(f"{'═'*60}")

    # ── Live order submission ──────────────────────────────────────────────────
    if LIVE_TRADING:
        if side in ("YES", "BOTH"):
            execute_live_order(market_id, True,  True, BET_USD)
        if side in ("NO",  "BOTH"):
            execute_live_order(market_id, False, True, BET_USD)
    else:
        log.info("📄 PAPER MODE — no real Solana transaction")

    # ── Open trade record ─────────────────────────────────────────────────────
    trade = open_trade_record(entry_decision, entry_snap)

    # ── Poll loop ─────────────────────────────────────────────────────────────
    poll_count    = 0
    exit_reason   = ""
    final_pnl     = 0.0
    exit_details  = {}
    yes_exited    = False   # strangle tracking
    no_exited     = False

    while True:
        poll_count += 1
        time.sleep(POLL_INTERVAL)

        # Refresh live prices
        try:
            live = get_live_pricing(market_id)
        except Exception as e:
            log.warning(f"  ⚠ Poll #{poll_count} [{token}] price refresh: {e}")
            continue

        mins_left  = live.get("mins_left")
        pnl_result = compute_pnl(trade, live)
        combined   = pnl_result.get("combined_pnl", 0)

        log.info(
            f"── Poll #{poll_count} [{token}] ───  "
            f"YES_sell={live['yes_sell']:.3f}  NO_sell={live['no_sell']:.3f}  "
            f"P&L=${combined:+.4f}  close_in={mins_left}m"
        )

        # ── STRANGLE exit logic ───────────────────────────────────────────────
        if strategy == "STRANGLE" and side == "BOTH":
            if not yes_exited and live["yes_sell"] >= STRANGLE_EXIT_PRICE:
                log.info(f"  🟢 YES wins! sell={live['yes_sell']:.3f} >= {STRANGLE_EXIT_PRICE}")
                if LIVE_TRADING:
                    execute_live_order(
                        market_id, True, False,
                        contracts=trade["entry"].get("yes_contracts", 0)
                    )
                yes_exited = True
                exit_details["yes_exit_price"] = live["yes_sell"]
                exit_details["yes_pnl"]        = pnl_result.get("yes_pnl", 0)

            if not no_exited and live["no_sell"] >= STRANGLE_EXIT_PRICE:
                log.info(f"  🟢 NO wins! sell={live['no_sell']:.3f} >= {STRANGLE_EXIT_PRICE}")
                if LIVE_TRADING:
                    execute_live_order(
                        market_id, False, False,
                        contracts=trade["entry"].get("no_contracts", 0)
                    )
                no_exited = True
                exit_details["no_exit_price"] = live["no_sell"]
                exit_details["no_pnl"]        = pnl_result.get("no_pnl", 0)

            # Close when both sides settled or market expires
            if yes_exited and no_exited:
                final_pnl   = exit_details.get("yes_pnl", 0) + exit_details.get("no_pnl", 0)
                exit_reason = "Strangle: both sides exited at target"
                break

            if mins_left is not None and mins_left <= 1:
                # Market about to expire — take whatever we have
                final_pnl = (
                    exit_details.get("yes_pnl", pnl_result.get("yes_pnl", 0)) +
                    exit_details.get("no_pnl",  pnl_result.get("no_pnl",  0))
                )
                exit_reason = f"Strangle: market expired (P&L=${final_pnl:+.4f})"
                break
            continue

        # ── MOMENTUM hard stops ────────────────────────────────────────────────
        if combined >= PROFIT_TARGET_USD:
            exit_reason = f"Take-profit (P&L=${combined:+.4f})"
            final_pnl   = combined
            log.info(f"  🎯 {exit_reason}")
            break

        if combined <= -STOP_LOSS_USD:
            exit_reason = f"Stop-loss (P&L=${combined:+.4f})"
            final_pnl   = combined
            log.info(f"  🛑 {exit_reason}")
            break

        if mins_left is not None and mins_left <= 1:
            exit_reason = f"Market expiry (P&L=${combined:+.4f})"
            final_pnl   = combined
            log.info(f"  ⏰ {exit_reason}")
            break

        # ── DeepSeek exit check every 2nd poll (conserves Groq tokens) ────────
        if poll_count % 2 == 0:
            position_snap = {
                "trade_id":       trade["trade_id"],
                "token":          token,
                "strategy":       strategy,
                "side":           side,
                "minutes_to_close": mins_left,
                "entry":          trade["entry"],
                "live_prices":    live,
                "pnl_result":     pnl_result,
                "combined_pnl":   combined,
                "polls_elapsed":  poll_count,
                "elapsed_seconds": poll_count * POLL_INTERVAL,
            }
            try:
                exit_dec = deepseek_exit_decision(position_snap)
                ds().save_decision(exit_dec)
                log.info(f"  DeepSeek exit: {exit_dec['action']} — {exit_dec.get('reason')}")

                if exit_dec["action"] == "EXIT":
                    exit_reason = exit_dec.get("reason", "DeepSeek exit signal")
                    final_pnl   = combined
                    break
            except Exception as e:
                log.warning(f"  ⚠ DeepSeek exit error: {e}")

        log.info(f"  HOLD — next poll in {POLL_INTERVAL}s")

    # ── Close position (live sell) ─────────────────────────────────────────────
    if LIVE_TRADING and strategy != "STRANGLE":
        is_yes    = (side == "YES")
        contracts = (trade["entry"].get("yes_contracts") if is_yes
                     else trade["entry"].get("no_contracts")) or 0
        execute_live_order(market_id, is_yes, False, contracts=contracts)

    close_trade_record(trade, final_pnl, exit_details, exit_reason)

    log.info(f"\n  ── Trade Result ──────────────────────────────────")
    log.info(f"  [{token}] {title}")
    log.info(f"  Side: {side}  Strategy: {strategy}  Polls: {poll_count}")
    log.info(f"  P&L:  ${final_pnl:+.4f}  ({exit_reason})")
    log.info(f"  {'─'*50}")


# ─── Main Continuous Loop ─────────────────────────────────────────────────────

def print_banner() -> None:
    budget = ds().nansen_budget()
    log.info("=" * 60)
    log.info("Jupiter Live Bot  |  DeepSeek-R1 (Groq)  |  MongoDB")
    log.info(f"Mode:     {'🔴 LIVE TRADING' if LIVE_TRADING else '📄 PAPER MODE'}")
    log.info(f"Strategy: {'STRANGLE' if STRANGLE_MODE else 'MOMENTUM'}")
    log.info(f"Target:   +${PROFIT_TARGET_USD}  |  Stop: -${STOP_LOSS_USD}")
    log.info(f"Max concurrent trades: {MAX_OPEN_TRADES}  |  Poll: {POLL_INTERVAL}s")
    log.info(f"Nansen budget: {budget['credits_remaining']}/{budget['credits_limit']} credits remaining "
             f"({budget['calls_remaining']} calls left this month)")
    log.info("=" * 60)


def main() -> None:
    missing = [k for k, v in {
        "JUPITER_API_KEY": JUPITER_API_KEY,
        "GROQ_API_KEY":    GROQ_API_KEY,
    }.items() if not v]
    if missing:
        raise SystemExit(f"❌ Missing env vars: {', '.join(missing)}")

    if not ds().markets.trading_active():
        raise SystemExit("Exchange is not trading right now. Try again later.")
    log.info("Exchange is live ✓")

    print_banner()

    active_threads: list[threading.Thread] = []

    while True:
        # ── Prune dead threads ─────────────────────────────────────────────────
        active_threads = [t for t in active_threads if t.is_alive()]
        open_count     = len(active_threads)

        log.info(f"\n{'─'*60}")
        log.info(f"Active trades: {open_count} / {MAX_OPEN_TRADES}")

        # Print budget every cycle
        budget = ds().nansen_budget()
        log.info(
            f"Nansen budget: {budget['credits_used']}/{budget['credits_limit']} credits used  "
            f"({budget['calls_remaining']} calls remaining)"
        )

        if open_count >= MAX_OPEN_TRADES:
            log.info(f"⚠ Max trades reached. Waiting {POLL_INTERVAL}s…")
            time.sleep(POLL_INTERVAL)
            continue

        # ── Fetch + enrich live markets ────────────────────────────────────────
        try:
            snaps = ds().fetch_live_markets(
                max_minutes=MAX_MINUTES_TO_CLOSE,
                min_minutes=MIN_MINUTES_TO_CLOSE,
                min_volume=MIN_VOLUME_USD,
            )
        except Exception as e:
            log.warning(f"⚠ Market fetch error: {e}")
            time.sleep(POLL_INTERVAL)
            continue

        if not snaps:
            log.info("⚠ No live markets found. Waiting…")
            time.sleep(POLL_INTERVAL)
            continue

        snaps = ds().enrich_snapshots(snaps)
        log.info(f"Enriched {len(snaps)} live snapshots")

        # ── Filter out already-open markets ───────────────────────────────────
        open_ids = {t["market_id"] for t in ds().open_trades()}
        snaps = [s for s in snaps if s["market_id"] not in open_ids]

        if not snaps:
            log.info("⚠ All live markets already in active trades. Waiting…")
            time.sleep(POLL_INTERVAL)
            continue

        # ── DeepSeek entry decision ────────────────────────────────────────────
        try:
            stats   = ds().session_stats()
            entry   = deepseek_entry_decision(snaps, stats)
            ds().save_decision(entry)
        except Exception as e:
            log.warning(f"⚠ DeepSeek entry error: {e}")
            time.sleep(POLL_INTERVAL)
            continue

        if entry.get("action") != "BET":
            log.info(f"DeepSeek says SKIP: {entry.get('skip_reason')}")
            time.sleep(MAIN_LOOP_PAUSE)
            continue

        market_id  = entry.get("market_id")
        entry_snap = next((s for s in snaps if s["market_id"] == market_id), None)

        if not entry_snap:
            log.warning(f"⚠ Snapshot for {market_id} not found. Skipping.")
            time.sleep(MAIN_LOOP_PAUSE)
            continue

        # ── Spawn trade thread ─────────────────────────────────────────────────
        token = entry.get("token", "?")
        t = threading.Thread(
            target=run_trade,
            args=(entry, entry_snap),
            daemon=True,
            name=f"trade-{token}-{int(time.time())}",
        )
        t.start()
        active_threads.append(t)
        log.info(f"🚀 Trade thread launched: {t.name}")

        # Brief pause before next opportunity scan
        time.sleep(MAIN_LOOP_PAUSE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\n⛔ Interrupted by user")
        stats = ds().session_stats()
        log.info(f"\nFinal session stats: {json.dumps(stats, indent=2)}")

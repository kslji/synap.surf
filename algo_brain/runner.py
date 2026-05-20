#!/usr/bin/env python3
"""
brain/runner.py — Main execution loop for the AI Brain trading system.

This is the entry point. It orchestrates:
  1. Data fetching (Nansen, news, technicals)
  2. Watchlist generation (dynamic coin selection)
  3. AI decision making (Claude Brain)
  4. Paper trade execution
  5. Portfolio management
  6. Logging and monitoring

Usage:
  python -m brain.runner              # Full loop
  python -m brain.runner --once       # Single cycle then exit
  python -m brain.runner --dry-run    # No API calls, mock data
"""

import sys
import os
import time
import json
import logging
import argparse
from datetime import datetime, timezone
from typing import Union

# ── Make sure project root is on path ────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from algo_brain.config import (  # noqa: E402
    MAIN_LOOP_INTERVAL_SECONDS,
    POSITION_MONITOR_INTERVAL_SECONDS,
    INITIAL_CAPITAL,
    WATCHLIST_FILE,
    LOGS_DIR,
    ANTHROPIC_API_KEY,
    NANSEN_API_KEY,
    COINGECKO_API_KEY,
    BRAIN_TYPE,
    TELEGRAM_REPORT_INTERVAL_SECONDS,
    CORE_WATCHLIST,
    MAX_OPEN_POSITIONS,
    LIVE_TRADING,
    DEFAULT_LEVERAGE,
)
from algo_brain import market_data  # noqa: E402
from algo_brain import nansen_client  # noqa: E402
from algo_brain import news_sentiment  # noqa: E402
from algo_brain.paper_trader import PaperTrader  # noqa: E402
from algo_brain.hyperliquid_trader import HyperliquidTrader  # noqa: E402
from algo_brain import trade_journal  # noqa: E402
from algo_brain.telegram_bot import TelegramNotifier, start_bot_thread  # noqa: E402

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "brain.log"),
    ],
)
logger = logging.getLogger(__name__)

# Thresholds that trigger a full Nansen + Claude cycle when positions are open
AI_CALL_PROFIT_THRESHOLD_PCT = 1.85  # Call AI when any position is ≥ +1.85% up
AI_CALL_LOSS_THRESHOLD_PCT = -1.5  # Call AI when any position is ≥  1.5% down

# Track last successful AI scan timestamp to regulate scans on fast 2m loop
LAST_AI_SCAN_TIMESTAMP = 0.0

# Track last balance alert timestamp to rate-limit alerts
LAST_BALANCE_ALERT_TIMESTAMP = 0.0

# ── Win Streak Tracker ───────────────────────────────────────────────────────
# Counts consecutive trades that closed with ROE >= MIN_ROE_EXIT_PCT (5%).
# When streak >= 2, conviction threshold is raised to 0.80 so Claude only
# takes the very best setups after a hot run.
WIN_STREAK: int = 0                    # consecutive 5%+ ROE wins
HIGH_CONVICTION_MODE: bool = False     # True when WIN_STREAK >= 2
WIN_STREAK_REQUIRED: int = 2           # how many back-to-back wins trigger the mode
HIGH_CONVICTION_THRESHOLD: float = 0.80  # raised bar when in the mode
ROE_WIN_THRESHOLD_PCT: float = 5.0     # must reach this ROE to count as a "win"

# ═══════════════════════════════════════════════════════════════════════════════
# WATCHLIST GENERATION — Dynamic coin selection  funnel
# ═══════════════════════════════════════════════════════════════════════════════


def generate_watchlist(
    nansen_data: dict,
    sentiment: dict,
    all_hl_coins: set[str],
    vol_leaders: list[str],
) -> list[str]:
    """
    Funnel to dynamically select which coins to analyze:
    Now focuses on Volatility Leaders (biggest fluctuators).
    """
    candidates = set()

    # ── Layer 1: Top Volatility Leaders (The "Fluctuators") ──────────────
    candidates.update(vol_leaders)

    # ── Layer 1.5: Core Assets (Majors) ─────────────────────────────────
    candidates.update(CORE_WATCHLIST)

    # ── Layer 2: From Nansen perp screener ──────────────────────────────
    perp_data = nansen_data.get("perp_screener")
    if perp_data and isinstance(perp_data, dict):
        items = perp_data.get("data") or perp_data.get("results") or []
        for item in items:
            symbol = ""
            if isinstance(item, dict):
                symbol = item.get("symbol", item.get("coin", item.get("name", "")))
            if symbol:
                symbol = (
                    symbol.upper()
                    .replace("-PERP", "")
                    .replace("/USD", "")
                    .replace("USDT", "")
                )
                if symbol in all_hl_coins:
                    candidates.add(symbol)

    # ── Layer 3: From Nansen smart money flows ──────────────────────────
    smart_money_flows = nansen_data.get("smart_money_flows") or {}
    for coin in smart_money_flows.keys():
        if coin.upper() in all_hl_coins:
            candidates.add(coin.upper())

    # ── Filter to only Hyperliquid listed coins ──────────────────────────
    watchlist = sorted([c for c in candidates if c in all_hl_coins])
    watchlist = watchlist[:20]  # Limit total to 20 for API token efficiency

    logger.info(f"👀 Watchlist: {len(watchlist)} coins — {', '.join(watchlist)}")

    # Persist for debugging
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(
                {
                    "watchlist": watchlist,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                f,
                indent=2,
            )
    except Exception:
        pass

    return watchlist


# ═══════════════════════════════════════════════════════════════════════════════
# AI-CALL GATE — Avoid wasting Nansen + Claude API calls
# ═══════════════════════════════════════════════════════════════════════════════


def should_make_ai_calls(
    positions: list, prices: dict, last_scan_time: float
) -> tuple[bool, str]:
    """
    Decide whether expensive API calls (Nansen + Claude) are warranted.

    Rules:
      • No open positions                   → True  (need to scan for new trades)
      • Open slots available & cooldown ok  → True  (scan for new trades to fill remaining slots)
      • Any position profit ≥ +1.75%         → True  (manage / take profit on winner)
      • Any position loss   ≥  1.25%         → True  (manage / cut a loser)
      • Otherwise                           → False (conserve credits)

    Returns (should_call: bool, reason: str)
    """
    now = time.time()

    # Rule 1: No open positions
    if not positions:
        return True, "No open positions — running full scan for new trades"

    # Rule 2: Open slots available (under MAX_OPEN_POSITIONS) and cooldown has passed
    if len(positions) < MAX_OPEN_POSITIONS:
        time_since_last_scan = now - last_scan_time
        if time_since_last_scan >= MAIN_LOOP_INTERVAL_SECONDS:
            return (
                True,
                f"Open slots available ({len(positions)}/{MAX_OPEN_POSITIONS}) and 40m threshold passed "
                f"({time_since_last_scan // 60:.1f}m ≥ {MAIN_LOOP_INTERVAL_SECONDS // 60}m) — scanning for new trades",
            )

    # Rule 3: Urgent position risk management (profit/loss thresholds)
    for pos in positions:
        coin = pos["coin"]
        side = pos["side"]
        entry = pos["entry_price"]
        current = prices.get(coin, pos.get("current_price", entry))

        if side == "LONG":
            pnl_pct = (current / entry - 1) * 100
        else:  # SHORT
            pnl_pct = (1 - current / entry) * 100

        if pnl_pct >= AI_CALL_PROFIT_THRESHOLD_PCT:
            if now - last_scan_time >= 3600:  # 1 hour cooldown for urgent scans
                return (
                    True,
                    f"{coin} is at +{pnl_pct:.2f}% profit "
                    f"(≥ +{AI_CALL_PROFIT_THRESHOLD_PCT}% threshold) — triggering urgent management scan",
                )
        if pnl_pct <= AI_CALL_LOSS_THRESHOLD_PCT:
            if now - last_scan_time >= 3600:
                return (
                    True,
                    f"{coin} is at {pnl_pct:.2f}% loss "
                    f"(≥ {abs(AI_CALL_LOSS_THRESHOLD_PCT)}% loss threshold) — triggering urgent risk management",
                )

    # Otherwise, skip
    slots_status = f"{len(positions)}/{MAX_OPEN_POSITIONS} slots filled"
    time_to_next_scan = max(0.0, MAIN_LOOP_INTERVAL_SECONDS - (now - last_scan_time))
    cooldown_status = (
        f"cooldown active (next scan in {time_to_next_scan // 60:.1f}m)"
        if len(positions) < MAX_OPEN_POSITIONS
        else "slots full"
    )
    return (
        False,
        f"Stable positions ({slots_status}) & {cooldown_status} — "
        "skipping Nansen + Claude to conserve API credits",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WIN STREAK TRACKER
# ═══════════════════════════════════════════════════════════════════════════════


def _update_win_streak(pnl: float | None, roe_pct: float):
    """
    Called after every trade close. Updates the global WIN_STREAK and
    HIGH_CONVICTION_MODE based on whether the trade hit >= 5% ROE.

    - A "quality win" = closed with ROE >= ROE_WIN_THRESHOLD_PCT (5%)
    - After WIN_STREAK_REQUIRED consecutive quality wins → HIGH_CONVICTION_MODE = True
    - Any non-quality close (loss OR < 5% ROE) resets streak and exits the mode
    """
    global WIN_STREAK, HIGH_CONVICTION_MODE

    if pnl is None:
        return  # no PnL data, skip

    is_quality_win = pnl > 0 and roe_pct >= ROE_WIN_THRESHOLD_PCT

    if is_quality_win:
        WIN_STREAK += 1
        logger.info(
            f"🔥 Win streak: {WIN_STREAK} (ROE={roe_pct:.1f}%). "
            f"Required for high-conviction mode: {WIN_STREAK_REQUIRED}"
        )
        if WIN_STREAK >= WIN_STREAK_REQUIRED and not HIGH_CONVICTION_MODE:
            HIGH_CONVICTION_MODE = True
            logger.warning(
                f"🔥 HIGH CONVICTION MODE ON — {WIN_STREAK} consecutive {ROE_WIN_THRESHOLD_PCT}%+ "
                f"ROE wins. Claude will now only take trades with conviction >= "
                f"{HIGH_CONVICTION_THRESHOLD:.0%}."
            )
    else:
        if WIN_STREAK > 0:
            logger.info(
                f"📉 Streak broken (pnl={pnl:.2f}, ROE={roe_pct:.1f}%). "
                f"Resetting from {WIN_STREAK} → 0."
            )
        WIN_STREAK = 0
        if HIGH_CONVICTION_MODE:
            HIGH_CONVICTION_MODE = False
            logger.info("✅ HIGH CONVICTION MODE OFF — streak reset.")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE CYCLE
# ═══════════════════════════════════════════════════════════════════════════════


def run_cycle(
    trader: Union[PaperTrader, HyperliquidTrader],
    dry_run: bool = False,
    notifier=None,
) -> bool:
    """
    Execute one full brain cycle:
      1.  Fetch HL universe
      1.5 Quick price update → gate AI calls by P&L threshold
      2.  [gated] Fetch Nansen intelligence
      3.  [gated] Fetch news & sentiment
      4.  [gated] Generate watchlist
      5.  [gated] Fetch technicals
      6.  SL / TP / expiry checks  (always runs)
      7.  [gated] Fetch funding rates
      8.  [gated] Claude / MiroFish AI decision
      9.  [gated] Execute trades
      10. Portfolio snapshot       (always runs)

    Returns True if cycle completed successfully.
    """
    global LAST_AI_SCAN_TIMESTAMP
    cycle_start = datetime.now(timezone.utc)
    logger.info(f"\n{'═' * 70}")
    logger.info(f"  🧠 BRAIN CYCLE — {cycle_start:%Y-%m-%d %H:%M:%S} UTC")
    logger.info(f"{'═' * 70}")

    try:
        # ── Step 1: Get Hyperliquid universe & Volatility Leaders ─────────
        logger.info("\n📊 Step 1: Scanning for Volatility Leaders...")
        all_coins = market_data.get_coin_names()
        if not all_coins:
            logger.error("Failed to fetch Hyperliquid coin list")
            return False
        all_hl_set = set(all_coins)

        # This identifies the top 10 tokens with most fluctuation (up or down)
        vol_leaders = market_data.get_top_volatility_coins(limit=10)

        # ── Step 1.5: Early price update → gate expensive API calls ──────
        logger.info("\n⚡ Step 1.5: Quick price check to gate API calls...")
        prices = market_data.get_mid_prices()
        trader.update_prices(prices)  # keeps unrealized P&L fresh

        needs_ai_calls, ai_gate_reason = should_make_ai_calls(
            trader.positions, prices, LAST_AI_SCAN_TIMESTAMP
        )
        gate_icon = "✅" if needs_ai_calls else "⏭️ "
        logger.info(f"  {gate_icon} {ai_gate_reason}")

        # ── Step 2: [GATED] Fetch Nansen intelligence ─────────────────────
        # Start with volatility leaders, core assets, and open positions
        target_coins = list(
            set(
                vol_leaders + CORE_WATCHLIST + [pos["coin"] for pos in trader.positions]
            )
        )

        if needs_ai_calls:
            logger.info("\n🔍 Step 2: Fetching Nansen intelligence...")
            if dry_run:
                nansen_data = {
                    "perp_screener": None,
                    "smart_money_flows": {},
                    "token_trends": None,
                    "credits_used": 0,
                    "credits_remaining": 1000,
                }
            else:
                nansen_data = nansen_client.build_nansen_intelligence(target_coins)
        else:
            logger.info("\n🔍 Step 2: [SKIPPED] Nansen — positions within thresholds")
            nansen_data = {
                "perp_screener": None,
                "smart_money_flows": {},
                "token_trends": None,
            }

        # ── Step 3: [GATED] Fetch news & sentiment ────────────────────────
        if needs_ai_calls:
            logger.info("\n📰 Step 3: Fetching news & sentiment...")
            if dry_run:
                sentiment_data = {
                    "fear_greed": {
                        "value": 50,
                        "classification": "Neutral",
                        "trend_direction": "STABLE",
                    },
                    "trending_coins": [],
                    "trending_categories": [],
                    "coin_headlines": {},
                    "market_headlines": [],
                }
            else:
                sentiment_data = news_sentiment.build_sentiment_data(target_coins)
        else:
            logger.info(
                "\n📰 Step 3: [SKIPPED] News & sentiment — positions within thresholds"
            )
            sentiment_data = {
                "fear_greed": {
                    "value": 50,
                    "classification": "Neutral",
                    "trend_direction": "STABLE",
                },
                "trending_coins": [],
                "trending_categories": [],
                "coin_headlines": {},
                "market_headlines": [],
            }

        # ── Step 4: [GATED] Generate dynamic watchlist ────────────────────
        if needs_ai_calls:
            logger.info("\n👀 Step 4: Generating watchlist...")
            watchlist = generate_watchlist(
                nansen_data, sentiment_data, all_hl_set, vol_leaders
            )
            if not watchlist:
                watchlist = vol_leaders[:3]
                logger.warning(
                    "Empty watchlist — falling back to top volatility leaders"
                )

            last_traded = getattr(trader, "last_traded_token", "")
            if last_traded:
                original_len = len(watchlist)
                watchlist = [c for c in watchlist if c.upper() != last_traded.upper()]
                if len(watchlist) < original_len:
                    logger.info(
                        f"  🚫 Filtered out {last_traded} from watchlist (last traded token)"
                    )
        else:
            logger.info("\n👀 Step 4: [SKIPPED] Watchlist generation")
            watchlist = [pos["coin"] for pos in trader.positions] or vol_leaders[:3]

        # ── Step 5: [GATED] Fetch technicals for watchlist coins ──────────
        if needs_ai_calls:
            logger.info(
                f"\n📈 Step 5: Fetching technicals for {len(watchlist)} coins..."
            )
            technicals = {}
            for coin in watchlist:
                mtf_data = market_data.get_mtf_technicals(coin)
                if mtf_data:
                    technicals[coin] = mtf_data
                time.sleep(0.2)  # Rate limiting
            logger.info(f"  Got technicals for {len(technicals)} coins")
        else:
            logger.info("\n📈 Step 5: [SKIPPED] Technicals fetch")
            technicals = {}

        # ── Step 6: SL-proximity AI check + SL / TP / expiry (ALWAYS runs) ──
        logger.info("\n💰 Step 6: Checking SL proximity, TP hits, expiry exits...")

        # ── Step 6a: SL-Proximity AI Intervention ─────────────────────────
        # Before letting check_exits auto-close on SL, check every open
        # position that is within SL_PROXIMITY_PCT of its stop-loss price.
        # If one is close, call Claude to decide: EXIT now or SET_NEW_SL.
        SL_PROXIMITY_PCT = 0.003  # within 0.3% of SL price → call AI
        positions_snapshot = list(getattr(trader, 'positions', []))
        for pos in positions_snapshot:
            coin = pos["coin"]
            current = prices.get(coin)
            if current is None:
                continue
            sl = pos.get("stop_loss", 0)
            if sl <= 0:
                continue
            side = pos["side"]
            # Check proximity: is price within 0.3% of the SL?
            proximity = abs(current - sl) / sl
            near_sl = (
                (side == "LONG"  and current > sl and proximity <= SL_PROXIMITY_PCT) or
                (side == "SHORT" and current < sl and proximity <= SL_PROXIMITY_PCT)
            )
            if near_sl and not dry_run:
                logger.warning(
                    f"  ⚠️  {coin} is {proximity*100:.3f}% from SL (${sl:.4f}). "
                    f"Calling Claude for exit decision..."
                )
                try:
                    from algo_brain import claude_brain
                    sl_decision = claude_brain.get_sl_decision(pos, current, prices)
                    if sl_decision:
                        action = sl_decision.get("action", "EXIT")
                        reasoning = sl_decision.get("reasoning", "")
                        logger.info(f"  🧠 Claude SL decision for {coin}: {action} — {reasoning}")
                        if notifier:
                            try:
                                notifier.broadcast(
                                    f"🚨 <b>SL Alert: {coin}</b>\n"
                                    f"Price ${current:.4f} near SL ${sl:.4f}\n"
                                    f"Claude says: <b>{action}</b>\n{reasoning}"
                                )
                            except Exception:
                                pass
                        if action == "EXIT":
                            pnl = trader.close_position(coin, current, "AI_SL_DECISION_EXIT")
                            logger.info(f"  ✅ Closed {coin} on AI instruction. PnL=${pnl}")
                            _update_win_streak(pnl, pos.get("unrealized_pnl_pct", 0))
                        elif action == "SET_NEW_SL":
                            new_sl = sl_decision.get("new_stop_loss", 0)
                            if new_sl and new_sl > 0:
                                updates = [{
                                    "coin": coin,
                                    "action": "TIGHTEN_STOP",
                                    "new_stop_loss": new_sl,
                                    "reasoning": f"Claude AI SL update: {reasoning}",
                                }]
                                trader.apply_ai_updates(updates, prices)
                                logger.info(f"  🔄 {coin} SL updated to ${new_sl:.4f} by AI")
                except Exception as sl_e:
                    logger.error(f"  SL AI call failed for {coin}: {sl_e}")

        # ── Step 6b: Normal SL / TP / expiry auto-exits ───────────────────
        exit_actions = trader.check_exits(prices)
        if exit_actions:
            for action in exit_actions:
                logger.info(f"  ⚡ Auto-exit: {action['coin']} — {action['action']}")
                # Update win streak based on closed trade ROE
                closed_pos = next(
                    (p for p in positions_snapshot if p["coin"] == action["coin"]), {}
                )
                _update_win_streak(action.get("pnl"), closed_pos.get("unrealized_pnl_pct", 0))
        else:
            logger.info("  No automatic exits triggered")

        # Log current win-streak mode
        if HIGH_CONVICTION_MODE:
            logger.info(
                f"  🔥 HIGH CONVICTION MODE active (streak={WIN_STREAK}) — "
                f"only trades ≥{HIGH_CONVICTION_THRESHOLD:.0%} conviction will be taken"
            )

        # ── Step 7: [GATED] Get funding rates ────────────────────────────
        if needs_ai_calls:
            logger.info("\n📊 Step 7: Fetching funding rates...")
            funding_rates = market_data.get_all_funding_rates()
        else:
            logger.info("\n📊 Step 7: [SKIPPED] Funding rates fetch")
            funding_rates = {}

        # ── Step 8: [GATED] Get AI decision ──────────────────────────────
        if needs_ai_calls:
            LAST_AI_SCAN_TIMESTAMP = time.time()
            logger.info(f"\n🧠 Step 8: Consulting {BRAIN_TYPE} Brain...")
            portfolio = trader.get_portfolio_snapshot()

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Skipping {BRAIN_TYPE} call — no trades executed"
                )
                decision = {
                    "scan_result": {
                        "top_coins": watchlist[:3],
                        "reasoning": "Dry run mode",
                    },
                    "trades": [],
                    "position_updates": [],
                    "market_assessment": "Dry run active",
                    "skip_reason": "Dry run mode",
                }
            else:
                # Direct call to Claude Brain (MiroFish removed)
                from algo_brain import claude_brain as brain_instance

                # Refresh headlines for the final watchlist
                sentiment_data = news_sentiment.build_sentiment_data(watchlist)

                decision = brain_instance.get_ai_decision(
                    technicals,
                    sentiment_data,
                    nansen_data,
                    portfolio,
                    funding_rates,
                    watchlist,
                )

            if decision is None:
                logger.warning(
                    f"{BRAIN_TYPE} returned no decision — skipping execution"
                )
                return False

            # ── Step 9: Validate and execute decision ─────────────────────
            logger.info("\n🚀 Step 9: Executing AI decisions...")
            from algo_brain import claude_brain

            validated = claude_brain.validate_decision(decision)

            if validated.get("market_assessment"):
                logger.info(f"  📝 Market view: {validated['market_assessment']}")
            if validated.get("skip_reason"):
                logger.info(f"  ⏸️  Skip reason: {validated['skip_reason']}")

            # Execute new trades
            for trade in validated.get("trades", []):
                coin = trade["coin"]

                # Prevent consecutive trades on the same token
                last_traded = getattr(trader, "last_traded_token", "")
                if last_traded and coin.upper() == last_traded.upper():
                    logger.warning(
                        f"⚠️ Skipping trade execution on {coin} because it was the last traded token (consecutive trades on same token are disabled)."
                    )
                    continue

                action = trade["action"]
                side = "LONG" if action == "OPEN_LONG" else "SHORT"

                entry_price = prices.get(coin)
                if entry_price is None or entry_price <= 0:
                    entry_price = float(trade.get("entry_price", 0.0))

                # Force trade margin (collateral) to exactly $40.00.
                # The leverage is dynamically decided by the AI (falling back to DEFAULT_LEVERAGE).
                # This makes the total notional position size equal to margin_usd * leverage.
                margin_usd = 40.00
                leverage = int(trade.get("leverage", DEFAULT_LEVERAGE))
                size_usd = margin_usd * leverage

                # ── High Conviction Mode Gate ─────────────────────────────────
                # After 2 consecutive 5%+ ROE wins, only take trades with
                # conviction >= 0.80 (the bar is raised automatically).
                if HIGH_CONVICTION_MODE:
                    if trade["conviction"] < HIGH_CONVICTION_THRESHOLD:
                        logger.info(
                            f"  🔥 [{coin}] Skipped — HIGH CONVICTION MODE active "
                            f"(conviction={trade['conviction']:.2f} < {HIGH_CONVICTION_THRESHOLD:.2f}). "
                            f"Streak={WIN_STREAK}. Waiting for stronger setup."
                        )
                        continue

                success = trader.open_position(
                    coin=coin,
                    side=side,
                    entry_price=entry_price,
                    size_usd=size_usd,
                    leverage=leverage,
                    stop_loss=trade["stop_loss"],
                    tp1=trade["take_profit_1"],
                    tp2=trade["take_profit_2"],
                    conviction=trade["conviction"],
                    reasoning=trade["reasoning"],
                )

                if success:
                    logger.info(f"  ✅ Opened {side} {coin} @ ${entry_price:.4f}")
                    # ── Telegram signal broadcast ──────────────────────
                    if notifier:
                        try:
                            notifier.broadcast_trade(
                                {**trade, "entry_price": entry_price}
                            )
                        except Exception:
                            pass
                else:
                    logger.warning(f"  ❌ Failed to open {side} {coin}")

            # Apply position updates from AI
            if validated.get("position_updates"):
                trader.apply_ai_updates(validated["position_updates"], prices)
                # Broadcast closes to Telegram
                if notifier:
                    for upd in validated["position_updates"]:
                        if upd.get("action") == "CLOSE":
                            try:
                                notifier.broadcast_close(upd)
                            except Exception:
                                pass

            # ── Update Market Intelligence for Dashboard ────────────────
            trade_journal.update_market_intel(sentiment_data, validated)

        else:
            logger.info(
                "\n🧠 Step 8: [SKIPPED] AI decision — positions within thresholds"
            )
            logger.info("\n🚀 Step 9: [SKIPPED] Trade execution — no AI decision made")

        # ── Step 10: Portfolio snapshot (ALWAYS runs) ─────────────────────
        logger.info("\n📋 Step 10: Portfolio snapshot...")
        portfolio = trader.get_portfolio_snapshot()
        trade_journal.log_portfolio_snapshot(portfolio)
        trade_journal.update_daily_summary(portfolio)

        # ── Cycle complete ────────────────────────────────────────────────
        elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        logger.info(
            f"\n✅ Cycle complete in {elapsed:.1f}s | "
            f"Equity: ${portfolio['total_equity']:.2f} | "
            f"Positions: {portfolio['open_position_count']} | "
            f"Win rate: {portfolio['win_rate']:.0f}% | "
            f"AI calls: {'YES' if needs_ai_calls else 'SKIPPED'}"
        )

        return True

    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.error(f"Cycle failed: {e}", exc_info=True)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════════


def run_brain(once: bool = False, dry_run: bool = False):
    """Main entry point for the AI Brain trading system."""
    global LAST_BALANCE_ALERT_TIMESTAMP

    logger.info("=" * 70)
    logger.info("  🧠 AI BRAIN TRADING SYSTEM")
    logger.info(f"  Capital:       ${INITIAL_CAPITAL}")
    logger.info(
        f"  Poll interval: {MAIN_LOOP_INTERVAL_SECONDS // 60} min (idle) / "
        f"{POSITION_MONITOR_INTERVAL_SECONDS // 60} min (with positions)"
    )
    logger.info(f"  Claude model:  {os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5')}")
    mode_str = "DRY RUN" if dry_run else ("MAINNET" if LIVE_TRADING else "PAPER TRADE")
    logger.info(f"  Mode:          {mode_str}")
    logger.info(
        f"  Nansen API:    {'✅ Configured' if NANSEN_API_KEY else '❌ Not set'}"
    )
    logger.info(
        f"  CoinGecko:     {'✅ Configured' if COINGECKO_API_KEY else '⚠️  No key (rate limited)'}"
    )
    logger.info(
        f"  Claude API:    {'✅ Configured' if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'sk-ant-your-key-here' else '❌ Not set'}"
    )
    logger.info("=" * 70)

    if LIVE_TRADING:
        logger.info(
            "🟢 LIVE TRADING MODE ON — Real orders will be executed on Hyperliquid Mainnet! 🟢"
        )
        trader = HyperliquidTrader()
    else:
        logger.info("🟡 PAPER TRADING MODE ON — Simulation only. 🟡")
        trader = PaperTrader()

    notifier = TelegramNotifier()
    start_bot_thread()  # background thread for /start /status etc.

    last_report_time = 0  # 0 ensures first report happens on start

    if once:
        run_cycle(trader, dry_run=dry_run, notifier=notifier)
        return

    while True:
        try:
            # Safety Check: If live trading on mainnet and balance is 0, alert (rate-limited) but continue execution
            if LIVE_TRADING and not dry_run:
                try:
                    balance = trader.cash
                    if balance <= 0.01:
                        now_time = time.time()
                        if now_time - LAST_BALANCE_ALERT_TIMESTAMP >= 1800:
                            LAST_BALANCE_ALERT_TIMESTAMP = now_time
                            err_msg = (
                                f"⚠️ <b>Hyperliquid Balance Alert</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━\n"
                                f"❌ Your live account balance is <b>$0.00</b> (or too low: ${balance:.4f}).\n"
                                f"🤖 The bot is continuing to monitor and manage open positions, but new trades cannot be opened.\n\n"
                                f"Please deposit USDC to your Hyperliquid address:\n"
                                f"<code>{os.getenv('HL_WALLET', 'your address')}</code> to resume full trading."
                            )
                            logger.warning(
                                f"Hyperliquid balance is 0 (${balance:.4f}). Sending rate-limited Telegram alert."
                            )
                            notifier.broadcast(err_msg)
                except Exception as balance_err:
                    logger.error(f"Error checking live account balance: {balance_err}")

            run_cycle(trader, dry_run=dry_run, notifier=notifier)

            # ── Periodic Telegram Report (every 2 hours) ─────────────────
            now = time.time()
            if now - last_report_time >= TELEGRAM_REPORT_INTERVAL_SECONDS:
                portfolio = trader.get_portfolio_snapshot()
                notifier.broadcast_portfolio_report(portfolio)
                last_report_time = now
                logger.info("📢 Scheduled portfolio report sent to Telegram")

            # Adaptive sleep: fast monitoring when positions are open
            has_positions = len(trader.positions) > 0
            sleep_seconds = (
                POSITION_MONITOR_INTERVAL_SECONDS
                if has_positions
                else MAIN_LOOP_INTERVAL_SECONDS
            )
            sleep_label = (
                f"{sleep_seconds // 60} min (positions open — monitoring SL/TP)"
                if has_positions
                else f"{sleep_seconds // 60} min (no positions — full AI scan next)"
            )
            next_run = datetime.now(timezone.utc).timestamp() + sleep_seconds
            next_dt = datetime.fromtimestamp(next_run, tz=timezone.utc)
            logger.info(
                f"\n💤 Sleeping {sleep_label}. Next cycle: {next_dt:%H:%M:%S} UTC\n"
            )
            time.sleep(sleep_seconds)

        except KeyboardInterrupt:
            logger.info("\n🛑 Brain stopped by user. Saving state...")
            trader._save_state()
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            logger.info("Retrying in 60 seconds...")
            time.sleep(60)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Brain Crypto Perps Paper Trading System"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit (no continuous loop)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip external API calls (Nansen, Claude). Uses mock data.",
    )
    args = parser.parse_args()
    run_brain(once=args.once, dry_run=args.dry_run)

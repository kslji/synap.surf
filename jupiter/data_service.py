"""
jupiter/jupiter_live_bot.py
Jupiter Prediction Market — Live Trading Bot
Short-duration (5-15min) Up/Down crypto markets
"""

import os
import time
import uuid
import logging
from typing import Optional
from datetime import datetime

from data_service import DataService

# ─── Config ──────────────────────────────────────────────────────────────────

TRADE_AMOUNT_USD = 5.0  # Size per leg (YES + NO for strangle)
MAX_CONCURRENT_TRADES = 3
MAX_RISK_PER_TRADE_PCT = 1  # 4% of bankroll per trade (conservative)
MIN_CONFIDENCE = "MEDIUM"
MIN_COMPOSITE_SCORE = 0.28

POLL_INTERVAL = 45  # seconds (light)
CHECK_OPEN_TRADES_INTERVAL = 12

# Wallet simulation (replace with real Solana wallet + Jupiter Prediction execution)
DRY_RUN = True  # Set False when ready with real execution

log = logging.getLogger("jupiter_bot")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# ─── Main Bot ────────────────────────────────────────────────────────────────


class JupiterPredictionBot:
    def __init__(self):
        self.ds = DataService()
        self.trade_id_counter = 0
        self.running = True

    def get_bankroll(self) -> float:
        """Replace with real wallet balance query later"""
        return 1250.0  # Example starting bankroll

    def can_open_new_trade(self) -> bool:
        open_trades = self.ds.open_trades()
        return len(open_trades) < MAX_CONCURRENT_TRADES

    def calculate_position_size(self, confidence: str) -> float:
        bankroll = self.get_bankroll()
        base = TRADE_AMOUNT_USD
        if confidence == "HIGH":
            base *= 1.4
        size = min(base, bankroll * MAX_RISK_PER_TRADE_PCT)
        return round(size, 2)

    def execute_strangle(self, snap: dict) -> Optional[dict]:
        """Buy both YES and NO when combined cost is low (edge)"""
        pricing = snap["pricing"]
        combined_cost = pricing["combined_cost"]

        if combined_cost >= 0.98:
            return None

        size_usd = self.calculate_position_size(snap["sentiment"]["confidence"])

        trade = {
            "trade_id": f"jup_{int(time.time())}_{self.trade_id_counter}",
            "market_id": snap["market_id"],
            "token": snap["token"],
            "duration_label": snap["duration_label"],
            "minutes_to_close": snap["minutes_to_close"],
            "entry_time": datetime.utcnow().isoformat(),
            "status": "OPEN",
            "strategy": "STRANGLE_LOW_COST",
            "yes_amount_usd": size_usd,
            "no_amount_usd": size_usd,
            "combined_cost": combined_cost,
            "expected_edge": round((1.0 - combined_cost) * 100, 2),
            "sentiment_score": snap["sentiment"]["composite_score"],
            "dry_run": DRY_RUN,
        }

        if not DRY_RUN:
            # TODO: Add real Jupiter Prediction Market order placement here
            # Use snap["market_id"], buy YES + NO via Jupiter API
            log.info(f"🚀 LIVE EXECUTION for {snap['token']} {snap['market_id']}")
            pass
        else:
            log.info(
                f"🧪 DRY RUN — Would open strangle on {snap['token']} | Edge: {trade['expected_edge']}%"
            )

        self.ds.save_trade(trade)
        self.ds.save_decision(
            {
                "decision_time": datetime.utcnow().isoformat(),
                "type": "ENTRY",
                "market_id": snap["market_id"],
                "token": snap["token"],
                "reason": f"Low combined cost + {snap['sentiment']['direction']} sentiment",
                "composite_score": snap["sentiment"]["composite_score"],
            }
        )

        self.trade_id_counter += 1
        return trade

    def check_open_trades(self):
        """Monitor and close winning positions early if profitable"""
        open_trades = self.ds.open_trades()
        for trade in open_trades:
            try:
                live = self.ds.get_live_price(trade["market_id"])
                # Simple early exit logic: if one side is very strong, sell the other
                yes_price = live["yes_buy"]
                no_price = live["no_buy"]

                # Example: If YES is trading at 0.85+, we are winning on YES leg
                pnl_estimate = (
                    yes_price * trade["yes_amount_usd"]
                    + no_price * trade["no_amount_usd"]
                    - (trade["yes_amount_usd"] + trade["no_amount_usd"])
                )

                if pnl_estimate > trade["yes_amount_usd"] * 0.35:  # 35%+ profit
                    log.info(
                        f"✅ Closing profitable trade {trade['trade_id']} | Est. PnL: ${pnl_estimate:.2f}"
                    )
                    self.ds.update_trade(
                        trade["trade_id"],
                        {
                            "status": "CLOSED",
                            "closed_at": datetime.utcnow().isoformat(),
                            "pnl_usd": round(pnl_estimate, 4),
                            "exit_reason": "PROFIT_TAKE",
                        },
                    )
            except Exception as e:
                log.warning(f"Error checking trade {trade.get('trade_id')}: {e}")

    def run(self):
        log.info("🚀 Jupiter Prediction Bot Started (Short-Duration Strangle Strategy)")
        log.info(f"Dry Run: {DRY_RUN} | Max Concurrent: {MAX_CONCURRENT_TRADES}")

        last_market_fetch = 0
        last_trade_check = 0

        while self.running:
            now = time.time()

            # 1. Check open trades frequently
            if now - last_trade_check > CHECK_OPEN_TRADES_INTERVAL:
                self.check_open_trades()
                last_trade_check = now

            # 2. Fetch fresh markets
            if now - last_market_fetch > POLL_INTERVAL:
                try:
                    snaps = self.ds.fetch_live_markets(
                        max_minutes=15, min_minutes=2, min_volume=35.0
                    )

                    enriched = self.ds.enrich_snapshots(snaps)

                    for snap in enriched:
                        if not self.can_open_new_trade():
                            break

                        sent = snap.get("sentiment", {})
                        if sent.get("confidence") in (None, "LOW"):
                            continue
                        if sent.get("composite_score", 0) < MIN_COMPOSITE_SCORE:
                            continue
                        if not snap.get("strangle_viable", False):
                            continue

                        self.execute_strangle(snap)

                except Exception as e:
                    log.error(f"Market fetch error: {e}")

                last_market_fetch = now
                log.info(f"Session Stats: {self.ds.session_stats()}")

            time.sleep(8)  # Fine-grained sleep


if __name__ == "__main__":
    try:
        bot = JupiterPredictionBot()
        bot.run()
    except KeyboardInterrupt:
        log.info("👋 Bot stopped by user")
    except Exception as e:
        log.critical(f"Bot crashed: {e}", exc_info=True)

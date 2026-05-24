"""
Legacy strategy-state helpers.

Signal execution is handled by ``synap.worker`` (PM2: trade-worker), which polls
``signals_queue`` with ``status: PENDING``. Do not run this module as a second
executor — it would duplicate or conflict with the worker.

To process AI signals:
  python -m synap.worker
"""
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.database import get_sync_db
from synap.hyperliquid_trader import HyperliquidTrader


def execute_signal_for_users(strategy_id: str, coin: str, action: str, price: float = None):
    """
    Executes trades for all ACTIVE users of a given strategy.
    Handles the transition of WAITING users to ACTIVE on CLOSE.
    """
    db = get_sync_db()

    if "OPEN" in action:
        direction = "LONG" if "LONG" in action else "SHORT"
        db.strategy_state.update_one(
            {"strategy_id": strategy_id},
            {"$set": {"status": "IN_TRADE", "active_coin": coin, "active_direction": direction}},
            upsert=True,
        )

        subs = list(db.synap_surf_ai.find({"strategy_id": strategy_id, "status": "ACTIVE"}))

        for sub in subs:
            wallet_address = sub.get("wallet_address")
            if not wallet_address:
                continue

            user = db.users.find_one(
                {"wallet_address": re.compile(f"^{wallet_address}$", re.IGNORECASE)}
            )
            if not user or not user.get("private_key"):
                print(f"Skipping {wallet_address} - no private key")
                continue

            u_asset = sub.get("asset_name", "AUTO")
            if u_asset != "AUTO" and u_asset.upper() != coin.upper():
                print(f"Skipping {wallet_address} - chose {u_asset}, not {coin}")
                continue

            capital = sub.get("capital", 1000)
            leverage = sub.get("leverage", 1)
            if capital == "AUTO":
                print(f"Skipping {wallet_address} - AUTO capital requires synap.worker")
                continue

            print(
                f"Executing {action} on {coin} for user {wallet_address} "
                f"with capital {capital} and leverage {leverage}"
            )
            try:
                trader = HyperliquidTrader(
                    private_key=user["private_key"], wallet_address=wallet_address
                )

                target_pct = float(sub.get("target_pct") or 5.0)
                stop_loss_pct = float(sub.get("stop_loss_pct") or 5.0)

                if direction == "LONG":
                    sl = price * (1 - (stop_loss_pct / 100))
                    tp1 = price * (1 + (target_pct / 100))
                else:
                    sl = price * (1 + (stop_loss_pct / 100))
                    tp1 = price * (1 - (target_pct / 100))

                trader.open_position(
                    coin=coin,
                    side=direction,
                    entry_price=price or 0.0,
                    size_usd=float(capital) * int(leverage),
                    leverage=int(leverage),
                    stop_loss=sl,
                    tp1=tp1,
                    tp2=tp1,
                    conviction=0.8,
                    reasoning=f"AI Signal: {action} {coin}",
                )
            except Exception as e:
                print(f"Failed to execute for {wallet_address}: {e}")

    elif "CLOSE" in action:
        db.strategy_state.update_one(
            {"strategy_id": strategy_id},
            {"$set": {"status": "FLAT", "active_coin": None, "active_direction": None}},
            upsert=True,
        )

        subs = list(db.synap_surf_ai.find({"strategy_id": strategy_id, "status": "ACTIVE"}))
        for sub in subs:
            wallet_address = sub.get("wallet_address")
            if not wallet_address:
                continue

            user = db.users.find_one(
                {"wallet_address": re.compile(f"^{wallet_address}$", re.IGNORECASE)}
            )
            if not user or not user.get("private_key"):
                continue

            print(f"Executing CLOSE on {coin} for user {wallet_address}")
            try:
                trader = HyperliquidTrader(
                    private_key=user["private_key"], wallet_address=wallet_address
                )
                trader.close_position(coin, price or 0.0, reason=f"AI Signal: {action}")
            except Exception as e:
                print(f"Failed to close for {wallet_address}: {e}")

        db.synap_surf_ai.update_many(
            {"strategy_id": strategy_id, "status": "WAITING"},
            {"$set": {"status": "ACTIVE"}},
        )
        print(f"Upgraded waiting users to ACTIVE for strategy {strategy_id}")


if __name__ == "__main__":
    print(
        "execution_engine.py no longer runs a signal loop.\n"
        "Use:  python -m synap.worker   (or PM2 app trade-worker)"
    )
    sys.exit(1)

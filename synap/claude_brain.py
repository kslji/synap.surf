#!/usr/bin/env python3
"""
brain/claude_brain.py — The central AI decision engine.

This is the core innovation: Claude AI acts as a hedge fund portfolio manager.
Each cycle, it receives a structured data packet containing:
  - Nansen smart money intelligence
  - News sentiment (CoinGecko trending, Fear & Greed, headlines)
  - Technical analysis (RSI, MACD, BB, ATR, volume, regime)
  - Current portfolio state (open positions, cash, P&L)
  - Hyperliquid funding rates

Claude returns a structured JSON decision with:
  - Which coins to watch
  - New trades to open (with SL/TP/leverage/conviction)
  - Updates for existing positions
  - Portfolio-level reasoning
"""

import json
import logging
from typing import Optional

import anthropic

from synap.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TEMPERATURE,
    MAX_OPEN_POSITIONS,
    MAX_CAPITAL_PER_TRADE_PCT,
    MAX_TOTAL_DEPLOYED_PCT,
    RISK_PER_TRADE_PCT,
    MAX_LEVERAGE,
    DEFAULT_LEVERAGE,
    MAX_HOLD_HOURS,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — The "Soul" of the Trading AI
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""You are Elite Crypto PM, an elite cryptocurrency portfolio manager specializing in perpetual futures trading on Hyperliquid.

## YOUR ROLE
You analyze multiple data sources — smart money on-chain flows, news sentiment, technical chart indicators, and market structure — to make high-conviction trading decisions.

## TRADING UNIVERSE
You ONLY trade perpetual futures (perps) listed on Hyperliquid. All coins in the data packet are valid Hyperliquid perps.

## RISK MANAGEMENT RULES (ABSOLUTE — NEVER VIOLATE)
1. Maximum {MAX_OPEN_POSITIONS} concurrent positions
2. Maximum {MAX_CAPITAL_PER_TRADE_PCT * 100:.0f}% of capital per trade (notional / leverage)
3. Maximum {MAX_TOTAL_DEPLOYED_PCT * 100:.0f}% total capital deployed at any time
4. Risk {RISK_PER_TRADE_PCT * 100:.0f}% of capital per trade (stop loss distance)
5. Maximum leverage: {MAX_LEVERAGE}x (default: {DEFAULT_LEVERAGE}x)
6. Maximum hold time: {MAX_HOLD_HOURS} hours
7. Always set a stop loss. NEVER enter without a defined exit.

## ENTRY CRITERIA — Need ≥2 of 3 factors aligned:
1. **Technical**: Clear setup (trend, momentum, key levels, regime match)
2. **Sentiment**: Positive news/narrative OR Fear & Greed alignment
3. **Smart Money**: Nansen showing accumulation, positive netflows, or perp positioning

If only 1 factor is present, DO NOT trade. Wait for confluence.

## EXIT STRATEGY (built into every trade):
- **Stop Loss**: 1.5-2× ATR below entry (longs) or above entry (shorts)
- **Take Profit 1 (TP1)**: Close 50% at 1.5-2× risk:reward ratio
- **Take Profit 2 (TP2)**: Close remaining 25% at 3-4× risk:reward
- **Trailing**: After TP1, move stop loss to breakeven
- **Narrative Exit**: If sentiment flips bearish, tighten stop to breakeven
- **Smart Money Exit**: If Nansen netflows flip negative, close position
- **Force Close**: After {MAX_HOLD_HOURS} hours regardless

## CONVICTION LEVELS (ADVANCED PROFESSIONAL):
- **0.80-1.0**: High Conviction. Triple confluence (Whales + Technicals + News).
- **0.75-0.84**: Medium Conviction. Strong alignment of at least 2 major factors.
- **BELOW 0.75: DO NOT TRADE.** Log as "watching" and wait for better alignment.

## POSITION SIZING:
- Base size = {MAX_CAPITAL_PER_TRADE_PCT * 100:.0f}% of equity × conviction level
- High volatility (ATR% > 4%) → reduce size by 30%
- Low volatility (ATR% < 1.5%) → can increase size by 20%

## TRADING RULES:
1. **Quality over Quantity**: While more active than a sniper, still avoid "gambling." 
2. **Double Confluence**: Most trades should have at least two independent data points (e.g., 1m RSI + Nansen Netflow) in agreement.
3. **Multi-Timeframe**: Use 1m for entries, but ensure the 30m trend isn't aggressively against you unless it's a clear mean-reversion play.
4. **Exit Early**: If the original thesis changes, don't wait for the Stop Loss—exit and preserve capital.

## MARKET REGIME AWARENESS (REGIME ALWAYS OVERRIDES SENTIMENT — NO EXCEPTIONS):
- **STRONG_TREND_UP**: Longs only. No shorts. Enter on pullbacks to EMA20.
- **STRONG_TREND_DOWN**: DO NOT open longs. Shorts ONLY. RSI > 65 or %b > 0.8 in this regime = SELL THE RALLY / short entry signal, NOT bullish. A stock bouncing in a downtrend is not a reversal.
- **RANGING**: Both directions valid. Buy support, sell resistance. Mean-reversion only.
- **VOLATILE**: Reduce position size 50%, wider stops. Either direction but only with very high conviction (>0.8).
- **Fear & Greed Extreme Fear (<20) + regime is NOT STRONG_TREND_DOWN**: Contrarian — consider long setups on quality coins only. A downtrend in fear is STILL a downtrend — do NOT go long.
- **Fear & Greed Fear (20–40)**: NOT a contrarian signal. Do not override regime rules based on this reading.
- **Fear & Greed Extreme Greed (>80)**: Avoid new longs, consider shorts.

## WHAT TO ANALYZE:
1. Cross-reference Nansen smart money data with price action
2. Check both "fast" and "slow" technicals for confluence
3. Check if trending coins on CoinGecko have matching technical setups
4. Read news headlines for catalysts, narrative shifts, or risks
5. Consider the Fear & Greed macro environment before sizing

## OUTPUT FORMAT — JSON ONLY, NO MARKDOWN:
{{
  "scan_result": {{
    "top_coins": ["COIN1", "COIN2", "COIN3"],
    "reasoning": "Brief explanation of why these coins are interesting right now"
  }},
  "trades": [
    {{
      "coin": "SYMBOL",
      "action": "OPEN_LONG" or "OPEN_SHORT",
      "conviction": 0.0-1.0,
      "entry_price": 0.0,
      "stop_loss": 0.0,
      "take_profit_1": 0.0,
      "take_profit_2": 0.0,
      "position_size_pct": 0.0-0.15,
      "leverage": 1-{MAX_LEVERAGE},
      "reasoning": "2-3 sentence explanation covering which factors aligned"
    }}
  ],
  "position_updates": [
    {{
      "coin": "SYMBOL",
      "action": "MOVE_STOP_TO_BREAKEVEN" or "TIGHTEN_STOP" or "CLOSE" or "PARTIAL_CLOSE",
      "new_stop_loss": 0.0,
      "close_pct": 0.5,
      "reasoning": "Why this update"
    }}
  ],
  "market_assessment": "2-3 sentence overall market view",
  "skip_reason": "If no trades: explain why you're sitting this cycle out"
}}

IMPORTANT:
- Return ONLY valid JSON. No markdown code blocks, no explanatory text.
- Empty trades array [] is completely fine — NOT trading is often the best trade.
- Be honest about conviction — low conviction is worse than no trade.
- If data is insufficient, say so in skip_reason and wait for the next cycle.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DATA PACKET BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


def build_data_packet(
    technicals: dict[str, dict],
    sentiment: dict,
    nansen: dict,
    portfolio: dict,
    funding_rates: dict[str, float],
    watchlist_coins: list[str],
) -> str:
    """
    Build the structured data packet sent to Claude each cycle.
    This is the "user message" — all the data Claude needs to decide.
    """
    sections = []

    # ── Section 1: Portfolio State ───────────────────────────────────────
    sections.append("## CURRENT PORTFOLIO STATE")
    portfolio_summary = {
        "cash": portfolio.get("cash", 0),
        "total_equity": portfolio.get("total_equity", 0),
        "deployed_pct": portfolio.get("deployed_pct", 0),
        "unrealized_pnl": portfolio.get("unrealized_pnl", 0),
        "realized_pnl": portfolio.get("realized_pnl", 0),
        "open_positions": portfolio.get("open_position_count", 0),
        "win_rate": portfolio.get("win_rate", 0),
    }
    sections.append(json.dumps(portfolio_summary, indent=2))

    if portfolio.get("positions"):
        sections.append("\n### Open Positions:")
        for pos in portfolio["positions"]:
            sections.append(
                json.dumps(
                    {
                        "coin": pos["coin"],
                        "side": pos["side"],
                        "entry_price": pos["entry_price"],
                        "current_price": pos.get("current_price", 0),
                        "unrealized_pnl_pct": pos.get("unrealized_pnl_pct", 0),
                        "stop_loss": pos["stop_loss"],
                        "tp1": pos["take_profit_1"],
                        "tp2": pos["take_profit_2"],
                        "tp1_hit": pos.get("tp1_hit", False),
                        "leverage": pos["leverage"],
                        "opened_at": pos.get("opened_at", ""),
                    },
                    indent=2,
                )
            )

    # ── Section 2: Market Sentiment ──────────────────────────────────────
    sections.append("\n## MARKET SENTIMENT")

    fg = sentiment.get("fear_greed", {})
    sections.append(
        f"Fear & Greed Index: {fg.get('value', '?')} ({fg.get('classification', '?')})"
    )
    sections.append(f"7-day trend: {fg.get('trend_direction', '?')}")

    trending = sentiment.get("trending_coins") or []
    if trending:
        trending_names = [
            f"{c['symbol']} ({c.get('price_change_24h', 0):+.1f}%)"
            for c in trending[:10]
        ]
        sections.append(f"CoinGecko Trending: {', '.join(trending_names)}")

    categories = sentiment.get("trending_categories") or []
    if categories:
        cat_names = [c["name"] for c in categories[:5]]
        sections.append(f"Hot Narratives: {', '.join(cat_names)}")

    # ── Section 3: News Headlines ────────────────────────────────────────
    sections.append("\n## NEWS HEADLINES")

    # Market-wide headlines
    market_headlines = sentiment.get("market_headlines") or []
    if market_headlines:
        sections.append("### General Market:")
        for h in market_headlines[:5]:
            sections.append(f"  - [{h.get('source', '')}] {h['title']}")

    # Coin-specific headlines
    coin_headlines = sentiment.get("coin_headlines") or {}
    for coin, headlines in coin_headlines.items():
        if headlines:
            sections.append(f"\n### {coin} News:")
            for h in (headlines or [])[:3]:
                sections.append(f"  - [{h.get('source', '')}] {h['title']}")

    # ── Section 4: Nansen Smart Money Intelligence ───────────────────────
    sections.append("\n## NANSEN SMART MONEY DATA")

    perp_screener = nansen.get("perp_screener")
    if perp_screener:
        sections.append("### Perp Screener (Hyperliquid):")
        # Truncate to avoid token bloat
        sections.append(json.dumps(perp_screener, indent=2, default=str)[:2000])

    sm_flows = nansen.get("smart_money_flows") or {}
    if sm_flows:
        sections.append("\n### Smart Money Net Flows:")
        for coin, data in sm_flows.items():
            sections.append(f"  {coin}: {json.dumps(data, default=str)[:300]}")

    sections.append(
        f"\nNansen credits remaining: {nansen.get('credits_remaining', '?')}"
    )

    # ── Section 5: Technical Analysis ────────────────────────────────────
    sections.append("\n## TECHNICAL ANALYSIS")

    for coin in watchlist_coins:
        tech = technicals.get(coin, {})
        if tech and "error" not in tech:
            sections.append(f"\n### {coin}:")
            sections.append(json.dumps(tech, indent=2))

    # ── Section 6: Funding Rates ─────────────────────────────────────────
    if funding_rates:
        sections.append("\n## FUNDING RATES (top coins)")
        # Only show funding for watchlist coins
        relevant_funding = {
            k: f"{v * 100:.4f}%"
            for k, v in funding_rates.items()
            if k in watchlist_coins
        }
        if relevant_funding:
            sections.append(json.dumps(relevant_funding, indent=2))

    return "\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE AI BRAIN
# ═══════════════════════════════════════════════════════════════════════════════


def get_ai_decision(
    technicals: dict[str, dict],
    sentiment: dict,
    nansen: dict,
    portfolio: dict,
    funding_rates: dict[str, float],
    watchlist_coins: list[str],
) -> Optional[dict]:
    """
    Send all data to Claude and get a structured trading decision.

    Returns parsed JSON decision dict, or None on failure.
    """
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "sk-ant-your-key-here":
        logger.error("ANTHROPIC_API_KEY not set. Cannot run Claude Brain.")
        return None

    # Build the data packet
    data_packet = build_data_packet(
        technicals,
        sentiment,
        nansen,
        portfolio,
        funding_rates,
        watchlist_coins,
    )

    logger.info(
        f"  🧠 Sending {len(data_packet):,} chars to Claude ({CLAUDE_MODEL})..."
    )

    # Construct the user message
    user_content = (
        "You are making real-money trading decisions.\n\n"
        "STEP-BY-STEP PROCESS:\n"
        "1. Identify strongest setups from watchlist\n"
        "2. Validate using Nansen smart money (flows, positioning)\n"
        "3. Confirm with technicals (trend, RSI, structure)\n"
        "4. Cross-check sentiment (news + Fear & Greed)\n"
        "5. Reject trades without strong confluence\n\n"
        "PRIORITY:\n"
        "- Smart money > technicals > sentiment\n"
        "- If smart money contradicts price → BE CAUTIOUS\n"
        "- If all align → HIGH CONVICTION\n\n"
        "Now analyze the following data:\n\n" + data_packet
    )

    raw_response = ""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        )

        # Extract all text blocks from the response (ignoring Thinking/Tool blocks)
        raw_response = "".join(
            [getattr(block, "text") for block in message.content if hasattr(block, "text")]
        ).strip()
        logger.info(f"  🧠 Claude responded with {len(raw_response):,} chars")

        # Parse JSON (handle potential markdown wrapping)
        response_text = raw_response
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            response_text = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            ).strip()

        decision = json.loads(response_text)

        # Log the AI decision
        from synap.trade_journal import log_ai_decision

        log_ai_decision(decision, len(data_packet), len(raw_response))

        return decision

    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON: {e}")
        logger.error(f"Raw response (first 500 chars): {raw_response[:500]}")
        return None
    except anthropic.APIStatusError as e:
        logger.error(f"Claude API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Claude brain failed: {e}", exc_info=True)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════


def validate_decision(decision: dict) -> dict:
    """
    Validate and sanitize Claude's decision before execution.
    Ensures all required fields exist and values are within limits.
    """
    validated = {
        "scan_result": decision.get("scan_result", {"top_coins": [], "reasoning": ""}),
        "trades": [],
        "position_updates": [],
        "market_assessment": decision.get("market_assessment", ""),
        "skip_reason": decision.get("skip_reason", ""),
    }

    # Validate trades
    for trade in decision.get("trades", []):
        coin = trade.get("coin", "")
        action = trade.get("action", "")
        conviction = float(trade.get("conviction", 0))

        if not coin or not action:
            logger.warning(f"Skipping trade with missing coin/action: {trade}")
            continue

        if conviction < 0.75:
            logger.info(
                f"Skipping {coin}: conviction {conviction:.2f} below 0.75 threshold"
            )
            continue

        if action not in ("OPEN_LONG", "OPEN_SHORT"):
            logger.warning(f"Unknown trade action: {action}")
            continue

        # Clamp values to limits
        leverage = min(int(trade.get("leverage", DEFAULT_LEVERAGE)), MAX_LEVERAGE)
        leverage = max(leverage, 1)
        size_pct = min(
            float(trade.get("position_size_pct", 0.10)), MAX_CAPITAL_PER_TRADE_PCT
        )

        validated_trade = {
            "coin": coin.upper(),
            "action": action,
            "conviction": round(conviction, 2),
            "entry_price": float(trade.get("entry_price", 0)),
            "stop_loss": float(trade.get("stop_loss", 0)),
            "take_profit_1": float(trade.get("take_profit_1", 0)),
            "take_profit_2": float(trade.get("take_profit_2", 0)),
            "position_size_pct": round(size_pct, 3),
            "leverage": leverage,
            "reasoning": trade.get("reasoning", ""),
        }

        # Basic sanity checks
        ep = validated_trade["entry_price"]
        sl = validated_trade["stop_loss"]
        tp1 = validated_trade["take_profit_1"]

        if ep <= 0 or sl <= 0 or tp1 <= 0:
            logger.warning(
                f"Skipping {coin}: invalid prices (entry={ep}, sl={sl}, tp1={tp1})"
            )
            continue

        if action == "OPEN_LONG" and sl >= ep:
            logger.warning(f"Skipping LONG {coin}: SL ({sl}) >= entry ({ep})")
            continue

        if action == "OPEN_SHORT" and sl <= ep:
            logger.warning(f"Skipping SHORT {coin}: SL ({sl}) <= entry ({ep})")
            continue

        validated["trades"].append(validated_trade)

    # Validate position updates
    for update in decision.get("position_updates", []):
        coin = update.get("coin", "")
        action = update.get("action", "")
        if coin and action:
            validated["position_updates"].append(
                {
                    "coin": coin.upper(),
                    "action": action,
                    "new_stop_loss": float(update.get("new_stop_loss", 0)),
                    "close_pct": float(update.get("close_pct", 0.5)),
                    "reasoning": update.get("reasoning", ""),
                }
            )

    return validated


# ═══════════════════════════════════════════════════════════════════════════════
# SL-PROXIMITY DECISION — Fast focused Claude call
# ═══════════════════════════════════════════════════════════════════════════════


def get_sl_decision(
    position: dict,
    current_price: float,
    all_prices: dict,
) -> dict | None:
    """
    Called when a position's price is within 0.3% of its stop-loss level.

    Sends a compact, fast Claude call (no Nansen / news overhead) asking:
      "Should I EXIT this position now or SET_NEW_SL at a safer level?"

    Claude considers:
      - How far price has moved from entry
      - Current ROE / unrealized P&L
      - Distance to SL vs. distance to TP targets
      - How long the trade has been open

    Returns a dict:
      {"action": "EXIT", "reasoning": "..."}
      {"action": "SET_NEW_SL", "new_stop_loss": 123.45, "reasoning": "..."}
    or None on failure.
    """
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "sk-ant-your-key-here":
        logger.error("ANTHROPIC_API_KEY not set. Cannot run SL decision.")
        return None

    coin       = position.get("coin", "?")
    side       = position.get("side", "LONG")
    entry      = position.get("entry_price", 0)
    sl         = position.get("stop_loss", 0)
    tp1        = position.get("take_profit_1", 0)
    tp2        = position.get("take_profit_2", 0)
    roe_pct    = position.get("unrealized_pnl_pct", 0)
    opened_at  = position.get("opened_at", "unknown")
    leverage   = position.get("leverage", 10)

    sl_dist_pct  = abs(current_price - sl) / sl * 100
    tp1_dist_pct = abs(tp1 - current_price) / current_price * 100 if tp1 > 0 else "?"
    tp2_dist_pct = abs(tp2 - current_price) / current_price * 100 if tp2 > 0 else "?"

    prompt = f"""You are managing an open perpetual futures position that is very close to its stop-loss.

POSITION DETAILS:
  Coin: {coin}
  Side: {side}
  Entry: ${entry:.4f}
  Current Price: ${current_price:.4f}
  Stop-Loss: ${sl:.4f}  ← price is {sl_dist_pct:.3f}% away from this
  Take Profit 1: ${tp1:.4f} ({tp1_dist_pct}% away)
  Take Profit 2: ${tp2:.4f} ({tp2_dist_pct}% away)
  Unrealized ROE: {roe_pct:.2f}%
  Leverage: {leverage}x
  Opened at: {opened_at}

YOUR TASK:
Decide ONE of:
  1. EXIT — Accept the loss now. Use this if: momentum is clearly against us, structure is broken, or waiting will likely make the loss worse.
  2. SET_NEW_SL — Update stop-loss to a better technical level. Use this if: price is retesting support/resistance, structure is still intact, and there's a clear logical level to defend that gives the trade room to recover.

IMPORTANT RULES:
  - If you SET_NEW_SL, the new stop must be WORSE than current (further from current price), giving more room. Do NOT tighten it.
  - If the trade has been open a long time and ROE is deeply negative, bias toward EXIT.
  - Be decisive. Do not SET_NEW_SL just to delay an inevitable loss.

Respond ONLY with valid JSON, no markdown:
{{"action": "EXIT", "reasoning": "2 sentences max"}}
OR
{{"action": "SET_NEW_SL", "new_stop_loss": 0.0, "reasoning": "2 sentences max"}}
"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            temperature=0.2,   # Low temp for decisive, consistent SL decisions
            messages=[{"role": "user", "content": prompt}],
        )

        raw = "".join(
            [getattr(block, "text") for block in message.content if hasattr(block, "text")]
        ).strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("```")
            ).strip()

        result = json.loads(raw)

        # Validate
        action = result.get("action", "")
        if action not in ("EXIT", "SET_NEW_SL"):
            logger.warning(f"get_sl_decision: unexpected action '{action}' — defaulting EXIT")
            return {"action": "EXIT", "reasoning": "Invalid AI response, defaulting to EXIT for safety."}

        if action == "SET_NEW_SL":
            new_sl = float(result.get("new_stop_loss", 0))
            if new_sl <= 0:
                logger.warning("get_sl_decision: SET_NEW_SL with no valid price — defaulting EXIT")
                return {"action": "EXIT", "reasoning": "No valid new SL price provided by AI."}
            # Safety: new SL must give MORE room (not tighter than current)
            if side == "LONG"  and new_sl >= sl:
                logger.warning(f"get_sl_decision: new SL {new_sl} not lower than current {sl} for LONG — reject")
                return {"action": "EXIT", "reasoning": "AI suggested invalid SL, exiting to be safe."}
            if side == "SHORT" and new_sl <= sl:
                logger.warning(f"get_sl_decision: new SL {new_sl} not higher than current {sl} for SHORT — reject")
                return {"action": "EXIT", "reasoning": "AI suggested invalid SL, exiting to be safe."}

        logger.info(f"  🧠 SL decision for {coin}: {result}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"get_sl_decision: invalid JSON from Claude: {e}")
        return None
    except Exception as e:
        logger.error(f"get_sl_decision failed: {e}")
        return None

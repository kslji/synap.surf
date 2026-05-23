#!/usr/bin/env python3
"""
brain/news_sentiment.py — Multi-source free news & sentiment aggregator.

Sources (all free, no paid APIs):
  1. CoinGecko Trending — top trending coins + categories (free demo key)
  2. Alternative.me Fear & Greed Index — macro sentiment (no key needed)
  3. RSS Feed Scraping — headlines from CoinDesk, CoinTelegraph, etc.
     Claude analyzes these for coin-specific sentiment.

Combined output: sentiment score -1.0 (extreme bearish) to +1.0 (extreme bullish)
"""

import re
import time
import logging
import xml.etree.ElementTree as ET
from typing import Optional, Any
from html import unescape

import requests

from synap.config import (
    COINGECKO_API_KEY,
    COINGECKO_BASE_URL,
    FEAR_GREED_URL,
    RSS_FEEDS,
    NEWS_CACHE_TTL_SECONDS,
    COINGECKO_CACHE_TTL_SECONDS,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE CACHE
# ═══════════════════════════════════════════════════════════════════════════════


class _SentimentCache:
    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str, ttl: int) -> Optional[Any]:
        if key in self._store:
            ts, val = self._store[key]
            if time.time() - ts < ttl:
                return val
            del self._store[key]
        return None

    def set(self, key: str, value: Any):
        self._store[key] = (time.time(), value)


_cache = _SentimentCache()


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 1: COINGECKO TRENDING (free demo key, 30 calls/min)
# ═══════════════════════════════════════════════════════════════════════════════


def _cg_headers() -> dict:
    headers = {"accept": "application/json"}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY
    return headers


def get_trending_coins() -> list[dict]:
    """
    Get top 15 trending coins on CoinGecko by search volume.
    Updates every 10 minutes.

    Returns: [{"name": "Bitcoin", "symbol": "BTC", "market_cap_rank": 1, ...}, ...]
    """
    cached = _cache.get("cg_trending", COINGECKO_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            f"{COINGECKO_BASE_URL}/search/trending",
            headers=_cg_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        coins = []
        for item in (data.get("coins") or []):
            c = item.get("item") or {}
            coins.append(
                {
                    "name": c.get("name", ""),
                    "symbol": c.get("symbol", "").upper(),
                    "market_cap_rank": c.get("market_cap_rank"),
                    "price_change_24h": c.get("data", {})
                    .get("price_change_percentage_24h", {})
                    .get("usd", 0),
                    "sparkline": c.get("data", {}).get("sparkline", ""),
                }
            )

        logger.info(f"🔥 CoinGecko trending: {[c['symbol'] for c in coins[:10]]}")
        _cache.set("cg_trending", coins)
        return coins

    except Exception as e:
        logger.error(f"CoinGecko trending fetch failed: {e}")
        return []


def get_trending_categories() -> list[dict]:
    """
    Get trending categories (narratives) from CoinGecko.
    Useful for identifying hot narratives: DeFi, AI, RWA, Memes, etc.
    """
    cached = _cache.get("cg_categories", COINGECKO_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            f"{COINGECKO_BASE_URL}/search/trending",
            headers=_cg_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        categories = []
        for cat in (data.get("categories") or []):
            categories.append(
                {
                    "name": cat.get("name", ""),
                    "market_cap_change_24h": cat.get("data", {})
                    .get("market_cap_change_percentage_24h", {})
                    .get("usd", 0),
                    "coins_count": cat.get("data", {}).get("coins_count", 0),
                }
            )

        if categories:
            logger.info(
                f"📂 Trending narratives: {[c['name'] for c in categories[:5]]}"
            )
        _cache.set("cg_categories", categories)
        return categories

    except Exception as e:
        logger.error(f"CoinGecko categories fetch failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 2: FEAR & GREED INDEX (free, no key)
# ═══════════════════════════════════════════════════════════════════════════════


def get_fear_greed() -> dict:
    """
    Get current Fear & Greed Index from Alternative.me.
    Returns: {"value": 45, "classification": "Fear", "timestamp": "..."}

    Scale:
      0-24:  Extreme Fear (potential buy zone)
      25-49: Fear
      50-54: Neutral
      55-74: Greed
      75-100: Extreme Greed (potential sell zone)
    """
    cached = _cache.get("fear_greed", NEWS_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    try:
        resp = requests.get(f"{FEAR_GREED_URL}?limit=7", timeout=10)
        resp.raise_for_status()
        data = resp.json()

        entries = data.get("data") or []
        if not entries:
            return {"value": 50, "classification": "Neutral", "error": "no data"}

        current = entries[0]
        result = {
            "value": int(current.get("value", 50)),
            "classification": current.get("value_classification", "Neutral"),
            "timestamp": current.get("timestamp", ""),
            # Include 7-day trend for Claude
            "history_7d": [
                {
                    "value": int(e.get("value", 50)),
                    "classification": e.get("value_classification", ""),
                }
                for e in entries
            ],
        }

        # Compute trend direction
        if len(entries) >= 3:
            recent_avg = sum(int(e["value"]) for e in entries[:3]) / 3
            older_avg = sum(int(e["value"]) for e in entries[3:]) / max(
                len(entries[3:]), 1
            )
            result["trend_direction"] = (
                "IMPROVING"
                if recent_avg > older_avg
                else ("DECLINING" if recent_avg < older_avg else "STABLE")
            )
        else:
            result["trend_direction"] = "STABLE"

        logger.info(
            f"😱 Fear & Greed: {result['value']} ({result['classification']}) "
            f"trend={result['trend_direction']}"
        )

        _cache.set("fear_greed", result)
        return result

    except Exception as e:
        logger.error(f"Fear & Greed fetch failed: {e}")
        return {"value": 50, "classification": "Neutral", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 3: RSS NEWS FEED SCRAPING (free, no key)
# ═══════════════════════════════════════════════════════════════════════════════


def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]  # Limit length


def _parse_rss_feed(url: str) -> list[dict]:
    """Parse an RSS feed and return list of articles."""
    articles = []
    try:
        resp = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.content)

        # Handle both RSS 2.0 and Atom formats
        items = root.findall(".//item")  # RSS 2.0
        if not items:
            # Try Atom format
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//atom:entry", ns)

        for item in items[:30]:  # Limit to 30 most recent per feed
            title = ""
            description = ""
            pub_date = ""
            link = ""

            # RSS 2.0 format
            title_el = item.find("title")
            desc_el = item.find("description")
            date_el = item.find("pubDate")
            link_el = item.find("link")

            if title_el is not None and title_el.text:
                title = _clean_html(title_el.text)
            if desc_el is not None and desc_el.text:
                description = _clean_html(desc_el.text)
            if date_el is not None and date_el.text:
                pub_date = date_el.text.strip()
            if link_el is not None:
                link = link_el.text.strip() if link_el.text else ""

            if title:
                articles.append(
                    {
                        "title": title,
                        "description": description,
                        "published": pub_date,
                        "source": url.split("/")[2],  # Extract domain
                        "link": link,
                    }
                )

    except Exception as e:
        logger.warning(f"RSS feed {url} failed: {e}")

    return articles


def get_all_headlines() -> list[dict]:
    """
    Fetch headlines from all configured RSS feeds.
    Returns list of recent articles (last ~50 headlines).
    """
    cached = _cache.get("rss_headlines", NEWS_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    all_articles = []
    seen_titles = set()
    for feed_url in RSS_FEEDS:
        articles = _parse_rss_feed(feed_url)
        for art in articles:
            title_clean = art["title"].lower().strip()
            if title_clean and title_clean not in seen_titles:
                seen_titles.add(title_clean)
                all_articles.append(art)
        time.sleep(0.5)  # Be polite to RSS servers

    logger.info(
        f"📰 Fetched {len(all_articles)} unique headlines from {len(RSS_FEEDS)} RSS feeds"
    )
    _cache.set("rss_headlines", all_articles)
    return all_articles


def get_coin_headlines(coin: str) -> list[dict]:
    """
    Filter headlines that mention a specific coin.
    Searches title and description for coin name/symbol.
    """
    all_headlines = get_all_headlines()

    # Build search patterns (case-insensitive)
    coin_upper = coin.upper()
    # Map common symbols to full names for better matching
    name_map = {
        "BTC": ["bitcoin", "btc"],
        "ETH": ["ethereum", "eth", "vitalik"],
        "SOL": ["solana", "sol"],
        "AVAX": ["avalanche", "avax"],
        "DOGE": ["dogecoin", "doge"],
        "XRP": ["ripple", "xrp"],
        "ADA": ["cardano", "ada"],
        "DOT": ["polkadot", "dot"],
        "MATIC": ["polygon", "matic"],
        "LINK": ["chainlink", "link"],
        "UNI": ["uniswap", "uni"],
        "AAVE": ["aave"],
        "SUI": ["sui network", "sui token", "sui"],
        "ARB": ["arbitrum", "arb"],
        "OP": ["optimism", "op"],
        "HYPE": ["hyperliquid", "hype token", "hype"],
        "BNB": ["binance", "bnb"],
        "NEAR": ["near protocol", "near"],
        "APT": ["aptos", "apt"],
        "SEI": ["sei network", "sei"],
        "TIA": ["celestia", "tia"],
        "JUP": ["jupiter", "jup"],
        "WIF": ["dogwifhat", "wif"],
        "PEPE": ["pepe"],
        "BONK": ["bonk"],
        "ZEC": ["zcash", "zec", "privacy coin"],
    }

    search_terms = name_map.get(coin_upper, [coin_upper, coin.lower()])

    matched = []
    for article in all_headlines:
        text = f"{article['title']} {article['description']}".lower()
        # Look for word boundaries to avoid partial matches (e.g., 'Sui' matching 'Suited')
        for term in search_terms:
            pattern = rf"\b{re.escape(term.lower())}\b"
            if re.search(pattern, text):
                matched.append(article)
                break

    return matched[:10]  # Return top 10 mentions


# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED SENTIMENT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


def build_sentiment_data(coins: list[str]) -> dict:
    """
    Build comprehensive sentiment data from all free sources.
    This is the main entry point called by the brain each cycle.

    Returns structured data ready for Claude to analyze:
    {
        "fear_greed": {"value": 45, "classification": "Fear", ...},
        "trending_coins": [...],
        "trending_categories": [...],
        "coin_headlines": {"SOL": [...], "ETH": [...]},
        "all_headlines": [...] (last 10 for general market context),
    }
    """
    result = {
        "fear_greed": get_fear_greed(),
        "trending_coins": get_trending_coins(),
        "trending_categories": get_trending_categories(),
        "coin_headlines": {},
        "market_headlines": [],
    }

    # Get general market headlines (last 10)
    all_headlines = get_all_headlines()
    result["market_headlines"] = all_headlines[:10]
    market_titles = {h["title"] for h in result["market_headlines"]}

    # Get coin-specific headlines
    seen_in_coins = set()
    for coin in coins[:10]:  # Cap at 10 to keep prompt size reasonable
        headlines = get_coin_headlines(coin)
        filtered = []
        for h in headlines:
            if h["title"] not in market_titles and h["title"] not in seen_in_coins:
                filtered.append(h)
                seen_in_coins.add(h["title"])
        if filtered:
            result["coin_headlines"][coin] = filtered

    logger.info(
        f"📊 Sentiment data built: F&G={result['fear_greed'].get('value', '?')}, "
        f"trending={len(result['trending_coins'])} coins, "
        f"headlines for {len(result['coin_headlines'])} coins"
    )

    return result

"""
SENTINEL CORE — Price Fetcher
Pulls live quotes for every symbol in price_data and writes back
price/change/volume/etc. Runs on a schedule (see refresh_manager.py,
or just cron/Celery-beat this directly): `python -m backend.services.price_fetcher`

Sources:
  - stocks      -> yfinance (Yahoo Finance)
  - commodities -> yfinance (futures tickers, e.g. GC=F, CL=F)
  - forex       -> yfinance (pairs, e.g. EURUSD=X)
  - crypto      -> CoinGecko (more reliable than yfinance for crypto)
"""
import asyncio
import argparse
from decimal import Decimal
from typing import Optional

import httpx
import yfinance as yf

from backend.db import get_pool

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map our internal symbol (e.g. "BTC-USD") to CoinGecko's id (e.g. "bitcoin")
# Extend this as you add curated crypto symbols.
COINGECKO_ID_MAP = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
    "XRP-USD": "ripple",
    "DOGE-USD": "dogecoin",
}


async def fetch_yfinance_symbol(symbol: str) -> Optional[dict]:
    """Stocks, commodities (futures), and forex all go through yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info  # lighter/faster than .info, fewer rate-limit issues

        price = float(getattr(info, "last_price", None) or 0)
        prev_close = float(getattr(info, "previous_close", None) or 0)
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

        return {
            "symbol": symbol,
            "price": price,
            "change_pct": round(change_pct, 4),
            "volume": int(getattr(info, "last_volume", None) or 0) or None,
            "week52_low": float(getattr(info, "year_low", None) or 0) or None,
            "week52_high": float(getattr(info, "year_high", None) or 0) or None,
        }
    except Exception as e:
        print(f"[price_fetcher] yfinance failed for {symbol}: {e}")
        return None


async def fetch_coingecko_batch(symbols: list[str]) -> dict[str, dict]:
    """Crypto goes through CoinGecko — one batched call for all crypto symbols."""
    ids = [COINGECKO_ID_MAP[s] for s in symbols if s in COINGECKO_ID_MAP]
    if not ids:
        return {}

    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": ",".join(ids),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[price_fetcher] CoinGecko request failed: {e}")
            return {}

    reverse_map = {v: k for k, v in COINGECKO_ID_MAP.items()}
    for cg_id, values in data.items():
        symbol = reverse_map.get(cg_id)
        if not symbol:
            continue
        results[symbol] = {
            "symbol": symbol,
            "price": values.get("usd", 0),
            "change_pct": round(values.get("usd_24h_change", 0) or 0, 4),
            "volume": int(values.get("usd_24h_vol", 0) or 0) or None,
            "week52_low": None,
            "week52_high": None,
        }
    return results


async def refresh_all_curated():
    """Fetches fresh prices for every symbol marked is_curated=true and writes them back."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT symbol, asset_class FROM price_data WHERE is_curated = true"
        )

    symbols_by_class: dict[str, list[str]] = {}
    for r in rows:
        symbols_by_class.setdefault(r["asset_class"], []).append(r["symbol"])

    updates = []

    # Crypto — batched
    crypto_symbols = symbols_by_class.get("crypto", [])
    if crypto_symbols:
        crypto_results = await fetch_coingecko_batch(crypto_symbols)
        updates.extend(crypto_results.values())

    # Stocks / commodities / forex — yfinance, one call per symbol
    yf_symbols = (
        symbols_by_class.get("stock", [])
        + symbols_by_class.get("commodity", [])
        + symbols_by_class.get("forex", [])
    )
    yf_results = await asyncio.gather(*[fetch_yfinance_symbol(s) for s in yf_symbols])
    updates.extend([r for r in yf_results if r])

    if not updates:
        print("[price_fetcher] No prices fetched — check network/API access")
        return 0

    pool = await get_pool()
    async with pool.acquire() as conn:
        for u in updates:
            await conn.execute(
                """
                UPDATE price_data
                SET price = $1, change_pct = $2, volume = $3,
                    week52_low = COALESCE($4, week52_low),
                    week52_high = COALESCE($5, week52_high),
                    fetched_at = now()
                WHERE symbol = $6
                """,
                Decimal(str(u["price"])), Decimal(str(u["change_pct"])), u["volume"],
                Decimal(str(u["week52_low"])) if u["week52_low"] else None,
                Decimal(str(u["week52_high"])) if u["week52_high"] else None,
                u["symbol"],
            )

    print(f"[price_fetcher] Updated {len(updates)} symbols")
    return len(updates)


async def run_loop(interval_seconds: int = 60):
    """Runs forever, refreshing on the given interval. Hand this to a
    background worker (Celery beat task, systemd service, or just nohup it)."""
    while True:
        try:
            await refresh_all_curated()
        except Exception as e:
            print(f"[price_fetcher] refresh cycle failed: {e}")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run a single fetch and exit")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between fetches in loop mode")
    args = parser.parse_args()

    if args.once:
        asyncio.run(refresh_all_curated())
    else:
        asyncio.run(run_loop(args.interval))

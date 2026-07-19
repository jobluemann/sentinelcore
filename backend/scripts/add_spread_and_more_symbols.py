"""
SENTINEL CORE — Migration: bid/ask spread columns + expanded symbol list
Adds bid_price/ask_price/spread_pct to price_data (nullable — not every
data source provides these, especially crypto via CoinGecko's free tier),
and seeds more curated symbols across forex, stocks, crypto, and commodities.
Run once against your live DB:  python -m backend.scripts.add_spread_and_more_symbols
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
ALTER TABLE price_data ADD COLUMN IF NOT EXISTS bid_price NUMERIC(18,6);
ALTER TABLE price_data ADD COLUMN IF NOT EXISTS ask_price NUMERIC(18,6);
ALTER TABLE price_data ADD COLUMN IF NOT EXISTS spread_pct NUMERIC(10,4);

INSERT INTO price_data (symbol, asset_class, name, price, change_pct, is_curated, ticker_order)
VALUES
    -- more forex majors (your explicit ask)
    ('USDZAR=X', 'forex', 'USD/ZAR', 0, 0, true, 11),
    ('USDJPY=X', 'forex', 'USD/JPY', 0, 0, true, 12),
    ('AUDUSD=X', 'forex', 'AUD/USD', 0, 0, true, 13),
    ('USDCAD=X', 'forex', 'USD/CAD', 0, 0, true, 14),
    ('NZDUSD=X', 'forex', 'NZD/USD', 0, 0, true, 15),
    ('USDCHF=X', 'forex', 'USD/CHF', 0, 0, true, 16),
    -- a few more of the others too
    ('AMZN', 'stock', 'Amazon.com Inc.', 0, 0, true, 17),
    ('GOOGL', 'stock', 'Alphabet Inc.', 0, 0, true, 18),
    ('SOL-USD', 'crypto', 'Solana', 0, 0, true, 19),
    ('XRP-USD', 'crypto', 'XRP', 0, 0, true, 20),
    ('SI=F', 'commodity', 'Silver', 0, 0, true, 21),
    ('NG=F', 'commodity', 'Natural Gas', 0, 0, true, 22)
ON CONFLICT (symbol) DO NOTHING;
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] Spread columns added, expanded symbol list seeded.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

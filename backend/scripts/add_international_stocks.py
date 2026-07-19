"""
SENTINEL CORE — Migration: international flagship stocks
Adds 2-3 well-known stocks per major exchange across 10 countries, using
the same Yahoo Finance ticker-suffix format your existing price_fetcher
already understands (e.g. .JO = Johannesburg, .L = London). No new data
source needed.

This is a curated-list expansion, not a full "every exchange, every
stock" search feature — that's a separate, larger piece of work (real
financial data licensing + rate-limit constraints on the free-tier
fetcher).

Run once against your live DB:  python -m backend.scripts.add_international_stocks
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
INSERT INTO price_data (symbol, asset_class, name, price, change_pct, is_curated, ticker_order)
VALUES
    ('NPN.JO', 'stock', 'Naspers (JSE)', 0, 0, true, 23),
    ('SOL.JO', 'stock', 'Sasol (JSE)', 0, 0, true, 24),
    ('SBK.JO', 'stock', 'Standard Bank (JSE)', 0, 0, true, 25),
    ('SHEL.L', 'stock', 'Shell (LSE)', 0, 0, true, 26),
    ('HSBA.L', 'stock', 'HSBC (LSE)', 0, 0, true, 27),
    ('7203.T', 'stock', 'Toyota (Tokyo)', 0, 0, true, 28),
    ('6758.T', 'stock', 'Sony (Tokyo)', 0, 0, true, 29),
    ('0700.HK', 'stock', 'Tencent (Hong Kong)', 0, 0, true, 30),
    ('9988.HK', 'stock', 'Alibaba (Hong Kong)', 0, 0, true, 31),
    ('BHP.AX', 'stock', 'BHP (ASX)', 0, 0, true, 32),
    ('CBA.AX', 'stock', 'Commonwealth Bank (ASX)', 0, 0, true, 33),
    ('RELIANCE.NS', 'stock', 'Reliance Industries (NSE)', 0, 0, true, 34),
    ('TCS.NS', 'stock', 'Tata Consultancy (NSE)', 0, 0, true, 35),
    ('SAP.DE', 'stock', 'SAP (Xetra)', 0, 0, true, 36),
    ('SIE.DE', 'stock', 'Siemens (Xetra)', 0, 0, true, 37),
    ('MC.PA', 'stock', 'LVMH (Paris)', 0, 0, true, 38),
    ('OR.PA', 'stock', 'L''Oreal (Paris)', 0, 0, true, 39),
    ('SHOP.TO', 'stock', 'Shopify (Toronto)', 0, 0, true, 40),
    ('RY.TO', 'stock', 'Royal Bank of Canada (Toronto)', 0, 0, true, 41),
    ('PETR4.SA', 'stock', 'Petrobras (B3)', 0, 0, true, 42),
    ('VALE3.SA', 'stock', 'Vale (B3)', 0, 0, true, 43)
ON CONFLICT (symbol) DO NOTHING;
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] International flagship stocks added (10 countries, 20 symbols).")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

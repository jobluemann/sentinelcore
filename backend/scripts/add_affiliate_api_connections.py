"""
SENTINEL CORE — Migration: affiliate_api_connections
Stores API credentials per affiliate platform (Amazon, eBay, Etsy, AliExpress,
etc.) so they're ready and waiting whenever a specific platform's auto-pull
integration gets built. This migration only adds credential STORAGE — it does
NOT include any actual product-fetching logic, since each platform's API is
genuinely different and needs its own integration built separately.
Run once against your live DB:  python -m backend.scripts.add_affiliate_api_connections
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS affiliate_api_connections (
    id              SERIAL PRIMARY KEY,
    platform        TEXT NOT NULL CHECK (platform IN ('amazon', 'ebay', 'etsy', 'aliexpress', 'custom')),
    label           TEXT NOT NULL,          -- e.g. "My Amazon Associates account"
    credentials     JSONB NOT NULL DEFAULT '{}',  -- flexible per-platform key/value (API key, secret, partner tag, etc.)
    is_active       BOOLEAN NOT NULL DEFAULT true,
    notes           TEXT,                   -- e.g. "Waiting on 3 qualifying sales before Amazon issues API access"
    last_synced_at  TIMESTAMPTZ,            -- populated once an actual sync job exists for this platform

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] affiliate_api_connections table ready.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

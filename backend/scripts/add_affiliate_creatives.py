"""
SENTINEL CORE — Migration: affiliate_creatives table
Adds the table that powers swappable banners + the top carousel.
Run once against your live DB:  python -m backend.scripts.add_affiliate_creatives

This is additive — it does NOT touch or remove the existing affiliate_links
table. affiliate_links can stay in use for simple text links; this new table
is specifically for image-based banners/carousel slides with placement,
sizing, and hover-behavior control.
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS affiliate_creatives (
    id              SERIAL PRIMARY KEY,

    -- WHERE it shows
    zone            TEXT NOT NULL CHECK (zone IN ('top_carousel', 'side_banner', 'bottom_banner')),
    size_key        TEXT NOT NULL CHECK (size_key IN ('leaderboard_728x90', 'skyscraper_160x600', 'rectangle_300x250')),

    -- WHAT it shows
    image_url       TEXT NOT NULL,
    click_url       TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    affiliate_name  TEXT NOT NULL,

    -- SCOPING (NULL asset_class = shows on every page; symbol further narrows within a class)
    asset_class     TEXT,          -- 'stock' | 'crypto' | 'commodity' | 'forex' | NULL (all)
    symbol          TEXT,          -- e.g. 'AAPL', NULL = whole asset_class

    -- BEHAVIOR
    behavior        TEXT NOT NULL DEFAULT 'static' CHECK (behavior IN ('static', 'fade_on_hover')),

    -- ORDERING / VISIBILITY
    priority        INTEGER NOT NULL DEFAULT 0,   -- higher shows first within its zone
    is_active       BOOLEAN NOT NULL DEFAULT true,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_creatives_zone_lookup
    ON affiliate_creatives(zone, asset_class, symbol)
    WHERE is_active = true;
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] affiliate_creatives table ready.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

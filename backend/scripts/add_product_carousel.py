"""
SENTINEL CORE — Migration: product_carousel + site_settings
product_carousel: the 5-8 item Amazon-style product strip (replaces the
single-image top_carousel concept with something matching Rudio's existing
WordPress Amazon Product Rotator tool).
site_settings: tiny generic key/value table — currently used for the
disclaimer text shown under the product strip.
Run once against your live DB:  python -m backend.scripts.add_product_carousel
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS product_carousel (
    id                  SERIAL PRIMARY KEY,
    title               TEXT NOT NULL,
    image_url           TEXT NOT NULL,
    price               NUMERIC(12,2) NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'USD',
    affiliate_link      TEXT NOT NULL,
    category            TEXT,
    rating              NUMERIC(2,1),              -- e.g. 4.5, shown as stars
    badge               TEXT,                       -- 'Best Seller' | 'New Arrival' | 'Trending Now' | 'Limited Stock' | NULL
    disclosed_shipping  BOOLEAN NOT NULL DEFAULT false,  -- must be true (+ is_active) to actually show
    priority            INTEGER NOT NULL DEFAULT 0,      -- higher shows first
    is_active           BOOLEAN NOT NULL DEFAULT true,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_carousel_live
    ON product_carousel(priority DESC)
    WHERE is_active = true AND disclosed_shipping = true;

CREATE TABLE IF NOT EXISTS site_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO site_settings (key, value)
VALUES ('carousel_disclaimer_text', 'Price shown may not include delivery costs or import duties. Please confirm final price and shipping before purchasing.')
ON CONFLICT (key) DO NOTHING;
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] product_carousel + site_settings tables ready.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

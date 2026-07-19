"""
SENTINEL CORE — Migration: scroll settings for ticker + product carousel
Reuses the existing site_settings key/value table (from the product carousel
disclaimer feature) to store per-row scroll config as JSON: whether it moves,
which direction, and how fast.
Run once against your live DB:  python -m backend.scripts.add_scroll_settings
"""
import asyncio
import os
import json
from dotenv import load_dotenv
import asyncpg

load_dotenv()

DEFAULT_CONFIG = json.dumps({"enabled": True, "direction": "left", "speed_seconds": 40})

SQL = """
INSERT INTO site_settings (key, value)
VALUES
    ('ticker_scroll_config', $1),
    ('product_carousel_scroll_config', $1)
ON CONFLICT (key) DO NOTHING;
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL, DEFAULT_CONFIG)
        print("[migration] Scroll settings seeded (ticker + product carousel).")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

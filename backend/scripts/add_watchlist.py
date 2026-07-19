"""
SENTINEL CORE — Migration: watchlist
Lets a user mark an asset "for monitoring" without having to hold/trade it.
Powers the new homepage's "Your watchlist" section — only watched assets
(plus anything actually held) show up there, keeping the homepage uncluttered.
Run once against your live DB:  python -m backend.scripts.add_watchlist
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS watchlist (
    id          SERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol      TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, symbol)
);
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] watchlist table ready.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

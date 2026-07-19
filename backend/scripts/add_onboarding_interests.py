"""
SENTINEL CORE — Migration: interests column for user_onboarding
Adds the 6th onboarding question — what the user is interested in
(books, food, tech, news) — as a multi-select array, same pattern as
asset_preferences.
Run once against your live DB:  python -m backend.scripts.add_onboarding_interests
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
ALTER TABLE user_onboarding ADD COLUMN IF NOT EXISTS interests TEXT[];
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] interests column added to user_onboarding.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

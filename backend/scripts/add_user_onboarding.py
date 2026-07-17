"""
SENTINEL CORE — Migration: user_onboarding table
Stores each user's onboarding answers (asked once, right after first sign-in).
Run once against your live DB:  python -m backend.scripts.add_user_onboarding
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS user_onboarding (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    email               TEXT NOT NULL,

    gender              TEXT,   -- 'male' | 'female'
    age_range           TEXT,   -- e.g. '18-24', '25-34', '35-44', '45-54', '55+'
    favorite_color      TEXT,   -- e.g. 'red', 'blue', 'green', 'purple', 'orange', 'black'
    favorite_pet        TEXT,   -- 'cat' | 'dog' | 'horse' | 'bird'
    asset_preferences   TEXT[], -- any of 'stock','crypto','commodity','forex' — multi-select

    completed_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_onboarding_email ON user_onboarding(email);
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] user_onboarding table ready.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

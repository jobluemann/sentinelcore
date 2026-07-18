"""
SENTINEL CORE — Migration: raw HTML embed support for affiliate_creatives
Some affiliate networks (e.g. XM) supply a full <a><img></a> or iframe
snippet rather than a plain image URL + click URL. This adds an alternative
'raw_html' creative type so you can paste their code directly instead of
splitting it into separate fields.
Run once against your live DB:  python -m backend.scripts.add_creative_embed_html
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
ALTER TABLE affiliate_creatives ALTER COLUMN image_url DROP NOT NULL;
ALTER TABLE affiliate_creatives ALTER COLUMN click_url DROP NOT NULL;

ALTER TABLE affiliate_creatives
    ADD COLUMN IF NOT EXISTS creative_type TEXT NOT NULL DEFAULT 'image_link'
        CHECK (creative_type IN ('image_link', 'raw_html'));

ALTER TABLE affiliate_creatives ADD COLUMN IF NOT EXISTS embed_html TEXT;
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] affiliate_creatives now supports raw HTML embed codes.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

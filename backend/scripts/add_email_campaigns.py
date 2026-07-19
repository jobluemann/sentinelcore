"""
SENTINEL CORE — Migration: email campaign system
Templates, a send queue (spread over a randomized window instead of firing
all at once), a permanent unsubscribe list, and campaign history.
Run once against your live DB:  python -m backend.scripts.add_email_campaigns
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS email_templates (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT,                 -- e.g. 'welcome', 're-engagement', 'product', 'update'
    subject     TEXT NOT NULL,
    body_html   TEXT NOT NULL,        -- may include {{FIRST_NAME}} etc. — unsubscribe footer is added automatically, not stored here
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS email_unsubscribes (
    email             TEXT PRIMARY KEY,
    unsubscribed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS email_campaigns (
    id                SERIAL PRIMARY KEY,
    name              TEXT NOT NULL,
    subject           TEXT NOT NULL,
    body_html         TEXT NOT NULL,
    segment_filters   JSONB NOT NULL DEFAULT '{}',
    total_recipients  INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'sending', 'sent', 'cancelled')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS email_queue (
    id                  SERIAL PRIMARY KEY,
    campaign_id         INTEGER NOT NULL REFERENCES email_campaigns(id) ON DELETE CASCADE,
    recipient_email     TEXT NOT NULL,
    recipient_name      TEXT,
    scheduled_at        TIMESTAMPTZ NOT NULL,   -- randomized send time within the campaign's spread window
    status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'skipped_unsubscribed')),
    unsubscribe_token   TEXT NOT NULL UNIQUE,
    sent_at             TIMESTAMPTZ,
    error               TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_queue_due
    ON email_queue(scheduled_at)
    WHERE status = 'pending';
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] Email campaign tables ready (templates, queue, unsubscribes, campaigns).")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

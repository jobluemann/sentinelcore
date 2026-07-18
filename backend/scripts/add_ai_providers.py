"""
SENTINEL CORE — Migration: ai_providers table
Stores the user-configurable list of AI providers tried in priority order
before falling back to Claude (which is hardcoded, not stored here — see
backend/services/ai_router.py).
Run once against your live DB:  python -m backend.scripts.add_ai_providers
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

SQL = """
CREATE TABLE IF NOT EXISTS ai_providers (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,               -- e.g. "My OpenAI key", "Grok backup"
    provider_type   TEXT NOT NULL CHECK (provider_type IN ('openai', 'xai_grok', 'openrouter', 'custom')),
    api_base_url    TEXT NOT NULL,                -- e.g. https://api.openai.com/v1
    api_key         TEXT NOT NULL,                -- stored plaintext, admin-key protected
    model_name      TEXT NOT NULL,                -- e.g. gpt-4o-mini, grok-2-latest, openai/gpt-4o
    priority        INTEGER NOT NULL DEFAULT 0,   -- higher = tried first
    is_active       BOOLEAN NOT NULL DEFAULT true,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_providers_priority
    ON ai_providers(priority DESC)
    WHERE is_active = true;
"""


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(SQL)
        print("[migration] ai_providers table ready.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

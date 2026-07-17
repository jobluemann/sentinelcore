"""
SENTINEL CORE — Database Schema Initialisation
Run once: python backend/scripts/init_db.py

Creates all tables in Supabase (Postgres) via the service-role connection.
Safe to re-run — every statement uses IF NOT EXISTS / ON CONFLICT.
"""
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

SCHEMA_SQL = """
-- ============================================================
-- USERS — one row per authenticated person (Firebase UID is the key)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid    TEXT UNIQUE NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    display_name    TEXT,
    auth_provider   TEXT NOT NULL DEFAULT 'email',   -- 'google' | 'github' | 'email'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

-- ============================================================
-- AUTH EVENTS — login audit trail (also drives the admin email notification)
-- ============================================================
CREATE TABLE IF NOT EXISTS auth_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,         -- 'signup' | 'login'
    ip_address  TEXT,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- DEMO ACCOUNTS — one paper-trading account per user
-- balance starts at DEMO_STARTING_BALANCE (see .env), default 10000.00
-- ============================================================
CREATE TABLE IF NOT EXISTS demo_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cash_balance    NUMERIC(14,2) NOT NULL DEFAULT 10000.00,
    starting_balance NUMERIC(14,2) NOT NULL DEFAULT 10000.00,
    round_number    INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    source          TEXT NOT NULL DEFAULT 'signup',  -- 'signup' | 'admin_grant' | 'paid'
    granted_by      TEXT,                             -- admin email, if admin_grant
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- DEMO HOLDINGS — current open positions per demo account
-- ============================================================
CREATE TABLE IF NOT EXISTS demo_holdings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demo_account_id UUID NOT NULL REFERENCES demo_accounts(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,
    asset_class     TEXT NOT NULL,        -- 'stock' | 'crypto' | 'commodity' | 'forex'
    quantity        NUMERIC(18,8) NOT NULL DEFAULT 0,
    avg_entry_price NUMERIC(14,4) NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(demo_account_id, symbol)
);

-- ============================================================
-- DEMO TRADES — full buy/sell transaction log (never deleted, even on reset)
-- ============================================================
CREATE TABLE IF NOT EXISTS demo_trades (
    id              BIGSERIAL PRIMARY KEY,
    demo_account_id UUID NOT NULL REFERENCES demo_accounts(id) ON DELETE CASCADE,
    round_number    INTEGER NOT NULL,
    symbol          TEXT NOT NULL,
    asset_class     TEXT NOT NULL,
    side            TEXT NOT NULL,        -- 'buy' | 'sell'
    quantity        NUMERIC(18,8) NOT NULL,
    price           NUMERIC(14,4) NOT NULL,
    total_value     NUMERIC(14,2) NOT NULL,
    balance_after    NUMERIC(14,2) NOT NULL,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- DEMO ROUND HISTORY — snapshot saved every time an account resets
-- ============================================================
CREATE TABLE IF NOT EXISTS demo_round_history (
    id              BIGSERIAL PRIMARY KEY,
    demo_account_id UUID NOT NULL REFERENCES demo_accounts(id) ON DELETE CASCADE,
    round_number    INTEGER NOT NULL,
    final_balance   NUMERIC(14,2) NOT NULL,
    starting_balance NUMERIC(14,2) NOT NULL,
    pnl             NUMERIC(14,2) NOT NULL,
    pnl_pct         NUMERIC(8,4) NOT NULL,
    ended_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- PRICE DATA — short-lived cache of last-fetched quotes (reduces API calls)
-- ============================================================
CREATE TABLE IF NOT EXISTS price_data (
    symbol          TEXT PRIMARY KEY,
    asset_class     TEXT NOT NULL,
    name            TEXT,
    price           NUMERIC(18,6) NOT NULL,
    change_pct      NUMERIC(8,4),
    volume          BIGINT,
    market_cap      NUMERIC(20,2),
    pe_ratio        NUMERIC(10,2),
    week52_low      NUMERIC(18,6),
    week52_high     NUMERIC(18,6),
    is_curated      BOOLEAN NOT NULL DEFAULT false,   -- shown in the top ticker
    ticker_order    INTEGER,                           -- display order in ticker, NULL = not in ticker
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- NEWS ARCHIVE — headlines pulled for sentiment / forecast context
-- ============================================================
CREATE TABLE IF NOT EXISTS news_archive (
    id          BIGSERIAL PRIMARY KEY,
    symbol      TEXT,
    headline    TEXT NOT NULL,
    source      TEXT,
    url         TEXT,
    sentiment   NUMERIC(4,3),     -- -1.0 to 1.0 from VADER/TextBlob
    published_at TIMESTAMPTZ,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- FORECASTS — AI Forecast results, cached per symbol so repeat
-- views don't re-spend an API call unnecessarily
-- ============================================================
CREATE TABLE IF NOT EXISTS forecasts (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,
    signal          TEXT NOT NULL,        -- 'BUY' | 'SELL' | 'HOLD'
    confidence      NUMERIC(5,2),
    price_target    NUMERIC(14,4),
    rationale       TEXT,
    risk_factors    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- AFFILIATE LINKS — editable lookup table, no code changes needed to update
-- ============================================================
CREATE TABLE IF NOT EXISTS affiliate_links (
    id              SERIAL PRIMARY KEY,
    asset_class     TEXT NOT NULL,         -- 'stock' | 'crypto' | 'commodity' | 'forex' | 'all'
    symbol          TEXT,                   -- NULL = applies to whole asset_class
    label           TEXT NOT NULL,          -- e.g. "Trade on Binance"
    affiliate_name  TEXT NOT NULL,          -- e.g. "Binance"
    url             TEXT NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 0,  -- higher shows first if multiple match
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_demo_trades_account ON demo_trades(demo_account_id);
CREATE INDEX IF NOT EXISTS idx_demo_holdings_account ON demo_holdings(demo_account_id);
CREATE INDEX IF NOT EXISTS idx_price_data_ticker_order ON price_data(ticker_order) WHERE is_curated = true;
CREATE INDEX IF NOT EXISTS idx_forecasts_symbol ON forecasts(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_affiliate_lookup ON affiliate_links(asset_class, symbol) WHERE is_active = true;
"""

# A starter set of curated ticker symbols so the ticker strip isn't empty
# on first run. Edit/add rows directly in price_data via SQL or admin panel.
SEED_TICKER_SQL = """
INSERT INTO price_data (symbol, asset_class, name, price, change_pct, is_curated, ticker_order)
VALUES
    ('AAPL', 'stock', 'Apple Inc.', 0, 0, true, 1),
    ('MSFT', 'stock', 'Microsoft Corp.', 0, 0, true, 2),
    ('NVDA', 'stock', 'NVIDIA Corp.', 0, 0, true, 3),
    ('TSLA', 'stock', 'Tesla Inc.', 0, 0, true, 4),
    ('BTC-USD', 'crypto', 'Bitcoin', 0, 0, true, 5),
    ('ETH-USD', 'crypto', 'Ethereum', 0, 0, true, 6),
    ('GC=F', 'commodity', 'Gold', 0, 0, true, 7),
    ('CL=F', 'commodity', 'Crude Oil', 0, 0, true, 8),
    ('EURUSD=X', 'forex', 'EUR/USD', 0, 0, true, 9),
    ('GBPUSD=X', 'forex', 'GBP/USD', 0, 0, true, 10)
ON CONFLICT (symbol) DO NOTHING;
"""


async def main():
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError(
            "Set DATABASE_URL (or SUPABASE_DB_URL) in .env — "
            "found under Supabase → Settings → Database → Connection string (URI)"
        )

    conn = await asyncpg.connect(db_url)
    try:
        print("Creating schema...")
        await conn.execute(SCHEMA_SQL)
        print("Seeding curated ticker symbols...")
        await conn.execute(SEED_TICKER_SQL)
        print("Done. Tables ready: users, auth_events, demo_accounts, demo_holdings, "
              "demo_trades, demo_round_history, price_data, news_archive, forecasts, "
              "affiliate_links")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

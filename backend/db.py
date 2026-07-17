"""
SENTINEL CORE — Database connection pool
Shared by every service/route. Uses asyncpg directly against the
Supabase Postgres connection string (simpler and faster than going
through the Supabase REST client for internal backend logic).
"""
import os
import asyncpg
from typing import Optional

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set in .env")
        _pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

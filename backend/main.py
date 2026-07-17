"""
SENTINEL CORE — FastAPI Backend v4.2
Real REST endpoints — auth, demo trading, admin grants, ticker, affiliate links.

NOTE ON FORECAST GATING: per the current product direction this is OPEN —
every logged-in user gets a free demo account automatically and AI Forecast
is available to anyone, not gated behind payment (no payment system is live).
The has_active_demo_account() check is wired in but currently passes for
everyone since accounts are auto-created on first login. Flip
REQUIRE_DEMO_ACCOUNT_FOR_FORECAST=true in .env if you want to gate it later.
"""
import os
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.db import get_pool, close_pool
from backend.services import auth as auth_service
from backend.services import demo_trading

load_dotenv()

app = FastAPI(title="Sentinel Core API", version="4.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")  # set a strong random value in .env
REQUIRE_DEMO_ACCOUNT_FOR_FORECAST = os.getenv("REQUIRE_DEMO_ACCOUNT_FOR_FORECAST", "false").lower() == "true"


# ──────────────────────────────────────────────────────────────
# Auth dependency — verifies Firebase token, returns our internal user_id
# ──────────────────────────────────────────────────────────────
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    id_token = authorization.split(" ", 1)[1]
    try:
        decoded = auth_service.verify_firebase_token(id_token)
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    result = await auth_service.upsert_user(decoded)
    return result["user"]


def require_admin_key(x_admin_key: Optional[str] = Header(None)):
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(403, "Invalid admin key")
    return True


# ──────────────────────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "operational", "version": "4.2.0"}


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


# ──────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────
@app.post("/api/auth/session")
async def create_session(user=Depends(get_current_user)):
    """Call this right after Firebase sign-in. Creates/updates the user row
    and auto-provisions a free demo account."""
    account = await demo_trading.get_or_create_demo_account(user["id"])
    return {"user": user, "demo_account": account}


# ──────────────────────────────────────────────────────────────
# DEMO TRADING
# ──────────────────────────────────────────────────────────────
class TradeRequest(BaseModel):
    symbol: str
    asset_class: str
    quantity: float
    price: float


@app.get("/api/demo/portfolio")
async def portfolio(user=Depends(get_current_user)):
    try:
        return await demo_trading.get_portfolio(user["id"])
    except demo_trading.NoDemoAccountError:
        account = await demo_trading.get_or_create_demo_account(user["id"])
        return await demo_trading.get_portfolio(user["id"])


@app.post("/api/demo/buy")
async def demo_buy(req: TradeRequest, user=Depends(get_current_user)):
    try:
        return await demo_trading.buy(
            user["id"], req.symbol, req.asset_class, Decimal(str(req.quantity)), Decimal(str(req.price))
        )
    except demo_trading.NoDemoAccountError:
        raise HTTPException(404, "No demo account — sign in again to provision one")
    except demo_trading.InsufficientFundsError as e:
        raise HTTPException(400, str(e))


@app.post("/api/demo/sell")
async def demo_sell(req: TradeRequest, user=Depends(get_current_user)):
    try:
        return await demo_trading.sell(
            user["id"], req.symbol, Decimal(str(req.quantity)), Decimal(str(req.price))
        )
    except demo_trading.NoDemoAccountError:
        raise HTTPException(404, "No demo account")
    except demo_trading.InsufficientHoldingsError as e:
        raise HTTPException(400, str(e))


# ──────────────────────────────────────────────────────────────
# ADMIN — manual credit grants (used until payment integration is live)
# Protect with X-Admin-Key header. Set ADMIN_API_KEY in .env to a long random string.
# ──────────────────────────────────────────────────────────────
class AdminGrantRequest(BaseModel):
    user_email: str
    amount: Optional[float] = None
    granted_by: str = "admin"


@app.post("/api/admin/grant-demo-account")
async def admin_grant(req: AdminGrantRequest, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        user_row = await conn.fetchrow("SELECT id FROM users WHERE email = $1", req.user_email)
        if user_row is None:
            raise HTTPException(404, f"No user found with email {req.user_email}")

    amount = Decimal(str(req.amount)) if req.amount is not None else None
    account = await demo_trading.admin_grant_or_reset(str(user_row["id"]), req.granted_by, amount)
    return {"granted": True, "account": account}


@app.get("/api/admin/demo-accounts")
async def list_demo_accounts(_=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT u.email, u.display_name, d.cash_balance, d.starting_balance,
                   d.round_number, d.source, d.is_active, d.created_at, d.updated_at
            FROM demo_accounts d
            JOIN users u ON u.id = d.user_id
            ORDER BY d.updated_at DESC
            """
        )
        return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────
# TICKER — curated symbol strip for the top of the dashboard
# ──────────────────────────────────────────────────────────────
@app.get("/api/ticker")
async def get_ticker():
    """Public endpoint — no auth required, used to render the scrolling price strip."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT symbol, asset_class, name, price, change_pct, fetched_at
            FROM price_data
            WHERE is_curated = true
            ORDER BY ticker_order ASC NULLS LAST
            """
        )
        return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────
# AFFILIATE LINKS — gated alongside AI Forecast, not replacing it
# ──────────────────────────────────────────────────────────────
@app.get("/api/affiliate-links")
async def affiliate_links(symbol: Optional[str] = None, asset_class: Optional[str] = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if symbol:
            rows = await conn.fetch(
                """
                SELECT * FROM affiliate_links
                WHERE is_active = true AND (symbol = $1 OR (symbol IS NULL AND asset_class = $2) OR asset_class = 'all')
                ORDER BY priority DESC
                """,
                symbol, asset_class,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM affiliate_links WHERE is_active = true ORDER BY priority DESC"
            )
        return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────
# FORECAST GATE — example of how to gate a feature behind demo account status
# (currently a pass-through since accounts are free & auto-created)
# ──────────────────────────────────────────────────────────────
async def require_demo_account_if_configured(user_id: str):
    if not REQUIRE_DEMO_ACCOUNT_FOR_FORECAST:
        return
    if not await demo_trading.has_active_demo_account(user_id):
        raise HTTPException(403, "Sim trading account required for AI Forecast")

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
# AI PROVIDERS — configurable failover chain (Claude is hardcoded elsewhere,
# not stored here — see backend/services/ai_router.py)
# ──────────────────────────────────────────────────────────────
from backend.services.ai_router import call_ai, _call_openai_compatible

VALID_PROVIDER_TYPES = {"openai", "xai_grok", "openrouter", "custom"}


class AIProviderInput(BaseModel):
    name: str
    provider_type: str
    api_base_url: str
    api_key: str
    model_name: str
    priority: int = 0
    is_active: bool = True

    def validate_choices(self):
        if self.provider_type not in VALID_PROVIDER_TYPES:
            raise HTTPException(422, f"provider_type must be one of {VALID_PROVIDER_TYPES}")


@app.get("/api/admin/ai-providers")
async def admin_list_ai_providers(_=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM ai_providers ORDER BY priority DESC, id ASC")
        # Mask keys in the list view — full key only needed for the edit form,
        # which the admin UI re-fetches; here we just show it's set.
        return [
            {**dict(r), "api_key": (r["api_key"][:4] + "..." if r["api_key"] else "")}
            for r in rows
        ]


@app.post("/api/admin/ai-providers")
async def admin_create_ai_provider(req: AIProviderInput, _=Depends(require_admin_key)):
    req.validate_choices()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ai_providers (name, provider_type, api_base_url, api_key, model_name, priority, is_active)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            RETURNING *
            """,
            req.name, req.provider_type, req.api_base_url, req.api_key,
            req.model_name, req.priority, req.is_active,
        )
        return dict(row)


@app.put("/api/admin/ai-providers/{provider_id}")
async def admin_update_ai_provider(provider_id: int, req: AIProviderInput, _=Depends(require_admin_key)):
    req.validate_choices()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE ai_providers
            SET name=$1, provider_type=$2, api_base_url=$3, api_key=$4,
                model_name=$5, priority=$6, is_active=$7, updated_at=now()
            WHERE id=$8
            RETURNING *
            """,
            req.name, req.provider_type, req.api_base_url, req.api_key,
            req.model_name, req.priority, req.is_active, provider_id,
        )
        if row is None:
            raise HTTPException(404, "Provider not found")
        return dict(row)


@app.delete("/api/admin/ai-providers/{provider_id}")
async def admin_delete_ai_provider(provider_id: int, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM ai_providers WHERE id=$1", provider_id)
        if result == "DELETE 0":
            raise HTTPException(404, "Provider not found")
        return {"deleted": True, "id": provider_id}


@app.post("/api/admin/ai-providers/{provider_id}/test")
async def admin_test_ai_provider(provider_id: int, _=Depends(require_admin_key)):
    """Sends a tiny test prompt directly to this one provider (bypassing
    priority/failover) so you can confirm a key actually works."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM ai_providers WHERE id=$1", provider_id)
    if row is None:
        raise HTTPException(404, "Provider not found")
    provider = dict(row)
    try:
        text = await _call_openai_compatible(provider, "Reply with exactly: OK", None)
        return {"success": True, "response": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/admin/ai-providers/test-claude-fallback")
async def admin_test_claude_fallback(_=Depends(require_admin_key)):
    """Confirms the hardcoded Claude fallback itself is working (tests your
    ANTHROPIC_API_KEY env var directly, ignoring the ai_providers table)."""
    try:
        result = await call_ai("Reply with exactly: OK")
        return {"success": True, "response": result["text"], "provider_used": result["provider_used"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# ONBOARDING — 5 quick questions asked once, right after first sign-in
# ──────────────────────────────────────────────────────────────
class OnboardingAnswers(BaseModel):
    gender: Optional[str] = None
    age_range: Optional[str] = None
    favorite_color: Optional[str] = None
    favorite_pet: Optional[str] = None
    asset_preferences: list[str] = []


@app.get("/api/onboarding/status")
async def onboarding_status(user=Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM user_onboarding WHERE user_id = $1", user["id"])
        return {"completed": row is not None}


@app.post("/api/onboarding")
async def save_onboarding(req: OnboardingAnswers, user=Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_onboarding (user_id, email, gender, age_range, favorite_color, favorite_pet, asset_preferences)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id) DO UPDATE SET
                gender = EXCLUDED.gender,
                age_range = EXCLUDED.age_range,
                favorite_color = EXCLUDED.favorite_color,
                favorite_pet = EXCLUDED.favorite_pet,
                asset_preferences = EXCLUDED.asset_preferences,
                completed_at = now()
            RETURNING *
            """,
            user["id"], user["email"], req.gender, req.age_range,
            req.favorite_color, req.favorite_pet, req.asset_preferences,
        )
        return dict(row)


@app.get("/api/admin/onboarding-responses")
async def admin_onboarding_responses(_=Depends(require_admin_key)):
    """All users' onboarding answers — for your own review/analysis."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM user_onboarding ORDER BY completed_at DESC")
        return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────
# AFFILIATE CREATIVES — swappable banners + top carousel
# Public read endpoint for the frontend, admin CRUD for managing them.
# ──────────────────────────────────────────────────────────────
VALID_ZONES = {"top_carousel", "side_banner", "bottom_banner"}
VALID_SIZES = {"leaderboard_728x90", "skyscraper_160x600", "rectangle_300x250"}
VALID_BEHAVIORS = {"static", "fade_on_hover"}


class CreativeInput(BaseModel):
    zone: str
    size_key: str
    image_url: str
    click_url: str
    product_name: str
    affiliate_name: str
    asset_class: Optional[str] = None
    symbol: Optional[str] = None
    behavior: str = "static"
    priority: int = 0
    is_active: bool = True

    def validate_choices(self):
        if self.zone not in VALID_ZONES:
            raise HTTPException(422, f"zone must be one of {VALID_ZONES}")
        if self.size_key not in VALID_SIZES:
            raise HTTPException(422, f"size_key must be one of {VALID_SIZES}")
        if self.behavior not in VALID_BEHAVIORS:
            raise HTTPException(422, f"behavior must be one of {VALID_BEHAVIORS}")


@app.get("/api/creatives")
async def get_creatives(zone: Optional[str] = None, asset_class: Optional[str] = None, symbol: Optional[str] = None):
    """Public endpoint — the frontend calls this to render carousels/banners.
    Returns active creatives matching the zone + scope, most specific first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM affiliate_creatives
            WHERE is_active = true
              AND ($1::text IS NULL OR zone = $1)
              AND (
                    symbol = $2
                 OR (asset_class = $3 AND symbol IS NULL)
                 OR (asset_class IS NULL AND symbol IS NULL)
              )
            ORDER BY priority DESC, id ASC
            """,
            zone, symbol, asset_class,
        )
        return [dict(r) for r in rows]


@app.get("/api/admin/creatives")
async def admin_list_creatives(_=Depends(require_admin_key)):
    """Returns EVERY creative (active + inactive) — used by the admin preview page."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM affiliate_creatives ORDER BY zone, priority DESC, id ASC")
        return [dict(r) for r in rows]


@app.post("/api/admin/creatives")
async def admin_create_creative(req: CreativeInput, _=Depends(require_admin_key)):
    req.validate_choices()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO affiliate_creatives
                (zone, size_key, image_url, click_url, product_name, affiliate_name,
                 asset_class, symbol, behavior, priority, is_active)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING *
            """,
            req.zone, req.size_key, req.image_url, req.click_url, req.product_name,
            req.affiliate_name, req.asset_class, req.symbol, req.behavior, req.priority, req.is_active,
        )
        return dict(row)


@app.put("/api/admin/creatives/{creative_id}")
async def admin_update_creative(creative_id: int, req: CreativeInput, _=Depends(require_admin_key)):
    req.validate_choices()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE affiliate_creatives
            SET zone=$1, size_key=$2, image_url=$3, click_url=$4, product_name=$5,
                affiliate_name=$6, asset_class=$7, symbol=$8, behavior=$9,
                priority=$10, is_active=$11, updated_at=now()
            WHERE id=$12
            RETURNING *
            """,
            req.zone, req.size_key, req.image_url, req.click_url, req.product_name,
            req.affiliate_name, req.asset_class, req.symbol, req.behavior,
            req.priority, req.is_active, creative_id,
        )
        if row is None:
            raise HTTPException(404, "Creative not found")
        return dict(row)


@app.delete("/api/admin/creatives/{creative_id}")
async def admin_delete_creative(creative_id: int, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM affiliate_creatives WHERE id=$1", creative_id)
        if result == "DELETE 0":
            raise HTTPException(404, "Creative not found")
        return {"deleted": True, "id": creative_id}


# ──────────────────────────────────────────────────────────────
# FORECAST GATE — example of how to gate a feature behind demo account status
# (currently a pass-through since accounts are free & auto-created)
# ──────────────────────────────────────────────────────────────
async def require_demo_account_if_configured(user_id: str):
    if not REQUIRE_DEMO_ACCOUNT_FOR_FORECAST:
        return
    if not await demo_trading.has_active_demo_account(user_id):
        raise HTTPException(403, "Sim trading account required for AI Forecast")

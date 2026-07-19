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

from fastapi import FastAPI, Depends, HTTPException, Header, Body
from fastapi.responses import HTMLResponse
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
# WATCHLIST — mark assets "for monitoring" without holding them.
# Powers the homepage redesign: only watched + held assets show there.
# ──────────────────────────────────────────────────────────────
class WatchlistInput(BaseModel):
    symbol: str
    asset_class: str


@app.get("/api/watchlist")
async def get_watchlist(user=Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.symbol, p.asset_class, p.name, p.price, p.change_pct, p.spread_pct
            FROM watchlist w
            JOIN price_data p ON p.symbol = w.symbol
            WHERE w.user_id = $1
            ORDER BY w.added_at DESC
            """,
            user["id"],
        )
        return [dict(r) for r in rows]


@app.post("/api/watchlist")
async def add_to_watchlist(req: WatchlistInput, user=Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO watchlist (user_id, symbol, asset_class)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, symbol) DO NOTHING
            """,
            user["id"], req.symbol, req.asset_class,
        )
        return {"added": True, "symbol": req.symbol}


@app.delete("/api/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, user=Depends(get_current_user)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM watchlist WHERE user_id = $1 AND symbol = $2", user["id"], symbol)
        return {"removed": True, "symbol": symbol}


@app.get("/api/ticker/top-performers")
async def get_top_performers():
    """Public — biggest % gainer overall, plus one per asset class, for the homepage."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (asset_class) symbol, asset_class, name, price, change_pct
            FROM price_data
            WHERE is_curated = true
            ORDER BY asset_class, change_pct DESC
            """
        )
        by_class = {r["asset_class"]: dict(r) for r in rows}
        overall = max(rows, key=lambda r: r["change_pct"], default=None)
        return {"overall": dict(overall) if overall else None, "by_class": by_class}


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
            SELECT symbol, asset_class, name, price, change_pct, fetched_at,
                   bid_price, ask_price, spread_pct
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
# EMAIL CAMPAIGNS — sent via your own domain's SMTP mailbox, queued with
# randomized timing (see backend/services/email_sender.py). This is NOT
# instant bulk sending — recipients get randomized send times spread over
# a window, processed later by backend/scripts/process_email_queue.py.
# ──────────────────────────────────────────────────────────────
from backend.services import email_sender


class TemplateInput(BaseModel):
    name: str
    category: Optional[str] = None
    subject: str
    body_html: str


class AudienceFilters(BaseModel):
    gender: Optional[str] = None
    age_range: Optional[str] = None
    favorite_color: Optional[str] = None
    favorite_pet: Optional[str] = None
    interests: list[str] = []
    asset_preferences: list[str] = []


class SendCampaignRequest(BaseModel):
    name: str
    subject: str
    body_html: str
    filters: AudienceFilters
    window_hours: int = 48


@app.get("/api/admin/email-templates")
async def admin_list_templates(_=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM email_templates ORDER BY id DESC")
        return [dict(r) for r in rows]


@app.post("/api/admin/email-templates")
async def admin_create_template(req: TemplateInput, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO email_templates (name, category, subject, body_html) VALUES ($1,$2,$3,$4) RETURNING *",
            req.name, req.category, req.subject, req.body_html,
        )
        return dict(row)


@app.put("/api/admin/email-templates/{template_id}")
async def admin_update_template(template_id: int, req: TemplateInput, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE email_templates SET name=$1, category=$2, subject=$3, body_html=$4, updated_at=now()
               WHERE id=$5 RETURNING *""",
            req.name, req.category, req.subject, req.body_html, template_id,
        )
        if row is None:
            raise HTTPException(404, "Template not found")
        return dict(row)


@app.delete("/api/admin/email-templates/{template_id}")
async def admin_delete_template(template_id: int, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM email_templates WHERE id=$1", template_id)
        if result == "DELETE 0":
            raise HTTPException(404, "Template not found")
        return {"deleted": True, "id": template_id}


@app.post("/api/admin/audience/preview")
async def admin_preview_audience(filters: AudienceFilters, _=Depends(require_admin_key)):
    recipients = await email_sender.build_audience(filters.dict())
    return {"count": len(recipients), "sample": recipients[:10]}


@app.post("/api/admin/email-campaigns/send")
async def admin_send_campaign(req: SendCampaignRequest, _=Depends(require_admin_key)):
    campaign = await email_sender.queue_campaign(
        req.name, req.subject, req.body_html, req.filters.dict(), req.window_hours
    )
    return campaign


@app.get("/api/admin/email-campaigns")
async def admin_list_campaigns(_=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        campaigns = await conn.fetch("SELECT * FROM email_campaigns ORDER BY id DESC LIMIT 50")
        result = []
        for c in campaigns:
            counts = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                    COUNT(*) FILTER (WHERE status = 'sent') AS sent,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE status = 'skipped_unsubscribed') AS skipped
                FROM email_queue WHERE campaign_id = $1
                """,
                c["id"],
            )
            result.append({**dict(c), **dict(counts)})
        return result


@app.get("/api/unsubscribe")
async def unsubscribe(token: str):
    """Public — clicked directly from an email footer link. No login required."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT recipient_email FROM email_queue WHERE unsubscribe_token = $1", token)
        if row is None:
            return HTMLResponse("<h2>Invalid or expired unsubscribe link.</h2>")
        await conn.execute(
            "INSERT INTO email_unsubscribes (email) VALUES ($1) ON CONFLICT (email) DO NOTHING",
            row["recipient_email"],
        )
        return HTMLResponse(
            f"<h2>You've been unsubscribed.</h2><p>{row['recipient_email']} will not receive further emails from Sentinel Core.</p>"
        )


# ──────────────────────────────────────────────────────────────
# AFFILIATE API CONNECTIONS — credential storage only, ready for whenever
# a specific platform's auto-pull integration gets built (each platform's
# API is different and needs its own separate integration work).
# ──────────────────────────────────────────────────────────────
import json as _json

VALID_AFFILIATE_PLATFORMS = {"amazon", "ebay", "etsy", "aliexpress", "custom"}


class AffiliateAPIConnectionInput(BaseModel):
    platform: str
    label: str
    credentials: dict = {}
    is_active: bool = True
    notes: Optional[str] = None

    def validate_choices(self):
        if self.platform not in VALID_AFFILIATE_PLATFORMS:
            raise HTTPException(422, f"platform must be one of {VALID_AFFILIATE_PLATFORMS}")


@app.get("/api/admin/affiliate-api-connections")
async def admin_list_affiliate_api_connections(_=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM affiliate_api_connections ORDER BY platform, id")
        result = []
        for r in rows:
            d = dict(r)
            # Mask credential values in the list view for safety
            creds = d.get("credentials") or {}
            if isinstance(creds, str):
                creds = _json.loads(creds)
            d["credentials"] = {k: (v[:4] + "..." if v else "") for k, v in creds.items()}
            result.append(d)
        return result


@app.post("/api/admin/affiliate-api-connections")
async def admin_create_affiliate_api_connection(req: AffiliateAPIConnectionInput, _=Depends(require_admin_key)):
    req.validate_choices()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO affiliate_api_connections (platform, label, credentials, is_active, notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            req.platform, req.label, _json.dumps(req.credentials), req.is_active, req.notes,
        )
        return dict(row)


@app.put("/api/admin/affiliate-api-connections/{conn_id}")
async def admin_update_affiliate_api_connection(conn_id: int, req: AffiliateAPIConnectionInput, _=Depends(require_admin_key)):
    req.validate_choices()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE affiliate_api_connections
            SET platform=$1, label=$2, credentials=$3, is_active=$4, notes=$5, updated_at=now()
            WHERE id=$6
            RETURNING *
            """,
            req.platform, req.label, _json.dumps(req.credentials), req.is_active, req.notes, conn_id,
        )
        if row is None:
            raise HTTPException(404, "Connection not found")
        return dict(row)


@app.delete("/api/admin/affiliate-api-connections/{conn_id}")
async def admin_delete_affiliate_api_connection(conn_id: int, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM affiliate_api_connections WHERE id=$1", conn_id)
        if result == "DELETE 0":
            raise HTTPException(404, "Connection not found")
        return {"deleted": True, "id": conn_id}


# ──────────────────────────────────────────────────────────────
# PRODUCT CAROUSEL — 5-8 item Amazon-style product strip
# (mirrors Rudio's existing WordPress Amazon Product Rotator tool)
# ──────────────────────────────────────────────────────────────
class ProductCarouselInput(BaseModel):
    title: str
    image_url: str
    price: float
    currency: str = "USD"
    affiliate_link: str
    category: Optional[str] = None
    rating: Optional[float] = None
    badge: Optional[str] = None
    disclosed_shipping: bool = False
    priority: int = 0
    is_active: bool = True


@app.get("/api/carousel-products")
async def get_carousel_products():
    """Public endpoint. A product only appears here if BOTH is_active
    and disclosed_shipping are true — same safety behavior as the WP tool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM product_carousel
            WHERE is_active = true AND disclosed_shipping = true
            ORDER BY priority DESC, id ASC
            """
        )
        return [dict(r) for r in rows]


@app.get("/api/admin/carousel-products")
async def admin_list_carousel_products(_=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM product_carousel ORDER BY priority DESC, id ASC")
        return [dict(r) for r in rows]


@app.post("/api/admin/carousel-products")
async def admin_create_carousel_product(req: ProductCarouselInput, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO product_carousel
                (title, image_url, price, currency, affiliate_link, category,
                 rating, badge, disclosed_shipping, priority, is_active)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING *
            """,
            req.title, req.image_url, req.price, req.currency, req.affiliate_link,
            req.category, req.rating, req.badge, req.disclosed_shipping, req.priority, req.is_active,
        )
        return dict(row)


@app.put("/api/admin/carousel-products/{product_id}")
async def admin_update_carousel_product(product_id: int, req: ProductCarouselInput, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE product_carousel
            SET title=$1, image_url=$2, price=$3, currency=$4, affiliate_link=$5,
                category=$6, rating=$7, badge=$8, disclosed_shipping=$9,
                priority=$10, is_active=$11, updated_at=now()
            WHERE id=$12
            RETURNING *
            """,
            req.title, req.image_url, req.price, req.currency, req.affiliate_link,
            req.category, req.rating, req.badge, req.disclosed_shipping,
            req.priority, req.is_active, product_id,
        )
        if row is None:
            raise HTTPException(404, "Product not found")
        return dict(row)


@app.delete("/api/admin/carousel-products/{product_id}")
async def admin_delete_carousel_product(product_id: int, _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM product_carousel WHERE id=$1", product_id)
        if result == "DELETE 0":
            raise HTTPException(404, "Product not found")
        return {"deleted": True, "id": product_id}


@app.get("/api/site-settings/{key}")
async def get_site_setting(key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM site_settings WHERE key=$1", key)
        return {"key": key, "value": row["value"] if row else ""}


@app.put("/api/admin/site-settings/{key}")
async def set_site_setting(key: str, value: str = Body(..., embed=True), _=Depends(require_admin_key)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO site_settings (key, value, updated_at)
            VALUES ($1, $2, now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
            RETURNING *
            """,
            key, value,
        )
        return dict(row)


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
    interests: list[str] = []
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
            INSERT INTO user_onboarding (user_id, email, gender, age_range, favorite_color, favorite_pet, interests, asset_preferences)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id) DO UPDATE SET
                gender = EXCLUDED.gender,
                age_range = EXCLUDED.age_range,
                favorite_color = EXCLUDED.favorite_color,
                favorite_pet = EXCLUDED.favorite_pet,
                interests = EXCLUDED.interests,
                asset_preferences = EXCLUDED.asset_preferences,
                completed_at = now()
            RETURNING *
            """,
            user["id"], user["email"], req.gender, req.age_range,
            req.favorite_color, req.favorite_pet, req.interests, req.asset_preferences,
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
    creative_type: str = "image_link"   # 'image_link' | 'raw_html'
    image_url: Optional[str] = None
    click_url: Optional[str] = None
    embed_html: Optional[str] = None    # used when creative_type == 'raw_html' — paste the network's own <a><img> or iframe code
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
        if self.creative_type not in {"image_link", "raw_html"}:
            raise HTTPException(422, "creative_type must be 'image_link' or 'raw_html'")
        if self.creative_type == "raw_html" and not self.embed_html:
            raise HTTPException(422, "embed_html is required when creative_type is 'raw_html'")
        if self.creative_type == "image_link" and (not self.image_url or not self.click_url):
            raise HTTPException(422, "image_url and click_url are required when creative_type is 'image_link'")


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
                (zone, size_key, creative_type, image_url, click_url, embed_html,
                 product_name, affiliate_name, asset_class, symbol, behavior, priority, is_active)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            RETURNING *
            """,
            req.zone, req.size_key, req.creative_type, req.image_url, req.click_url, req.embed_html,
            req.product_name, req.affiliate_name, req.asset_class, req.symbol, req.behavior, req.priority, req.is_active,
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
            SET zone=$1, size_key=$2, creative_type=$3, image_url=$4, click_url=$5, embed_html=$6,
                product_name=$7, affiliate_name=$8, asset_class=$9, symbol=$10, behavior=$11,
                priority=$12, is_active=$13, updated_at=now()
            WHERE id=$14
            RETURNING *
            """,
            req.zone, req.size_key, req.creative_type, req.image_url, req.click_url, req.embed_html,
            req.product_name, req.affiliate_name, req.asset_class, req.symbol, req.behavior,
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

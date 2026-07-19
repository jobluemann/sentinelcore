"""
SENTINEL CORE — Email campaign service
Sends via your own domain's mailbox (SMTP relay), not a third-party bulk
service — appropriate for the low volume / high-reputation-care use case.
Recipients are queued with randomized send times spread across a window
(default 48h) rather than fired all at once, so sending never looks
automated from the outside.

Env vars required (set in Render):
    SMTP_HOST       e.g. mail.winegrapetrader.com
    SMTP_PORT       e.g. 465
    SMTP_USERNAME   e.g. info@winegrapetrader.com
    SMTP_PASSWORD   the mailbox password
    SMTP_FROM_NAME  e.g. "Sentinel Core"
    PUBLIC_SITE_URL e.g. https://winegrapetrader.com  (used to build the unsubscribe link)
"""
import os
import random
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

from backend.db import get_pool

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Sentinel Core")
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://winegrapetrader.com")


def _build_unsubscribe_footer(token: str) -> str:
    link = f"{PUBLIC_SITE_URL.rstrip('/')}/api/unsubscribe?token={token}"
    return f"""
    <hr style="margin-top:32px;border:none;border-top:1px solid #333;">
    <p style="font-size:11px;color:#888;margin-top:12px;">
        You're receiving this because you signed up at Sentinel Core.
        <a href="{link}" style="color:#888;">Unsubscribe from future emails</a>.
    </p>
    """


def _personalize(body_html: str, recipient_name: str | None) -> str:
    first_name = (recipient_name or "there").split(" ")[0]
    return body_html.replace("{{FIRST_NAME}}", first_name).replace("{{NAME}}", recipient_name or "there")


def send_one_email(to_email: str, subject: str, body_html: str, unsubscribe_token: str) -> None:
    """Sends a single email via the domain's own SMTP mailbox. Raises on failure."""
    if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD]):
        raise RuntimeError("SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD not configured in environment")

    full_html = body_html + _build_unsubscribe_footer(unsubscribe_token)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USERNAME}>"
    msg["To"] = to_email
    msg.attach(MIMEText(full_html, "html"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, [to_email], msg.as_string())


async def build_audience(filters: dict) -> list[dict]:
    """Returns matching users (email, display_name) based on onboarding answers,
    excluding anyone who has unsubscribed. filters is a dict that may contain:
    gender, age_range, favorite_color, favorite_pet (exact match strings),
    interests, asset_preferences (arrays — matches if ANY overlap)."""
    pool = await get_pool()
    conditions = ["1=1"]
    params = []

    def add_exact(field, value):
        if value:
            params.append(value)
            conditions.append(f"o.{field} = ${len(params)}")

    def add_overlap(field, values):
        if values:
            params.append(values)
            conditions.append(f"o.{field} && ${len(params)}::text[]")

    add_exact("gender", filters.get("gender"))
    add_exact("age_range", filters.get("age_range"))
    add_exact("favorite_color", filters.get("favorite_color"))
    add_exact("favorite_pet", filters.get("favorite_pet"))
    add_overlap("interests", filters.get("interests"))
    add_overlap("asset_preferences", filters.get("asset_preferences"))

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT u.email, u.display_name
        FROM user_onboarding o
        JOIN users u ON u.id = o.user_id
        WHERE {where_clause}
          AND u.email NOT IN (SELECT email FROM email_unsubscribes)
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


async def queue_campaign(name: str, subject: str, body_html: str, filters: dict, window_hours: int = 48) -> dict:
    """Resolves the audience and inserts one randomized-schedule row per
    recipient into email_queue. Doesn't send anything itself — a separate
    scheduled job (process_email_queue.py) does the actual sending."""
    recipients = await build_audience(filters)
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            campaign = await conn.fetchrow(
                """
                INSERT INTO email_campaigns (name, subject, body_html, segment_filters, total_recipients, status)
                VALUES ($1, $2, $3, $4, $5, 'queued')
                RETURNING *
                """,
                name, subject, body_html, __import__("json").dumps(filters), len(recipients),
            )
            now = datetime.now(timezone.utc)
            for r in recipients:
                # Randomized send time anywhere in the window — this is what
                # keeps a batch of "simultaneous" sends from looking automated.
                offset_seconds = random.uniform(0, window_hours * 3600)
                scheduled_at = now + timedelta(seconds=offset_seconds)
                token = secrets.token_urlsafe(24)
                await conn.execute(
                    """
                    INSERT INTO email_queue (campaign_id, recipient_email, recipient_name, scheduled_at, unsubscribe_token)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    campaign["id"], r["email"], r["display_name"], scheduled_at, token,
                )
            return dict(campaign)

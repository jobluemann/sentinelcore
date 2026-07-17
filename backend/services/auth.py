"""
SENTINEL CORE — Auth Service
Verifies Firebase ID tokens, upserts the user into our own `users` table,
logs the login event, and emails busstechai@gmail.com on every signup/login
(per the disclosed Terms of Service: "login data sent to busstechai@gmail.com
for monitoring").
"""
import os
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from backend.db import get_pool

_firebase_initialized = False


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return

    json_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

    if json_env:
        # Preferred on platforms without a persistent filesystem (e.g. Render)
        cred = credentials.Certificate(json.loads(json_env))
    elif cred_path and os.path.exists(cred_path):
        # Preferred on traditional hosts where you can upload the file directly
        cred = credentials.Certificate(cred_path)
    else:
        raise RuntimeError(
            "Set either FIREBASE_SERVICE_ACCOUNT_JSON (paste the full JSON "
            "contents as the env var value) or FIREBASE_SERVICE_ACCOUNT_PATH "
            "(path to the uploaded file). Download the service account JSON "
            "from Firebase Console -> Project Settings -> Service Accounts -> "
            "Generate private key."
        )

    firebase_admin.initialize_app(cred)
    _firebase_initialized = True


def verify_firebase_token(id_token: str) -> dict:
    """Raises firebase_auth.InvalidIdTokenError / ExpiredIdTokenError on failure."""
    _init_firebase()
    decoded = firebase_auth.verify_id_token(id_token)
    return decoded


async def upsert_user(decoded_token: dict, ip_address: str = None, user_agent: str = None) -> dict:
    """
    Creates the user row on first login, updates last_login_at on every login.
    Returns the user row as a dict, plus whether this was a brand-new signup.
    """
    firebase_uid = decoded_token["uid"]
    email = decoded_token.get("email", "")
    display_name = decoded_token.get("name", email.split("@")[0] if email else "User")

    provider = "email"
    sign_in_provider = decoded_token.get("firebase", {}).get("sign_in_provider", "")
    if "google" in sign_in_provider:
        provider = "google"
    elif "github" in sign_in_provider:
        provider = "github"

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE firebase_uid = $1", firebase_uid
        )
        is_new_signup = existing is None

        row = await conn.fetchrow(
            """
            INSERT INTO users (firebase_uid, email, display_name, auth_provider, last_login_at)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (firebase_uid) DO UPDATE
                SET last_login_at = now(),
                    display_name = EXCLUDED.display_name
            RETURNING id, firebase_uid, email, display_name, auth_provider, created_at, last_login_at
            """,
            firebase_uid, email, display_name, provider,
        )

        await conn.execute(
            """
            INSERT INTO auth_events (user_id, event_type, ip_address, user_agent)
            VALUES ($1, $2, $3, $4)
            """,
            row["id"], "signup" if is_new_signup else "login", ip_address, user_agent,
        )

    user_dict = dict(row)

    # Fire-and-forget admin notification — never let email failure break login
    try:
        _send_admin_notification(user_dict, is_new_signup, ip_address)
    except Exception as e:
        print(f"[auth] admin email failed (non-fatal): {e}")

    return {"user": user_dict, "is_new_signup": is_new_signup}


def _send_admin_notification(user: dict, is_new_signup: bool, ip_address: str = None):
    admin_email = os.getenv("ADMIN_EMAIL", "busstechai@gmail.com")
    smtp_user = os.getenv("SMTP_USER", admin_email)
    smtp_password = os.getenv("SMTP_APP_PASSWORD")
    if not smtp_password:
        return  # not configured — skip silently, this is a non-critical side effect

    event = "NEW SIGNUP" if is_new_signup else "LOGIN"
    subject = f"Sentinel Core — {event}: {user['email']}"
    body = (
        f"Event: {event}\n"
        f"Email: {user['email']}\n"
        f"Display name: {user['display_name']}\n"
        f"Provider: {user['auth_provider']}\n"
        f"IP address: {ip_address or 'unknown'}\n"
        f"Time (UTC): {datetime.now(timezone.utc).isoformat()}\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = admin_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

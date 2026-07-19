"""
SENTINEL CORE — Migration: starter email templates
Seeds 4 ready-to-edit templates. Every email gets an unsubscribe footer
appended automatically at send time (see email_sender.py) — templates
don't need to include it themselves.
Run once against your live DB:  python -m backend.scripts.add_starter_email_templates
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

TEMPLATES = [
    (
        "Welcome Email",
        "welcome",
        "Welcome to Sentinel Core, {{FIRST_NAME}}",
        """
        <p>Hi {{FIRST_NAME}},</p>
        <p>Welcome to Sentinel Core — you've got a $10,000 demo account ready to go, so you can
        practice trading stocks, crypto, commodities, and forex with zero real risk.</p>
        <p>Jump back in whenever you're ready: <a href="https://winegrapetrader.com">winegrapetrader.com</a></p>
        <p>— The Sentinel Core team</p>
        """,
    ),
    (
        "Re-engagement",
        "re-engagement",
        "We miss you, {{FIRST_NAME}} — your demo account is still here",
        """
        <p>Hi {{FIRST_NAME}},</p>
        <p>It's been a while since your last visit to Sentinel Core. Markets have kept moving —
        your demo account and $10,000 balance are still exactly where you left them.</p>
        <p>Come see what's changed: <a href="https://winegrapetrader.com">winegrapetrader.com</a></p>
        <p>— The Sentinel Core team</p>
        """,
    ),
    (
        "Product Recommendation",
        "product",
        "A few things we thought you'd like, {{FIRST_NAME}}",
        """
        <p>Hi {{FIRST_NAME}},</p>
        <p>Based on what you're into, we've put together a few recommendations you might find useful.
        Check them out on the dashboard next time you're trading.</p>
        <p><a href="https://winegrapetrader.com">winegrapetrader.com</a></p>
        <p>— The Sentinel Core team</p>
        """,
    ),
    (
        "General Update",
        "update",
        "What's new at Sentinel Core",
        """
        <p>Hi {{FIRST_NAME}},</p>
        <p>Quick update on what's new — [add your update here].</p>
        <p><a href="https://winegrapetrader.com">winegrapetrader.com</a></p>
        <p>— The Sentinel Core team</p>
        """,
    ),
]


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        for name, category, subject, body_html in TEMPLATES:
            existing = await conn.fetchrow("SELECT id FROM email_templates WHERE name = $1", name)
            if existing:
                print(f"[seed] '{name}' already exists, skipping.")
                continue
            await conn.execute(
                "INSERT INTO email_templates (name, category, subject, body_html) VALUES ($1,$2,$3,$4)",
                name, category, subject, body_html.strip(),
            )
            print(f"[seed] Created template: {name}")
        print("[seed] Done.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

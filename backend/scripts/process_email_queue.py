"""
SENTINEL CORE — Email queue processor
Sends any queued emails whose scheduled time has arrived. Run this
periodically (e.g. every 15-30 minutes via a Render Cron Job) — it does
NOT send everything immediately; each recipient already has a randomized
scheduled_at time from when the campaign was queued (see email_sender.py).

This script just picks up whatever's due in this run and sends it, with a
small random pause between each individual send as extra insurance against
looking automated.

Run manually to test:  python -m backend.scripts.process_email_queue
"""
import asyncio
import random
import time

from dotenv import load_dotenv
from backend.db import get_pool
from backend.services.email_sender import send_one_email, _personalize

load_dotenv()

BATCH_LIMIT = 50            # max emails to send in one run of this script
MIN_DELAY_SECONDS = 5        # smallest gap between individual sends
MAX_DELAY_SECONDS = 45       # largest gap between individual sends


async def process_due_emails():
    pool = await get_pool()
    async with pool.acquire() as conn:
        due = await conn.fetch(
            """
            SELECT * FROM email_queue
            WHERE status = 'pending' AND scheduled_at <= now()
            ORDER BY scheduled_at ASC
            LIMIT $1
            """,
            BATCH_LIMIT,
        )

    if not due:
        print("[email_queue] Nothing due right now.")
        return 0

    sent, failed = 0, 0
    for i, row in enumerate(due):
        # Re-check unsubscribe status right before sending — someone may have
        # opted out after this row was queued but before it became due.
        async with pool.acquire() as conn:
            unsub = await conn.fetchrow(
                "SELECT 1 FROM email_unsubscribes WHERE email = $1", row["recipient_email"]
            )
            if unsub:
                await conn.execute(
                    "UPDATE email_queue SET status = 'skipped_unsubscribed' WHERE id = $1", row["id"]
                )
                continue

            campaign = await conn.fetchrow(
                "SELECT subject, body_html FROM email_campaigns WHERE id = $1", row["campaign_id"]
            )

        try:
            personalized_body = _personalize(campaign["body_html"], row["recipient_name"])
            send_one_email(row["recipient_email"], campaign["subject"], personalized_body, row["unsubscribe_token"])
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE email_queue SET status = 'sent', sent_at = now() WHERE id = $1", row["id"]
                )
            sent += 1
            print(f"[email_queue] Sent to {row['recipient_email']}")
        except Exception as e:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE email_queue SET status = 'failed', error = $1 WHERE id = $2", str(e), row["id"]
                )
            failed += 1
            print(f"[email_queue] Failed for {row['recipient_email']}: {e}")

        # Small randomized pause between sends — skip after the last one
        if i < len(due) - 1:
            time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    print(f"[email_queue] Done — {sent} sent, {failed} failed.")
    return sent


if __name__ == "__main__":
    asyncio.run(process_due_emails())

"""
SENTINEL CORE — One-time migration: copy Amazon products from the banner
tool (affiliate_creatives, zone='top_carousel') into the correct Product
Carousel tool (product_carousel).

This only COPIES — it doesn't delete the originals, so nothing is lost if
anything looks off afterward. Price is set to 0 and disclosed_shipping to
false as placeholders — go into #admin-products afterward to fill in the
real price and tick "Disclosed" for each one to make it go live.

Run once:  python -m backend.scripts.migrate_top_carousel_to_products
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()


async def main():
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(
            """
            SELECT * FROM affiliate_creatives
            WHERE zone = 'top_carousel' AND creative_type = 'image_link'
            ORDER BY id
            """
        )
        if not rows:
            print("[migrate] No image-based Top Carousel entries found — nothing to migrate.")
            return

        migrated = 0
        for r in rows:
            await conn.execute(
                """
                INSERT INTO product_carousel
                    (title, image_url, price, currency, affiliate_link, priority, is_active, disclosed_shipping)
                VALUES ($1, $2, 0, 'USD', $3, $4, $5, false)
                """,
                r["product_name"], r["image_url"], r["click_url"], r["priority"], r["is_active"],
            )
            migrated += 1
            print(f"[migrate] Copied: {r['product_name'][:60]}")

        print(f"\n[migrate] Done — {migrated} product(s) copied into product_carousel.")
        print("[migrate] Go to #admin-products, add the real price to each one, "
              "and tick 'Disclosed shipping/import costs' to make it go live.")
        print("[migrate] The originals in affiliate_creatives were left untouched — "
              "delete them from #admin once you've confirmed the copies look right.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

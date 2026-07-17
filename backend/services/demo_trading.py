"""
SENTINEL CORE — Demo Trading Engine
Paper trading against live prices. No real money ever moves.

Key functions:
  get_or_create_demo_account(user_id)   -> auto-grants a free demo account on first use
  admin_grant_or_reset(user_id, by)     -> manual admin action (used until payment is live)
  buy(user_id, symbol, asset_class, qty, price)
  sell(user_id, symbol, qty, price)
  get_portfolio(user_id)                -> balance, holdings, P&L
"""
import os
from decimal import Decimal
from backend.db import get_pool

DEFAULT_STARTING_BALANCE = Decimal(os.getenv("DEMO_STARTING_BALANCE", "10000.00"))


class InsufficientFundsError(Exception):
    pass


class InsufficientHoldingsError(Exception):
    pass


class NoDemoAccountError(Exception):
    pass


async def get_or_create_demo_account(user_id: str) -> dict:
    """Every signed-in user gets a free demo account automatically — no gating."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM demo_accounts WHERE user_id = $1", user_id
        )
        if row:
            return dict(row)

        row = await conn.fetchrow(
            """
            INSERT INTO demo_accounts (user_id, cash_balance, starting_balance, source)
            VALUES ($1, $2, $2, 'signup')
            RETURNING *
            """,
            user_id, DEFAULT_STARTING_BALANCE,
        )
        return dict(row)


async def admin_grant_or_reset(user_id: str, granted_by: str, amount: Decimal = None) -> dict:
    """
    Manual admin action — used for free-credit grants while payment isn't live yet.
    If the user already has an account, this archives the current round to
    demo_round_history and resets balance/holdings (new round). If not, creates one.
    """
    amount = amount if amount is not None else DEFAULT_STARTING_BALANCE
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT * FROM demo_accounts WHERE user_id = $1", user_id
            )

            if existing is None:
                row = await conn.fetchrow(
                    """
                    INSERT INTO demo_accounts
                        (user_id, cash_balance, starting_balance, round_number, source, granted_by)
                    VALUES ($1, $2, $2, 1, 'admin_grant', $3)
                    RETURNING *
                    """,
                    user_id, amount, granted_by,
                )
                return dict(row)

            # Archive the round that's ending
            pnl = existing["cash_balance"] - existing["starting_balance"]
            pnl_pct = (pnl / existing["starting_balance"] * 100) if existing["starting_balance"] else Decimal(0)
            await conn.execute(
                """
                INSERT INTO demo_round_history
                    (demo_account_id, round_number, final_balance, starting_balance, pnl, pnl_pct)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                existing["id"], existing["round_number"], existing["cash_balance"],
                existing["starting_balance"], pnl, pnl_pct,
            )

            # Clear holdings and reset balance for the new round
            await conn.execute("DELETE FROM demo_holdings WHERE demo_account_id = $1", existing["id"])
            row = await conn.fetchrow(
                """
                UPDATE demo_accounts
                SET cash_balance = $1,
                    starting_balance = $1,
                    round_number = round_number + 1,
                    source = 'admin_grant',
                    granted_by = $2,
                    is_active = true,
                    updated_at = now()
                WHERE user_id = $3
                RETURNING *
                """,
                amount, granted_by, user_id,
            )
            return dict(row)


async def has_active_demo_account(user_id: str) -> bool:
    """Used to gate features (e.g. AI Forecast) to users who've engaged with sim trading."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_active FROM demo_accounts WHERE user_id = $1", user_id
        )
        return bool(row and row["is_active"])


async def buy(user_id: str, symbol: str, asset_class: str, quantity: Decimal, price: Decimal) -> dict:
    quantity = Decimal(str(quantity))
    price = Decimal(str(price))
    total_cost = quantity * price

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            account = await conn.fetchrow(
                "SELECT * FROM demo_accounts WHERE user_id = $1 FOR UPDATE", user_id
            )
            if account is None:
                raise NoDemoAccountError(f"No demo account for user {user_id}")
            if account["cash_balance"] < total_cost:
                raise InsufficientFundsError(
                    f"Balance ${account['cash_balance']} insufficient for order of ${total_cost}"
                )

            new_balance = account["cash_balance"] - total_cost
            await conn.execute(
                "UPDATE demo_accounts SET cash_balance = $1, updated_at = now() WHERE id = $2",
                new_balance, account["id"],
            )

            existing_holding = await conn.fetchrow(
                "SELECT * FROM demo_holdings WHERE demo_account_id = $1 AND symbol = $2",
                account["id"], symbol,
            )
            if existing_holding:
                new_qty = existing_holding["quantity"] + quantity
                new_avg = (
                    (existing_holding["quantity"] * existing_holding["avg_entry_price"])
                    + (quantity * price)
                ) / new_qty
                await conn.execute(
                    """
                    UPDATE demo_holdings
                    SET quantity = $1, avg_entry_price = $2, updated_at = now()
                    WHERE id = $3
                    """,
                    new_qty, new_avg, existing_holding["id"],
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO demo_holdings (demo_account_id, symbol, asset_class, quantity, avg_entry_price)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    account["id"], symbol, asset_class, quantity, price,
                )

            await conn.execute(
                """
                INSERT INTO demo_trades
                    (demo_account_id, round_number, symbol, asset_class, side, quantity, price, total_value, balance_after)
                VALUES ($1, $2, $3, $4, 'buy', $5, $6, $7, $8)
                """,
                account["id"], account["round_number"], symbol, asset_class,
                quantity, price, total_cost, new_balance,
            )

            return {
                "symbol": symbol, "side": "buy", "quantity": str(quantity),
                "price": str(price), "total_cost": str(total_cost),
                "new_balance": str(new_balance),
            }


async def sell(user_id: str, symbol: str, quantity: Decimal, price: Decimal) -> dict:
    quantity = Decimal(str(quantity))
    price = Decimal(str(price))
    proceeds = quantity * price

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            account = await conn.fetchrow(
                "SELECT * FROM demo_accounts WHERE user_id = $1 FOR UPDATE", user_id
            )
            if account is None:
                raise NoDemoAccountError(f"No demo account for user {user_id}")

            holding = await conn.fetchrow(
                "SELECT * FROM demo_holdings WHERE demo_account_id = $1 AND symbol = $2",
                account["id"], symbol,
            )
            if holding is None or holding["quantity"] < quantity:
                held = holding["quantity"] if holding else Decimal(0)
                raise InsufficientHoldingsError(
                    f"Trying to sell {quantity} {symbol}, only hold {held}"
                )

            new_qty = holding["quantity"] - quantity
            if new_qty == 0:
                await conn.execute("DELETE FROM demo_holdings WHERE id = $1", holding["id"])
            else:
                await conn.execute(
                    "UPDATE demo_holdings SET quantity = $1, updated_at = now() WHERE id = $2",
                    new_qty, holding["id"],
                )

            new_balance = account["cash_balance"] + proceeds
            await conn.execute(
                "UPDATE demo_accounts SET cash_balance = $1, updated_at = now() WHERE id = $2",
                new_balance, account["id"],
            )

            await conn.execute(
                """
                INSERT INTO demo_trades
                    (demo_account_id, round_number, symbol, asset_class, side, quantity, price, total_value, balance_after)
                VALUES ($1, $2, $3, $4, 'sell', $5, $6, $7, $8)
                """,
                account["id"], account["round_number"], symbol, holding["asset_class"],
                quantity, price, proceeds, new_balance,
            )

            return {
                "symbol": symbol, "side": "sell", "quantity": str(quantity),
                "price": str(price), "proceeds": str(proceeds),
                "new_balance": str(new_balance),
            }


async def get_portfolio(user_id: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        account = await conn.fetchrow("SELECT * FROM demo_accounts WHERE user_id = $1", user_id)
        if account is None:
            raise NoDemoAccountError(f"No demo account for user {user_id}")

        holdings = await conn.fetch(
            "SELECT * FROM demo_holdings WHERE demo_account_id = $1", account["id"]
        )

        return {
            "cash_balance": str(account["cash_balance"]),
            "starting_balance": str(account["starting_balance"]),
            "round_number": account["round_number"],
            "holdings": [dict(h) for h in holdings],
        }

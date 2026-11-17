import logging
import re
from typing import Any

from app.chat_connectors.telegram import telegram_connector
from app.domain.models import TransactionStatus, User
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.categorization import create_or_update_vendor_rule
from app.services.transactions import (
    get_financial_summary,
    get_transaction_by_id,
    get_user_transactions,
    update_transaction,
)

logger = logging.getLogger(__name__)

async def dispatch_user_catchup(db: NativeRepository, user: User) -> dict[str, Any]:
    """Sends uncategorized transaction catch-up message to a single user."""
    if not user.telegram_chat_id:
        return {"user_id": user.id, "sent": False, "reason": "No telegram_chat_id linked"}

    pending = await get_user_transactions(
        db=db,
        user_id=user.id,
        limit=10,
        status=TransactionStatus.NEEDS_REVIEW,
    )
    if not pending:
        return {"user_id": user.id, "sent": False, "reason": "No transactions needing review"}

    lines = [f"🔔 *CashBuffer Catch-up*: You have *{len(pending)}* transactions needing review:\n"]
    for i, tx in enumerate(pending, 1):
        lines.append(
            f"{i}. *{tx.vendor_raw}* — `INR {tx.amount:.2f}` ({tx.record_date})\n   Tag: `/cat {tx.id} <CategoryName>`"
        )

    lines.append("\n_Example:_ `/cat " + str(pending[0].id) + " Food & Dining`")
    message_text = "\n".join(lines)

    sent = await telegram_connector.send_message(user.telegram_chat_id, message_text)
    return {"user_id": user.id, "sent": sent, "pending_count": len(pending)}

async def dispatch_all_catchups(db: NativeRepository, user_id: str | None = None) -> dict[str, Any]:
    """Dispatches catch-up messages to either one user or all users with linked Telegram."""
    if user_id:
        user = await db.get_user_by_idp(user_id)
        if not user:
            user = await db.get_user_by_id(user_id)
        if not user:
            return {"dispatched": 0, "results": [{"error": "User not found"}]}
        res = await dispatch_user_catchup(db, user)
        return {"dispatched": 1 if res.get("sent") else 0, "results": [res]}

    # Find all users with telegram_chat_id set
    async with db.pool.connection() as conn:
        from psycopg.rows import dict_row
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, idp_user_id, email, telegram_chat_id, created_at, updated_at "
                "FROM users WHERE telegram_chat_id IS NOT NULL;"
            )
            rows = await cur.fetchall()
            users = [
                User(
                    id=str(r["id"]),
                    idp_user_id=r["idp_user_id"],
                    email=r["email"],
                    telegram_chat_id=r["telegram_chat_id"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in rows
            ]

    results = []
    sent_count = 0
    for u in users:
        res = await dispatch_user_catchup(db, u)
        results.append(res)
        if res.get("sent"):
            sent_count += 1

    return {"dispatched": sent_count, "results": results}

async def process_telegram_update(db: NativeRepository, update_data: dict[str, Any]) -> dict[str, Any]:
    """
    Processes incoming Telegram Webhook payloads.
    Supports /start, /cat <id> <category>, /summary, /balance.
    """
    message = update_data.get("message") or update_data.get("edited_message")
    if not message:
        return {"status": "ignored", "reason": "No message in update"}

    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return {"status": "ignored", "reason": "Missing chat_id or text"}

    if text.startswith("/start"):
        await telegram_connector.send_message(
            chat_id,
            "👋 Welcome to CashBuffer!\nTo link your account, use the *Link Telegram* option in your CashBuffer dashboard.",
        )
        return {"status": "prompted_link"}

    user = await db.get_user_by_telegram_chat_id(chat_id)
    if not user:
        await telegram_connector.send_message(
            chat_id,
            "⚠️ Your Telegram is not linked to any CashBuffer account yet.\nUse the *Link Telegram* option in your CashBuffer dashboard to connect.",
        )
        return {"status": "unlinked_chat"}

    # 2. /summary or /balance
    if text.startswith("/summary") or text.startswith("/balance") or text.startswith("/buffer"):
        summary = await get_financial_summary(db, user.id)
        msg = (
            f"📊 *CashBuffer Summary*\n"
            f"💰 *Net Buffer:* `INR {summary['net_buffer']:.2f}`\n"
            f"📈 Total Inflow: `INR {summary['total_inflow']:.2f}`\n"
            f"📉 Total Outflow: `INR {summary['total_outflow']:.2f}`\n"
            f"❓ Pending Review: *{summary['uncategorized_count']}*"
        )
        await telegram_connector.send_message(chat_id, msg)
        return {"status": "summary_sent", "user_id": user.id}

    # 3. /cat <tx_id> <category_name>
    cat_match = re.match(r"^/cat\s+(\d+)\s+(.+)$", text, re.IGNORECASE)
    if cat_match:
        tx_id = int(cat_match.group(1))
        category_name = cat_match.group(2).strip()

        tx = await get_transaction_by_id(db, user.id, tx_id)
        if not tx:
            await telegram_connector.send_message(chat_id, f"❌ Transaction `#{tx_id}` not found in your account.")
            return {"status": "not_found", "tx_id": tx_id}

        cats = await db.get_categories(user.id)
        cat_obj = next((c for c in cats if c.name.lower() == category_name.lower()), None)
        if not cat_obj:
            cat_obj = await db.create_category(user_id=user.id, name=category_name)

        await update_transaction(db, user.id, tx.id, category_id=cat_obj.id)
        await create_or_update_vendor_rule(db, user.id, tx.vendor_raw, cat_obj.id)

        await telegram_connector.send_message(
            chat_id,
            f"✅ Categorized transaction `#{tx.id}` (*{tx.vendor_raw}*) as *{cat_obj.name}*!\n"
            f"🧠 Future transactions matching `{tx.vendor_raw}` will be auto-tagged.",
        )
        return {"status": "categorized", "tx_id": tx.id, "category": cat_obj.name}

    # Default help reply
    await telegram_connector.send_message(
        chat_id,
        "💡 *CashBuffer Bot Commands:*\n"
        "• `/summary` - View current buffer & totals\n"
        "• `/cat <id> <category>` - Categorize transaction & learn vendor rule\n"
        "• `/catchup` - Check pending uncategorized transactions",
    )
    return {"status": "help_replied"}

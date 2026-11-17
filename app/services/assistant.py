import json
import logging
import re
from typing import Any

import litellm

from app.domain.models import TransactionStatus
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.categorization import create_or_update_vendor_rule
from app.services.llm import get_user_active_llm_credentials
from app.services.transactions import (
    get_financial_summary,
    get_user_transactions,
    update_transaction,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CashBuffer's AI Financial Assistant.
You have access to the user's multi-tenant financial data:
- Inflows, Outflows, Net Buffer
- Recent transactions
- Category breakdown
- Uncategorized transactions needing review

Your job is to answer user queries with actionable financial insights, assist in categorizing expenses, and suggest automated vendor rules.
Be concise, accurate, and direct.

Available deterministic actions if the user wants to categorize or create rules:
- Categorize transaction: [ACTION:CATEGORIZE:tx_id:CategoryName]
- Create vendor rule: [ACTION:RULE:VendorPattern:CategoryName]
"""

async def get_assistant_context(db: NativeRepository, user_id: str) -> dict[str, Any]:
    """Assembles tenant-scoped financial context for the assistant."""
    summary = await get_financial_summary(db, user_id)

    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)

    categories = []
    if user:
        cats = await db.get_categories(user.id)
        categories = [c.name for c in cats]

    # Uncategorized transactions
    uncategorized = await get_user_transactions(db, user_id, limit=10, status=TransactionStatus.NEEDS_REVIEW)
    uncategorized_list = [
        {"id": tx.id, "vendor": tx.vendor_raw, "amount": tx.amount, "date": str(tx.record_date)}
        for tx in uncategorized
    ]

    # Recent transactions
    recent = await get_user_transactions(db, user_id, limit=10)
    recent_list = [
        {"id": tx.id, "vendor": tx.vendor_raw, "amount": tx.amount, "inflow": tx.is_inflow, "date": str(tx.record_date)}
        for tx in recent
    ]

    return {
        "summary": summary,
        "categories": categories,
        "uncategorized_count": len(uncategorized),
        "uncategorized": uncategorized_list,
        "recent_transactions": recent_list,
    }

async def execute_assistant_chat(
    db: NativeRepository,
    user_id: str,
    message: str,
) -> dict[str, Any]:
    """Processes chat request with context injection and action execution."""
    context = await get_assistant_context(db, user_id)
    msg_lower = message.lower().strip()

    # Fast deterministic shortcuts for common questions
    if any(q in msg_lower for q in ["buffer", "balance", "net", "how much do i have"]):
        summary = context["summary"]
        reply = (
            f"💼 *Net Cash Buffer Summary*:\n"
            f"• Inflows: `INR {summary['total_inflow']:.2f}`\n"
            f"• Outflows: `INR {summary['total_outflow']:.2f}`\n"
            f"• *Net Buffer*: `INR {summary['net_buffer']:.2f}`"
        )
        return {
            "reply": reply,
            "actions_executed": [],
            "widgets": [
                {
                    "type": "summary_card",
                    "data": summary,
                }
            ],
            "context": context,
        }

    if any(q in msg_lower for q in ["uncategorized", "needs review", "pending review"]):
        uncat = context["uncategorized"]
        if not uncat:
            reply = "🎉 All your transactions are cleanly categorized! No pending reviews."
        else:
            items_str = "\n".join([f"• ID #{t['id']} — *{t['vendor']}*: `INR {t['amount']:.2f}`" for t in uncat])
            reply = f"🔍 Found *{len(uncat)}* transactions needing review:\n{items_str}\n\nTell me how you'd like to categorize them!"
        return {
            "reply": reply,
            "actions_executed": [],
            "widgets": [{"type": "uncategorized_list", "data": uncat}],
            "context": context,
        }

    # If BYO-LLM credentials available, call LLM
    llm_creds = await get_user_active_llm_credentials(db, user_id)
    if not llm_creds:
        return {
            "reply": (
                "🤖 *BYO-LLM Not Configured*\n"
                "Please configure your OpenAI, Anthropic, or Ollama API key in `/llm-config` to enable intelligent conversational reasoning.\n\n"
                f"Meanwhile, your net cash buffer is *INR {context['summary']['net_buffer']:.2f}* across {context['summary']['transaction_count']} transactions."
            ),
            "actions_executed": [],
            "widgets": [],
            "context": context,
        }

    provider, model_name, api_key = llm_creds
    model_ident = f"{provider}/{model_name}" if "/" not in model_name else model_name

    prompt_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Financial Context:\n{json.dumps(context, default=str)}"},
        {"role": "user", "content": message},
    ]

    try:
        response = await litellm.acompletion(
            model=model_ident,
            messages=prompt_messages,
            api_key=api_key,
            max_tokens=600,
            temperature=0.2,
        )
        raw_reply = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LiteLLM call error: {e}")
        return {
            "reply": f"⚠️ Error communicating with your configured LLM ({provider}/{model_name}): {e!s}",
            "actions_executed": [],
            "widgets": [],
            "context": context,
        }

    # Parse and execute deterministic actions emitted by model
    actions_executed = []
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)

    cat_matches = re.findall(r"\[ACTION:CATEGORIZE:(\d+):([^\]]+)\]", raw_reply)
    for tx_id_str, cat_name in cat_matches:
        try:
            tx_id = int(tx_id_str)
            if user:
                cats = await db.get_categories(user.id)
                target_cat = next((c for c in cats if c.name.lower() == cat_name.lower().strip()), None)
                if not target_cat:
                    target_cat = await db.create_category(user_id=user.id, name=cat_name.strip())
                await update_transaction(db, user_id, tx_id, category_id=target_cat.id)
                actions_executed.append(f"Categorized #{tx_id} as {target_cat.name}")
        except Exception as ex:
            logger.warning(f"Failed to execute CATEGORIZE action: {ex}")

    rule_matches = re.findall(r"\[ACTION:RULE:([^:]+):([^\]]+)\]", raw_reply)
    for pattern, cat_name in rule_matches:
        try:
            if user:
                cats = await db.get_categories(user.id)
                target_cat = next((c for c in cats if c.name.lower() == cat_name.lower().strip()), None)
                if not target_cat:
                    target_cat = await db.create_category(user_id=user.id, name=cat_name.strip())
                await create_or_update_vendor_rule(
                    repo=db,
                    user_id=user.id,
                    vendor_pattern=pattern.strip(),
                    category_id=target_cat.id,
                    re_evaluate_pending=True,
                )
                actions_executed.append(f"Created rule: {pattern.strip()} -> {target_cat.name}")
        except Exception as ex:
            logger.warning(f"Failed to execute RULE action: {ex}")

    clean_reply = re.sub(r"\[ACTION:[^\]]+\]", "", raw_reply).strip()

    return {
        "reply": clean_reply,
        "actions_executed": actions_executed,
        "widgets": [],
        "context": context,
    }

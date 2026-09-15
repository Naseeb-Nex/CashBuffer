import json
import logging
import os
import re
from typing import Any

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category, TransactionStatus
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


async def get_assistant_context(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Assembles tenant-scoped financial context for the assistant."""
    summary = await get_financial_summary(db, user_id)

    # Categories
    cat_stmt = select(Category).where(Category.user_id == user_id)
    cat_res = await db.execute(cat_stmt)
    categories = [c.name for c in cat_res.scalars().all()]

    # Uncategorized transactions
    uncategorized = await get_user_transactions(db, user_id, limit=10, status=TransactionStatus.NEEDS_REVIEW)
    uncategorized_list = [
        {"id": tx.id, "vendor": tx.vendor_raw, "amount": tx.amount, "date": str(tx.record_date)} for tx in uncategorized
    ]

    # Recent transactions
    recent = await get_user_transactions(db, user_id, limit=10)
    recent_list = [
        {
            "id": tx.id,
            "vendor": tx.vendor_raw,
            "amount": tx.amount,
            "inflow": tx.is_inflow,
            "date": str(tx.record_date),
            "status": tx.status.value,
        }
        for tx in recent
    ]

    return {
        "summary": summary,
        "categories": categories,
        "uncategorized": uncategorized_list,
        "recent_transactions": recent_list,
    }


async def execute_assistant_chat(db: AsyncSession, user_id: str, message: str) -> dict[str, Any]:
    """
    Executes assistant query via BYO-LLM LiteLLM gateway with fallback and action resolution.
    """
    context = await get_assistant_context(db, user_id)
    creds = await get_user_active_llm_credentials(db, user_id)

    executed_actions = []
    widgets = []

    # Include financial summary widget by default if query asks for summary/spending/breakdown
    query_lower = message.lower()
    if any(k in query_lower for k in ["summary", "spending", "breakdown", "overview", "buffer"]):
        widgets.append(
            {
                "type": "summary_card",
                "data": context["summary"],
            }
        )
    if any(k in query_lower for k in ["uncategorized", "review", "catch up", "catch-up", "pending"]):
        widgets.append(
            {
                "type": "uncategorized_list",
                "items": context["uncategorized"],
            }
        )

    reply_text = ""

    if creds:
        provider, model_name, api_key = creds
        model_identifier = model_name
        if provider == "anthropic" and not model_name.startswith("anthropic/"):
            model_identifier = f"anthropic/{model_name}"
        elif provider == "gemini" and not model_name.startswith("gemini/"):
            model_identifier = f"gemini/{model_name}"

        context_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"User Financial Context:\n"
            f"- Net Buffer: INR {context['summary']['net_buffer']}\n"
            f"- Total Inflow: INR {context['summary']['total_inflow']}\n"
            f"- Total Outflow: INR {context['summary']['total_outflow']}\n"
            f"- Categories: {', '.join(context['categories'])}\n"
            f"- Uncategorized items: {json.dumps(context['uncategorized'])}\n"
            f"- Recent items: {json.dumps(context['recent_transactions'])}\n"
        )

        try:
            api_base = os.environ.get("OPENAI_API_BASE") if provider == "openai" else None
            response = await litellm.acompletion(
                model=model_identifier,
                messages=[
                    {"role": "system", "content": context_prompt},
                    {"role": "user", "content": message},
                ],
                api_key=api_key,
                api_base=api_base,
                max_tokens=500,
                temperature=0.3,
                timeout=25,
            )
            reply_text = response.choices[0].message.content.strip()

            # Check for action directives in LLM response
            cat_matches = re.findall(r"\[ACTION:CATEGORIZE:(\d+):([^\]]+)\]", reply_text)
            for tx_id_str, cat_name in cat_matches:
                tx_id = int(tx_id_str)
                # Find category
                cat_stmt = select(Category).where(Category.user_id == user_id, Category.name.ilike(cat_name.strip()))
                c_res = await db.execute(cat_stmt)
                cat_obj = c_res.scalar_one_or_none()
                if not cat_obj:
                    cat_obj = Category(user_id=user_id, name=cat_name.strip())
                    db.add(cat_obj)
                    await db.commit()
                    await db.refresh(cat_obj)

                await update_transaction(db, user_id, tx_id, category_id=cat_obj.id)
                executed_actions.append(f"Categorized transaction #{tx_id} as '{cat_obj.name}'")

            rule_matches = re.findall(r"\[ACTION:RULE:([^:]+):([^\]]+)\]", reply_text)
            for pattern, cat_name in rule_matches:
                cat_stmt = select(Category).where(Category.user_id == user_id, Category.name.ilike(cat_name.strip()))
                c_res = await db.execute(cat_stmt)
                cat_obj = c_res.scalar_one_or_none()
                if not cat_obj:
                    cat_obj = Category(user_id=user_id, name=cat_name.strip())
                    db.add(cat_obj)
                    await db.commit()
                    await db.refresh(cat_obj)

                await create_or_update_vendor_rule(db, user_id, pattern.strip(), cat_obj.id)
                executed_actions.append(f"Created rule: '{pattern.strip()}' -> '{cat_obj.name}'")

            # Clean action tokens from user visible text
            reply_text = re.sub(r"\[ACTION:[^\]]+\]", "", reply_text).strip()

        except Exception as e:
            logger.warning(f"LiteLLM completion failed, falling back to deterministic response: {e}")
            reply_text = _deterministic_fallback(message, context)
    else:
        reply_text = _deterministic_fallback(message, context)

    return {
        "reply": reply_text,
        "actions_executed": executed_actions,
        "widgets": widgets,
        "context": {
            "net_buffer": context["summary"]["net_buffer"],
            "uncategorized_count": len(context["uncategorized"]),
        },
    }


def _deterministic_fallback(message: str, context: dict[str, Any]) -> str:
    """Provides instant deterministic financial response when no LLM key is set."""
    msg = message.lower()
    summary = context["summary"]
    uncat = context["uncategorized"]

    if "buffer" in msg or "balance" in msg or "net" in msg:
        return (
            f"Your current Net Cash Buffer is INR {summary['net_buffer']:.2f}. "
            f"Total inflows: INR {summary['total_inflow']:.2f}, Total outflows: INR {summary['total_outflow']:.2f}."
        )
    if "uncategorized" in msg or "pending" in msg or "review" in msg:
        if not uncat:
            return "You have 0 uncategorized transactions! Everything is tagged."
        items_str = ", ".join([f"{u['vendor']} (INR {u['amount']})" for u in uncat[:5]])
        return f"You have {len(uncat)} transactions needing review: {items_str}."
    if "category" in msg or "breakdown" in msg or "spend" in msg:
        breakdown = summary.get("category_breakdown", [])
        if not breakdown:
            return "No spending categorized yet."
        top = breakdown[0]
        return f"Top spending category is '{top['category_name']}' with INR {top['total_amount']:.2f}."

    return f"CashBuffer status: Net Buffer INR {summary['net_buffer']:.2f}. {len(uncat)} transactions pending review."

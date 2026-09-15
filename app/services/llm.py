import logging
import os
from typing import Any

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_key, encrypt_key
from app.db.models import LLMConfig, User

logger = logging.getLogger(__name__)


def mask_key(api_key: str) -> str:
    """Returns a masked version of the API key for safe UI display."""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "sk-****"
    return f"{api_key[:4]}...{api_key[-4:]}"


async def get_user_llm_config(db: AsyncSession, user_id: str) -> dict[str, Any] | None:
    """Fetches user LLM config with masked API key."""
    stmt = select(LLMConfig).where(LLMConfig.user_id == user_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        return None

    try:
        raw_key = decrypt_key(config.encrypted_key)
        masked = mask_key(raw_key)
    except Exception:
        masked = "sk-****"

    return {
        "user_id": config.user_id,
        "provider": config.provider,
        "model_name": config.model_name,
        "masked_key": masked,
    }


async def save_user_llm_config(
    db: AsyncSession,
    user_id: str,
    provider: str,
    model_name: str,
    api_key: str,
) -> LLMConfig:
    """Encrypts key and saves/updates user LLM config."""
    stmt_user = select(User).where(User.id == user_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"{user_id}@cashbuffer.local")
        db.add(user)
        await db.commit()

    encrypted = encrypt_key(api_key.strip())
    stmt = select(LLMConfig).where(LLMConfig.user_id == user_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.provider = provider.strip().lower()
        config.model_name = model_name.strip()
        config.encrypted_key = encrypted
    else:
        config = LLMConfig(
            user_id=user_id,
            provider=provider.strip().lower(),
            model_name=model_name.strip(),
            encrypted_key=encrypted,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return config


async def get_user_active_llm_credentials(db: AsyncSession, user_id: str) -> tuple[str, str, str] | None:
    """
    Returns (provider, model_name, decrypted_api_key) for the user.
    Falls back to system environment if user has not set a custom key.
    """
    stmt = select(LLMConfig).where(LLMConfig.user_id == user_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        try:
            raw_key = decrypt_key(config.encrypted_key)
            return config.provider, config.model_name, raw_key
        except Exception as e:
            logger.error(f"Failed to decrypt user LLM key: {e}")

    # Fallback to system environment keys if available
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return "openai", "gpt-4o-mini", openai_key

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        return "anthropic", "claude-3-5-sonnet-20241022", anthropic_key

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return "gemini", "gemini-1.5-flash", gemini_key

    return None


async def test_llm_connection(provider: str, model_name: str, api_key: str) -> dict[str, Any]:
    """Tests LLM credentials by sending a lightweight completion request."""
    model_identifier = model_name
    if provider == "openai" and not model_name.startswith("openai/"):
        model_identifier = model_name
    elif provider == "anthropic" and not model_name.startswith("anthropic/"):
        model_identifier = f"anthropic/{model_name}"
    elif provider == "gemini" and not model_name.startswith("gemini/"):
        model_identifier = f"gemini/{model_name}"
    elif provider == "groq" and not model_name.startswith("groq/"):
        model_identifier = f"groq/{model_name}"
    elif provider == "ollama" and not model_name.startswith("ollama/"):
        model_identifier = f"ollama/{model_name}"

    try:
        api_base = os.environ.get("OPENAI_API_BASE") if provider == "openai" else None
        response = await litellm.acompletion(
            model=model_identifier,
            messages=[{"role": "user", "content": "Respond with the single word 'OK'."}],
            api_key=api_key,
            api_base=api_base,
            max_tokens=10,
            timeout=15,
        )
        content = response.choices[0].message.content.strip()
        return {"success": True, "model": model_identifier, "response": content}
    except Exception as e:
        return {"success": False, "error": str(e)}

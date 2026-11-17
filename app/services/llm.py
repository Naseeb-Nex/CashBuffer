import logging
import os
from typing import Any

import litellm

from app.core.crypto import decrypt_key, encrypt_key
from app.domain.models import LLMConfig
from app.infrastructure.persistence.native_repository import NativeRepository

logger = logging.getLogger(__name__)

def mask_key(api_key: str) -> str:
    """Returns a masked version of the API key for safe UI display."""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "sk-****"
    return f"{api_key[:4]}...{api_key[-4:]}"

async def get_user_llm_config(db: NativeRepository, user_id: str) -> dict[str, Any] | None:
    """Fetches user LLM config with masked API key."""
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        return None

    config = await db.get_llm_config(user.id)
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
    db: NativeRepository,
    user_id: str,
    provider: str,
    model_name: str,
    api_key: str,
) -> LLMConfig:
    """Encrypts key and saves/updates user LLM config."""
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        user = await db.get_or_create_user(user_id)

    encrypted = encrypt_key(api_key.strip())
    return await db.save_llm_config(
        user_id=user.id,
        provider=provider.strip().lower(),
        model_name=model_name.strip(),
        encrypted_key=encrypted,
    )

async def get_user_active_llm_credentials(
    db: NativeRepository, user_id: str
) -> tuple[str, str, str] | None:
    """
    Returns (provider, model_name, raw_decrypted_api_key) if configured.
    """
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        return None

    config = await db.get_llm_config(user.id)
    if not config:
        return None

    try:
        raw_key = decrypt_key(config.encrypted_key)
        return config.provider, config.model_name, raw_key
    except Exception as e:
        logger.error(f"Failed to decrypt key for user {user_id}: {e}")
        return None

async def test_llm_connection(provider: str, model_name: str, api_key: str) -> dict[str, Any]:
    """Tests connectivity to user's LLM provider using LiteLLM."""
    try:
        model_ident = f"{provider}/{model_name}" if "/" not in model_name else model_name
        response = await litellm.acompletion(
            model=model_ident,
            messages=[{"role": "user", "content": "ping"}],
            api_key=api_key,
            max_tokens=5,
        )
        return {"status": "success", "response": response.choices[0].message.content}
    except Exception as e:
        logger.warning(f"LLM Test failed for {provider}/{model_name}: {e}")
        return {"status": "error", "message": str(e)}

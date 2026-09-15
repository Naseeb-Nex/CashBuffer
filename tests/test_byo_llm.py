import uuid

import pytest

from app.core.crypto import decrypt_key, encrypt_key
from app.services.llm import (
    get_user_active_llm_credentials,
    get_user_llm_config,
    mask_key,
    save_user_llm_config,
)


def test_encryption_decryption_roundtrip():
    raw_key = "sk-test-secret-api-key-12345"
    encrypted = encrypt_key(raw_key)
    assert encrypted != raw_key
    decrypted = decrypt_key(encrypted)
    assert decrypted == raw_key


def test_mask_key():
    assert mask_key("sk-1234567890abcdef") == "sk-1...cdef"
    assert mask_key("short") == "sk-****"
    assert mask_key("") == ""


@pytest.mark.asyncio
async def test_byo_llm_storage_and_retrieval(db_session):
    user_id = f"test_llm_user_{uuid.uuid4().hex[:8]}"
    raw_key = "sk-user-openai-key-9999"

    # Save LLM config
    await save_user_llm_config(
        db=db_session,
        user_id=user_id,
        provider="openai",
        model_name="gpt-4o",
        api_key=raw_key,
    )

    # Get config (should be masked)
    cfg = await get_user_llm_config(db_session, user_id)
    assert cfg is not None
    assert cfg["provider"] == "openai"
    assert cfg["model_name"] == "gpt-4o"
    assert cfg["masked_key"] != raw_key
    assert "..." in cfg["masked_key"]

    # Active credentials (in-memory decrypted)
    creds = await get_user_active_llm_credentials(db_session, user_id)
    assert creds is not None
    provider, model, decrypted_key = creds
    assert provider == "openai"
    assert model == "gpt-4o"
    assert decrypted_key == raw_key

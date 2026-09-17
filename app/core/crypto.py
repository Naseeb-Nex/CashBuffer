import functools

from cryptography.fernet import Fernet

from app.core.config import settings


@functools.lru_cache(maxsize=1)
def _get_cipher() -> Fernet:
    key = getattr(settings, "ENCRYPTION_KEY", "") or ""
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable is not configured.")
    return Fernet(key.encode("utf-8"))


def encrypt_key(plain_key: str) -> str:
    """Encrypts an LLM API key for secure database storage."""
    return _get_cipher().encrypt(plain_key.encode("utf-8")).decode("utf-8")


def decrypt_key(encrypted_key: str) -> str:
    """Decrypts an LLM API key for in-memory Agent usage."""
    return _get_cipher().decrypt(encrypted_key.encode("utf-8")).decode("utf-8")

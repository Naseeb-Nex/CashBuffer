from cryptography.fernet import Fernet

from app.core.config import settings

# Initialize the cipher suite with our environment key
# Expects a 32-byte url-safe base64-encoded string
_cipher = Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))


def encrypt_key(plain_key: str) -> str:
    """Encrypts an LLM API key for secure database storage."""
    return _cipher.encrypt(plain_key.encode("utf-8")).decode("utf-8")


def decrypt_key(encrypted_key: str) -> str:
    """Decrypts an LLM API key for in-memory Agent usage."""
    return _cipher.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")

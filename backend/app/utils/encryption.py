import os

from cryptography.fernet import Fernet

from app.config import settings

_key: bytes | None = None


def _get_or_create_key() -> bytes:
    if settings.encryption_key:
        return settings.encryption_key.encode()
    key_file = ".encryption_key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(key_file, "wb") as f:
        f.write(key)
    return key


def ensure_encryption_key():
    global _key
    _key = _get_or_create_key()


def encrypt(plaintext: str) -> str:
    if not _key:
        ensure_encryption_key()
    f = Fernet(_key)
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not _key:
        ensure_encryption_key()
    f = Fernet(_key)
    return f.decrypt(ciphertext.encode()).decode()

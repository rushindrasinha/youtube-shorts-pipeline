from cryptography.fernet import Fernet

from ..settings import settings

_fernet = None


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if key == "change-me-in-production":
            raise ValueError("ENCRYPTION_KEY not configured")
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a previously encrypted value."""
    return get_fernet().decrypt(ciphertext.encode()).decode()

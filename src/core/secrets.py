import os

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    key = os.getenv("APP_SECRET_KEY", "")
    if not key:
        raise RuntimeError(
            "APP_SECRET_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()

from src.core.secrets import decrypt, encrypt
from src.repositories._backends import get_user_backend

_backend = get_user_backend()


def _key(name: str) -> str:
    return f"secret:{name}"


def set_secret(user_id: str, name: str, plaintext: str) -> None:
    _backend.save(user_id, _key(name), encrypt(plaintext))


def has_secret(user_id: str, name: str) -> bool:
    return _backend.exists(user_id, _key(name))


def get_secret(user_id: str, name: str) -> str | None:
    ciphertext = _backend.get(user_id, _key(name))
    if ciphertext is None:
        return None
    return decrypt(ciphertext)


def clear_secret(user_id: str, name: str) -> None:
    _backend.delete(user_id, _key(name))

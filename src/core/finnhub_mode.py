import os
from typing import Literal

FinnhubKeyMode = Literal["global", "per_user"]


class MissingFinnhubKey(Exception):
    pass


def current_mode() -> FinnhubKeyMode:
    return os.getenv("FINNHUB_KEY_MODE", "global")  # type: ignore[return-value]


def resolve_api_key(user_id: str) -> str:
    mode = current_mode()
    if mode == "global":
        key = os.getenv("FINNHUB_API_KEY", "")
        if not key:
            raise MissingFinnhubKey("FINNHUB_API_KEY not set in .env")
        return key
    # per_user mode
    from src.repositories.user_secrets_repo import get_secret  # local import avoids circular
    key = get_secret(user_id, "finnhub_api_key")
    if not key:
        raise MissingFinnhubKey("請至設定頁設定您的 Finnhub API key")
    return key

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from src.repositories.chip_data_cache_repo import clear_chip_cache
from src.repositories.market_data_cache_repo import clear_market_cache
from src.repositories.news_cache_repo import clear_news_cache
from src.repositories.price_cache_repo import clear_price_cache

RepositoryClearer = Callable[[str], int]

_REPOSITORY_CLEARERS: dict[str, RepositoryClearer] = {
    "prices": clear_price_cache,
    "news": clear_news_cache,
    "chip_data": clear_chip_cache,
    "market_data": clear_market_cache,
}


def clear_all_caches(user_id: str = "local") -> dict[str, object]:
    """Clear Streamlit cache and repository-backed pickle caches."""
    st.cache_data.clear()
    repository_counts: dict[str, int] = {}
    for repo_name, clear_repo in _REPOSITORY_CLEARERS.items():
        repository_counts[repo_name] = sum(clear_repo(uid) for uid in _repository_user_ids(user_id))

    return {
        "streamlit": True,
        "repositories": repository_counts,
        "deleted_files": sum(repository_counts.values()),
    }


def _repository_user_ids(user_id: str) -> list[str]:
    ids = ["global"]
    if user_id and user_id not in ids:
        ids.append(user_id)
    return ids

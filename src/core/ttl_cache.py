import functools
import time


_all_stores: list[dict] = []


def clear_all_ttl_caches() -> None:
    for store in _all_stores:
        store.clear()


def ttl_cache(ttl_seconds: int):
    """In-process TTL memoization for functions with hashable arguments.

    Drop-in replacement for the st.cache_data(ttl=...) decorators that data
    fetchers used while the UI was a Streamlit app.
    """

    def decorator(fn):
        store: dict = {}
        _all_stores.append(store)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            hit = store.get(key)
            if hit is not None and now - hit[0] < ttl_seconds:
                return hit[1]
            value = fn(*args, **kwargs)
            store[key] = (now, value)
            return value

        wrapper.clear = store.clear  # parity with st.cache_data API used in tests
        return wrapper

    return decorator

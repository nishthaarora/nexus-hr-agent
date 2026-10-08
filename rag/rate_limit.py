import time

from fastapi import Header, HTTPException

from rag.exceptions import RateLimitedError

WINDOW_SECONDS = 60
MAX_REQUESTS_PER_KEY = 30       # coarse cap: total requests for this API key, across all sessions
MAX_REQUESTS_PER_SESSION = 10   # tighter cap: requests within a single conversation

# key -> (window_start_timestamp, count_in_window)
_api_key_windows: dict[str, tuple[float, int]] = {}
_session_windows: dict[str, tuple[float, int]] = {}


def _check_and_increment(store: dict[str, tuple[float, int]], key: str, limit: int, window_seconds: float) -> None:
    now = time.monotonic()
    window_start, count = store.get(key, (now, 0))

    if now - window_start > window_seconds:
        # previous window expired — start a fresh one
        store[key] = (now, 1)
        return

    if count >= limit:
        raise RateLimitedError(f"Rate limit exceeded ({limit} requests per {int(window_seconds)}s). Please slow down.")

    store[key] = (window_start, count + 1)


def enforce_api_key_rate_limit(x_api_key: str = Header(...)) -> None:
    """FastAPI dependency — caps total requests per API key, regardless of session.
    Raises HTTPException directly since dependencies run before your route's try/except."""
    try:
        _check_and_increment(_api_key_windows, x_api_key, MAX_REQUESTS_PER_KEY, WINDOW_SECONDS)
    except RateLimitedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


def enforce_session_rate_limit(session_id: str) -> None:
    """Plain function, not a dependency — call this manually inside /chat once session_id
    is resolved. Raises RateLimitedError directly, so it flows through the same
    try/except block you already use for Bedrock throttling and context-overflow errors."""
    _check_and_increment(_session_windows, session_id, MAX_REQUESTS_PER_SESSION, WINDOW_SECONDS)
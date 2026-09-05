"""
utils/timestamp.py — Consistent UTC timestamps across AutoCatcher.
Always UTC. Always the same format. Legal validity depends on it.
"""

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def now_str() -> str:
    """Human-readable UTC string:  2026-05-20 14:32:01 UTC"""
    return now_utc().strftime("%Y-%m-%d %H:%M:%S UTC")


def now_slug() -> str:
    """Filesystem-safe UTC slug for file names:  2026-05-20_143201"""
    return now_utc().strftime("%Y-%m-%d_%H%M%S")


def date_slug() -> str:
    """Date-only slug for case folder prefix:  2026-05-20"""
    return now_utc().strftime("%Y-%m-%d")

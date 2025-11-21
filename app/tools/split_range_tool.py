"""Utility to split a date/time range into smaller windows.

Returns list of (start_iso, end_iso) tuples.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple


def split_range(
    start_iso: str, end_iso: str, max_span_days: int = 7
) -> List[Tuple[str, str]]:
    """Split ISO date range into windows no larger than max_span_days.

    start_iso and end_iso expected in ISO 8601 date or datetime format.
    Returns list of (start_iso, end_iso) in ISO format (date portion if input dates).
    """
    if not start_iso or not end_iso:
        return []

    try:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)
    except Exception:
        # fallback: return single window
        return [(start_iso, end_iso)]

    if start_dt > end_dt:
        return []

    windows = []
    cur = start_dt
    max_span = timedelta(days=max_span_days)
    while cur < end_dt:
        nxt = min(cur + max_span, end_dt)
        windows.append((cur.isoformat(), nxt.isoformat()))
        cur = nxt

    return windows

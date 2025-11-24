from langchain.tools import tool
from typing import Optional


@tool
def split_range(start_time: str, end_time: str, interval_days: int = 7) -> str:
    """Split a time range into smaller intervals for detailed querying.

    Args:
        start_time: Start datetime string (YYYY-MM-DD HH:MM:SS)
        end_time: End datetime string (YYYY-MM-DD HH:MM:SS)
        interval_days: Days per interval (default: 7 for weekly)

    Returns:
        JSON string with list of time ranges
    """
    from datetime import datetime, timedelta
    import json

    start = datetime.fromisoformat(start_time.replace(" ", "T"))
    end = datetime.fromisoformat(end_time.replace(" ", "T"))

    intervals = []
    current = start

    while current < end:
        next_time = min(current + timedelta(days=interval_days), end)
        intervals.append(
            {
                "start": current.strftime("%Y-%m-%d %H:%M:%S"),
                "end": next_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        current = next_time

    return json.dumps({"intervals": intervals}, ensure_ascii=False)

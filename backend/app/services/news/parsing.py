"""Date parsing helpers shared by news provider adapters."""

import time
from datetime import datetime, timezone


def from_struct_time(parsed: time.struct_time | None) -> datetime | None:
    """Convert a feedparser `*_parsed` struct_time (UTC) to a datetime."""
    if not parsed:
        return None
    try:
        return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    except (OverflowError, ValueError, OSError):
        return None


def from_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp (tolerating a trailing 'Z')."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Normalize naive timestamps to UTC.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

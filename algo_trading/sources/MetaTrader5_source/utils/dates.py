from datetime import datetime, timezone
from typing import Optional, Union


def get_timestamp_ms(date: datetime) -> int:
    """Get the timestamp in ms

    Args:
        date (datetime): Datetime that will be converted

    Returns:
        int: Timestamp in ms
    """
    # Split datetime
    timestamp = str(date.timestamp())
    seconds, microseconds = timestamp.split(".")

    # Set the standard microseconds size
    microseconds = microseconds.ljust(6, "0")

    return int(seconds + microseconds)


def ts_s_to_dt_utc(ts: Optional[Union[int, float, str]]) -> Optional[datetime]:
    """Convert a Unix timestamp in seconds to a UTC-aware ``datetime``.

    Args:
        ts (Optional[Union[int, float, str]]): Timestamp in seconds. If a string is provided,
            it must be convertible to ``float``. ``None`` or falsy values return ``None``.

    Returns:
        Optional[datetime]: A timezone-aware ``datetime`` in UTC if ``ts`` is provided;
        otherwise ``None``.
    """
    return None if not ts else datetime.fromtimestamp(float(ts), tz=timezone.utc)

def ts_ms_to_dt_utc(ms: Optional[Union[int, float, str]]) -> Optional[datetime]: 
    """Convert a Unix timestamp in milliseconds to a UTC-aware ``datetime``.

    Args:
        ms (Optional[Union[int, float, str]]): Timestamp in milliseconds. If a string is provided,
            it must be convertible to ``float``. ``None`` or falsy values return ``None``.

    Returns:
        Optional[datetime]: A timezone-aware ``datetime`` in UTC if ``ms`` is provided;
        otherwise ``None``.
    """
    return None if not ms else datetime.fromtimestamp(float(ms) / 1000, tz=timezone.utc)
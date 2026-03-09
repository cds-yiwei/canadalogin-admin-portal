from typing import Tuple, Optional
import datetime as _dt


def normalize_date_range(from_date: Optional[str], to_date: Optional[str], max_range_days: int = 89) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Normalize incoming date strings.

    Accepts either epoch-ms strings (digits) or ISO date strings (YYYY-MM-DD).
    Returns (from_ms, to_ms, error_message). If normalization/validation fails, from_ms/to_ms may be None and
    error_message set.
    """
    from_ms = None
    to_ms = None
    error_message = None
    try:
        if from_date:
            if from_date.isdigit():
                from_ms = from_date
            else:
                d = _dt.datetime.fromisoformat(from_date)
                # start of day in local timezone
                dt_start = _dt.datetime(d.year, d.month, d.day, 0, 0, 0)
                from_ms = str(int(dt_start.timestamp() * 1000))
        if to_date:
            if to_date.isdigit():
                to_ms = to_date
            else:
                d = _dt.datetime.fromisoformat(to_date)
                # end of day in local timezone
                dt_end = _dt.datetime(d.year, d.month, d.day, 23, 59, 59, 999000)
                to_ms = str(int(dt_end.timestamp() * 1000))
        if from_ms and to_ms:
            f = int(from_ms)
            t = int(to_ms)
            if f > t:
                error_message = "Start date must be before or equal to end date"
            else:
                diff_days = (t - f) / (1000 * 60 * 60 * 24)
                if diff_days > max_range_days:
                    error_message = f"Please select a range of at most {max_range_days} days"
    except Exception:
        error_message = "Invalid date format"
    return from_ms if from_ms and not error_message else None, to_ms if to_ms and not error_message else None, error_message

"""UTC-safe time helpers used by services and UI."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def ensure_aware_utc(value: datetime) -> datetime:
    """Normalise a datetime to aware UTC.

    Naive input is rejected: silently guessing the local zone can make an
    authorization valid outside its real window.
    """

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含时区信息")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def to_db_time(value: datetime) -> str:
    return ensure_aware_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_db_time(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return ensure_aware_utc(parsed)


def local_display(value: datetime | str, with_seconds: bool = False) -> str:
    moment = from_db_time(value) if isinstance(value, str) else ensure_aware_utc(value)
    local = moment.astimezone()
    return local.strftime("%Y-%m-%d %H:%M:%S" if with_seconds else "%Y-%m-%d %H:%M")

"""Utility helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .errors import usage_error


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise usage_error(f"Invalid date format: {value}. Use YYYY-MM-DD.") from exc


def ensure_date_order(start: str, end: str) -> tuple[date, date]:
    start_date = parse_iso_date(start)
    end_date = parse_iso_date(end)
    if start_date > end_date:
        raise usage_error("The start date cannot be after the end date.")
    return start_date, end_date


def daterange(start: date, end: date) -> Iterable[date]:
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_in_timezone(timezone_name: str) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


def json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return json_ready(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_ready(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def stable_json_dumps(value: Any, *, indent: int = 2) -> str:
    return json.dumps(json_ready(value), indent=indent, sort_keys=True)


def parse_fields(raw: str | None) -> list[str]:
    if raw is None:
        return []
    fields = [field.strip() for field in raw.split(",") if field.strip()]
    return fields


def select_fields(data: Any, fields: list[str]) -> Any:
    if not fields:
        return data
    if isinstance(data, list):
        return [select_fields(item, fields) for item in data]
    if not isinstance(data, dict):
        return data

    selected: dict[str, Any] = {}
    for field in fields:
        current = data
        parts = field.split(".")
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current is None:
            continue

        target = selected
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = current
    return selected


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

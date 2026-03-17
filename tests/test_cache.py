from __future__ import annotations

from pathlib import Path

from garmin_cli.cache import CacheBackend


def test_daily_roundtrip_and_stats(tmp_path: Path) -> None:
    cache = CacheBackend(tmp_path / "cache.db")
    cache.set_daily("2026-03-16", "sleep", {"score": 90}, "2026-03-16T07:00:00+00:00")

    record = cache.get_daily("2026-03-16", "sleep")
    assert record is not None
    assert record.data == {"score": 90}

    stats = cache.stats()
    assert stats["tables"]["daily_cache"] == 1
    assert stats["daily_metric_breakdown"]["sleep"] == 1


def test_clear_by_metric_and_before(tmp_path: Path) -> None:
    cache = CacheBackend(tmp_path / "cache.db")
    cache.set_daily("2026-03-10", "sleep", {"score": 80}, "2026-03-10T07:00:00+00:00")
    cache.set_daily("2026-03-16", "hrv", {"value": 70}, "2026-03-16T07:00:00+00:00")
    cache.set_activity_summary("1", "2026-03-10", "running", {"activityId": 1}, "2026-03-10T08:00:00+00:00")
    cache.set_activity_detail("1", "details", {"activityId": 1}, "2026-03-10T08:05:00+00:00")
    cache.set_range("steps:2026-03-01:2026-03-10", [{"calendarDate": "2026-03-10"}], "2026-03-10T09:00:00+00:00")

    deleted = cache.clear(metric="hrv")
    assert deleted["daily_cache"] == 1
    assert cache.get_daily("2026-03-16", "hrv") is None

    deleted = cache.clear(before="2026-03-12")
    assert deleted["daily_cache"] == 1
    assert deleted["activity_cache"] == 1
    assert deleted["activity_detail_cache"] == 1
    assert deleted["range_cache"] == 1
    assert cache.get_range("steps:2026-03-01:2026-03-10") is None

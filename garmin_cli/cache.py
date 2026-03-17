"""SQLite cache implementation."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class CacheRecord:
    data: Any
    fetched_at: str


class CacheBackend:
    """Small SQLite cache for immutable Garmin history."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS daily_cache (
                    date TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    data TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (date, metric)
                );

                CREATE TABLE IF NOT EXISTS activity_cache (
                    activity_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    type TEXT,
                    summary TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_detail_cache (
                    activity_id TEXT NOT NULL,
                    detail_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (activity_id, detail_type)
                );

                CREATE TABLE IF NOT EXISTS range_cache (
                    cache_key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_cache(date);
                CREATE INDEX IF NOT EXISTS idx_daily_metric ON daily_cache(metric, date);
                CREATE INDEX IF NOT EXISTS idx_activity_date ON activity_cache(date);
                """
            )

    def get_daily(self, cdate: str, metric: str) -> CacheRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data, fetched_at FROM daily_cache WHERE date = ? AND metric = ?",
                (cdate, metric),
            ).fetchone()
        if row is None:
            return None
        return CacheRecord(data=json.loads(row["data"]), fetched_at=row["fetched_at"])

    def set_daily(self, cdate: str, metric: str, data: Any, fetched_at: str) -> None:
        payload = json.dumps(data, sort_keys=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO daily_cache (date, metric, data, fetched_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date, metric)
                DO UPDATE SET data = excluded.data, fetched_at = excluded.fetched_at
                """,
                (cdate, metric, payload, fetched_at),
            )

    def get_activity_summary(
        self, activity_id: str, *, cache_source: str | None = None
    ) -> CacheRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary, fetched_at, type FROM activity_cache WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()
        if row is None:
            return None
        if cache_source is not None:
            raw_type = row["type"] or ""
            if not raw_type.startswith(f"{cache_source}:"):
                return None
        return CacheRecord(data=json.loads(row["summary"]), fetched_at=row["fetched_at"])

    def set_activity_summary(
        self,
        activity_id: str,
        activity_date: str,
        activity_type: str | None,
        summary: Any,
        fetched_at: str,
        *,
        cache_source: str = "activity",
    ) -> None:
        payload = json.dumps(summary, sort_keys=True)
        stored_type = f"{cache_source}:{activity_type or ''}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO activity_cache (activity_id, date, type, summary, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(activity_id)
                DO UPDATE SET
                    date = excluded.date,
                    type = excluded.type,
                    summary = excluded.summary,
                    fetched_at = excluded.fetched_at
                """,
                (activity_id, activity_date, stored_type, payload, fetched_at),
            )

    def get_activity_detail(self, activity_id: str, detail_type: str) -> CacheRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT data, fetched_at
                FROM activity_detail_cache
                WHERE activity_id = ? AND detail_type = ?
                """,
                (activity_id, detail_type),
            ).fetchone()
        if row is None:
            return None
        return CacheRecord(data=json.loads(row["data"]), fetched_at=row["fetched_at"])

    def set_activity_detail(
        self, activity_id: str, detail_type: str, data: Any, fetched_at: str
    ) -> None:
        payload = json.dumps(data, sort_keys=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO activity_detail_cache (activity_id, detail_type, data, fetched_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(activity_id, detail_type)
                DO UPDATE SET data = excluded.data, fetched_at = excluded.fetched_at
                """,
                (activity_id, detail_type, payload, fetched_at),
            )

    def get_range(self, cache_key: str) -> CacheRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data, fetched_at FROM range_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if row is None:
            return None
        return CacheRecord(data=json.loads(row["data"]), fetched_at=row["fetched_at"])

    def set_range(self, cache_key: str, data: Any, fetched_at: str) -> None:
        payload = json.dumps(data, sort_keys=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO range_cache (cache_key, data, fetched_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key)
                DO UPDATE SET data = excluded.data, fetched_at = excluded.fetched_at
                """,
                (cache_key, payload, fetched_at),
            )

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            totals = {
                "daily_cache": conn.execute("SELECT COUNT(*) FROM daily_cache").fetchone()[0],
                "activity_cache": conn.execute("SELECT COUNT(*) FROM activity_cache").fetchone()[0],
                "activity_detail_cache": conn.execute(
                    "SELECT COUNT(*) FROM activity_detail_cache"
                ).fetchone()[0],
                "range_cache": conn.execute("SELECT COUNT(*) FROM range_cache").fetchone()[0],
            }
            metric_rows = conn.execute(
                "SELECT metric, COUNT(*) AS count FROM daily_cache GROUP BY metric ORDER BY metric"
            ).fetchall()
            fetched_rows = conn.execute(
                """
                SELECT MIN(fetched_at) AS oldest_entry, MAX(fetched_at) AS newest_entry
                FROM (
                    SELECT fetched_at FROM daily_cache
                    UNION ALL SELECT fetched_at FROM activity_cache
                    UNION ALL SELECT fetched_at FROM activity_detail_cache
                    UNION ALL SELECT fetched_at FROM range_cache
                )
                """
            ).fetchone()
        return {
            "database_path": str(self.db_path),
            "database_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "tables": totals,
            "oldest_entry": fetched_rows["oldest_entry"],
            "newest_entry": fetched_rows["newest_entry"],
            "daily_metric_breakdown": {
                row["metric"]: row["count"] for row in metric_rows
            },
        }

    def clear(self, *, before: str | None = None, metric: str | None = None) -> dict[str, int]:
        deleted = {"daily_cache": 0, "activity_cache": 0, "activity_detail_cache": 0, "range_cache": 0}
        with self._connect() as conn:
            if metric is not None:
                cursor = conn.execute(
                    "DELETE FROM daily_cache WHERE metric = ?",
                    (metric,),
                )
                deleted["daily_cache"] = cursor.rowcount
                return deleted

            if before is not None:
                activity_ids = [
                    row["activity_id"]
                    for row in conn.execute(
                        "SELECT activity_id FROM activity_cache WHERE date < ?",
                        (before,),
                    ).fetchall()
                ]
                cursor = conn.execute("DELETE FROM daily_cache WHERE date < ?", (before,))
                deleted["daily_cache"] = cursor.rowcount
                cursor = conn.execute("DELETE FROM activity_cache WHERE date < ?", (before,))
                deleted["activity_cache"] = cursor.rowcount
                if activity_ids:
                    placeholders = ",".join("?" for _ in activity_ids)
                    cursor = conn.execute(
                        f"DELETE FROM activity_detail_cache WHERE activity_id IN ({placeholders})",
                        activity_ids,
                    )
                    deleted["activity_detail_cache"] = cursor.rowcount
                # Range cache keys do not carry structured date metadata, so the
                # safest selective prune is to invalidate them all when a
                # date-based clear is requested.
                cursor = conn.execute("DELETE FROM range_cache")
                deleted["range_cache"] = cursor.rowcount
                return deleted

            for table in deleted:
                cursor = conn.execute(f"DELETE FROM {table}")
                deleted[table] = cursor.rowcount
        return deleted

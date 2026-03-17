"""Garmin service layer with cache integration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from garminconnect import Garmin
from garth.data import GarminScoresData

from .auth import AuthManager
from .cache import CacheBackend
from .config import AppConfig
from .errors import GarminCliError, map_exception, usage_error
from .utils import daterange, ensure_date_order, json_ready, parse_iso_date, today_in_timezone, utcnow_iso


DAY_METRICS = {
    "sleep",
    "heart_rate",
    "hrv",
    "stress",
    "respiration",
    "spo2",
    "training_readiness",
    "training_status",
    "vo2max",
    "fitness_age",
    "user_summary",
    "endurance_score",
    "body_battery",
}


@dataclass(slots=True)
class ServiceOptions:
    no_cache: bool = False
    refresh: bool = False


@dataclass(slots=True)
class FetchResult:
    data: Any
    metadata: dict[str, Any]


class GarminService:
    """High-level Garmin operations for the CLI."""

    def __init__(
        self,
        *,
        auth: AuthManager,
        cache: CacheBackend,
        config: AppConfig,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.auth = auth
        self.cache = cache
        self.config = config
        self.sleep_fn = sleep_fn
        self._client: Garmin | None = None

    def _sdk(self) -> Garmin:
        if self._client is None:
            self._client = self.auth.load_client()
        return self._client

    def _today(self) -> date:
        return today_in_timezone(self.config.timezone)

    def _metadata(self, *, cached: bool, fetched_at: str, **extra: Any) -> dict[str, Any]:
        metadata = {"cached": cached, "fetched_at": fetched_at}
        metadata.update({key: value for key, value in extra.items() if value is not None})
        return metadata

    def _invoke(self, operation: Callable[[Garmin], Any]) -> Any:
        delays = (2, 5, 15)
        for attempt in range(len(delays) + 1):
            try:
                return json_ready(operation(self._sdk()))
            except Exception as exc:
                mapped = map_exception(exc)
                if mapped.code == "RATE_LIMITED" and attempt < len(delays):
                    self.sleep_fn(delays[attempt])
                    continue
                raise mapped from exc

    def _is_finalized_day(self, cdate: str) -> bool:
        return parse_iso_date(cdate) < self._today()

    def _can_read_day_cache(self, cdate: str, options: ServiceOptions) -> bool:
        if options.no_cache or options.refresh:
            return False
        return self._is_finalized_day(cdate)

    def _should_write_day_cache(self, cdate: str, options: ServiceOptions) -> bool:
        return not options.no_cache and self._is_finalized_day(cdate)

    def _is_finalized_cached_day_record(self, cdate: str, fetched_at: str) -> bool:
        requested_date = parse_iso_date(cdate)
        try:
            fetched_dt = datetime.fromisoformat(fetched_at)
        except ValueError:
            return False
        if fetched_dt.tzinfo is None:
            fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
        fetched_local_date = fetched_dt.astimezone(ZoneInfo(self.config.timezone)).date()
        return fetched_local_date > requested_date

    def _fetch_day(
        self,
        metric: str,
        cdate: str,
        options: ServiceOptions,
        fetcher: Callable[[Garmin, str], Any],
    ) -> FetchResult:
        parse_iso_date(cdate)
        if self._can_read_day_cache(cdate, options):
            cached = self.cache.get_daily(cdate, metric)
            if cached is not None and self._is_finalized_cached_day_record(cdate, cached.fetched_at):
                metadata = self._metadata(
                    cached=True,
                    fetched_at=cached.fetched_at,
                    date=cdate,
                )
                if cached.data is None:
                    metadata["note"] = "No data for this date."
                return FetchResult(cached.data, metadata)

        data = self._invoke(lambda client: fetcher(client, cdate))
        fetched_at = utcnow_iso()
        if self._should_write_day_cache(cdate, options):
            self.cache.set_daily(cdate, metric, data, fetched_at)
        metadata = self._metadata(cached=False, fetched_at=fetched_at, date=cdate)
        if data is None:
            metadata["note"] = "No data for this date."
        return FetchResult(data, metadata)

    def _fetch_range(
        self,
        cache_key: str,
        options: ServiceOptions,
        fetcher: Callable[[Garmin], Any],
        *,
        cacheable: bool,
        **metadata: Any,
    ) -> FetchResult:
        if cacheable and not options.no_cache and not options.refresh:
            cached = self.cache.get_range(cache_key)
            if cached is not None:
                return FetchResult(
                    cached.data,
                    self._metadata(cached=True, fetched_at=cached.fetched_at, **metadata),
                )

        data = self._invoke(fetcher)
        fetched_at = utcnow_iso()
        if cacheable and not options.no_cache:
            self.cache.set_range(cache_key, data, fetched_at)
        return FetchResult(
            data,
            self._metadata(cached=False, fetched_at=fetched_at, **metadata),
        )

    def login(self, email: str | None, password: str | None) -> FetchResult:
        data = self.auth.login(email=email, password=password)
        return FetchResult(data, self._metadata(cached=False, fetched_at=utcnow_iso()))

    def status(self) -> FetchResult:
        data = self.auth.status()
        data["cache"] = self.cache.stats()
        return FetchResult(data, self._metadata(cached=False, fetched_at=utcnow_iso()))

    def sleep(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day("sleep", cdate, options, lambda client, day: client.get_sleep_data(day))

    def heart_rate(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day(
            "heart_rate", cdate, options, lambda client, day: client.get_heart_rates(day)
        )

    def hrv(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day("hrv", cdate, options, lambda client, day: client.get_hrv_data(day))

    def stress(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day(
            "stress", cdate, options, lambda client, day: client.get_stress_data(day)
        )

    def respiration(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day(
            "respiration",
            cdate,
            options,
            lambda client, day: client.get_respiration_data(day),
        )

    def spo2(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day("spo2", cdate, options, lambda client, day: client.get_spo2_data(day))

    def training_readiness(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day(
            "training_readiness",
            cdate,
            options,
            lambda client, day: client.get_morning_training_readiness(day)
            or client.get_training_readiness(day),
        )

    def training_status(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day(
            "training_status",
            cdate,
            options,
            lambda client, day: client.get_training_status(day),
        )

    def vo2max(self, cdate: str, options: ServiceOptions) -> FetchResult:
        def fetch(client: Garmin, day: str) -> Any:
            scores = GarminScoresData.get(day, client=client.garth)
            if scores is None:
                return None
            return {
                "calendar_date": scores.calendar_date,
                "vo2max": scores.vo_2_max,
                "vo2max_precise": scores.vo_2_max_precise_value,
                "endurance_score": scores.endurance_score,
            }

        return self._fetch_day("vo2max", cdate, options, fetch)

    def endurance_score(self, start: str, end: str | None, options: ServiceOptions) -> FetchResult:
        if end is None:
            return self._fetch_day(
                "endurance_score",
                start,
                options,
                lambda client, day: client.get_endurance_score(day),
            )
        _, end_date = ensure_date_order(start, end)
        cacheable = end_date < self._today()
        cache_key = f"endurance_score:{start}:{end}"
        return self._fetch_range(
            cache_key,
            options,
            lambda client: client.get_endurance_score(start, end),
            cacheable=cacheable,
            start=start,
            end=end,
        )

    def fitness_age(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day(
            "fitness_age",
            cdate,
            options,
            lambda client, day: client.get_fitnessage_data(day),
        )

    def user_summary(self, cdate: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_day(
            "user_summary",
            cdate,
            options,
            lambda client, day: client.get_user_summary(day),
        )

    def steps(self, start: str, end: str, options: ServiceOptions) -> FetchResult:
        _, end_date = ensure_date_order(start, end)
        cacheable = end_date < self._today()
        cache_key = f"steps:{start}:{end}"
        return self._fetch_range(
            cache_key,
            options,
            lambda client: client.get_daily_steps(start, end),
            cacheable=cacheable,
            start=start,
            end=end,
        )

    def body_composition(self, start: str, end: str | None, options: ServiceOptions) -> FetchResult:
        end = end or start
        _, end_date = ensure_date_order(start, end)
        cacheable = end_date < self._today()
        cache_key = f"body_composition:{start}:{end}"
        return self._fetch_range(
            cache_key,
            options,
            lambda client: client.get_body_composition(start, end),
            cacheable=cacheable,
            start=start,
            end=end,
        )

    def weigh_ins(self, start: str, end: str, options: ServiceOptions) -> FetchResult:
        _, end_date = ensure_date_order(start, end)
        cacheable = end_date < self._today()
        cache_key = f"weigh_ins:{start}:{end}"
        return self._fetch_range(
            cache_key,
            options,
            lambda client: client.get_weigh_ins(start, end),
            cacheable=cacheable,
            start=start,
            end=end,
        )

    def race_predictions(
        self,
        *,
        start: str | None,
        end: str | None,
        latest: bool,
        options: ServiceOptions,
    ) -> FetchResult:
        if latest or (start is None and end is None):
            data = self._invoke(lambda client: client.get_race_predictions())
            return FetchResult(data, self._metadata(cached=False, fetched_at=utcnow_iso(), latest=True))
        if not start or not end:
            raise usage_error("Use both --start and --end for historical race predictions.")
        _, end_date = ensure_date_order(start, end)
        cache_key = f"race_predictions:{start}:{end}"
        return self._fetch_range(
            cache_key,
            options,
            lambda client: client.get_race_predictions(start, end, "daily"),
            cacheable=end_date < self._today(),
            start=start,
            end=end,
        )

    def personal_records(self) -> FetchResult:
        data = self._invoke(lambda client: client.get_personal_record())
        return FetchResult(data, self._metadata(cached=False, fetched_at=utcnow_iso()))

    def _extract_activity_date(self, payload: dict[str, Any]) -> str:
        for key in ("activityDate", "startTimeLocal", "beginTimestamp"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value.split(" ")[0].split("T")[0]
        return self._today().isoformat()

    def _extract_activity_type(self, payload: dict[str, Any]) -> str | None:
        for key in ("activityType", "activityTypeDTO", "activityTypeDetails"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value.get("typeKey") or value.get("type") or value.get("key")
        value = payload.get("activityType")
        if isinstance(value, str):
            return value
        return None

    def activities(
        self,
        *,
        start: str | None,
        end: str | None,
        activity_type: str | None,
        limit: int,
        options: ServiceOptions,
    ) -> FetchResult:
        if end and not start:
            raise usage_error("`--end` requires `--start`.")

        if start:
            end = end or self._today().isoformat()
            _, end_date = ensure_date_order(start, end)
            cache_key = f"activities:{start}:{end}:{activity_type or 'all'}:{limit}"
            result = self._fetch_range(
                cache_key,
                options,
                lambda client: client.connectapi(
                    "/activitylist-service/activities/search/activities",
                    params={
                        "startDate": start,
                        "endDate": end,
                        "start": "0",
                        "limit": str(limit),
                        **({"activityType": activity_type} if activity_type else {}),
                    },
                ),
                cacheable=end_date < self._today(),
                start=start,
                end=end,
                activity_type=activity_type,
                limit=limit,
            )
        else:
            data = self._invoke(
                lambda client: client.get_activities(start=0, limit=limit, activitytype=activity_type)
            )
            result = FetchResult(
                data,
                self._metadata(
                    cached=False,
                    fetched_at=utcnow_iso(),
                    activity_type=activity_type,
                    limit=limit,
                ),
            )

        return result

    def activity(self, activity_id: str, options: ServiceOptions) -> FetchResult:
        if not options.no_cache and not options.refresh:
            cached = self.cache.get_activity_summary(activity_id, cache_source="activity")
            if cached is not None:
                return FetchResult(
                    cached.data,
                    self._metadata(cached=True, fetched_at=cached.fetched_at, activity_id=activity_id),
                )

        data = self._invoke(lambda client: client.get_activity(activity_id))
        fetched_at = utcnow_iso()
        if not options.no_cache and isinstance(data, dict):
            self.cache.set_activity_summary(
                activity_id,
                self._extract_activity_date(data),
                self._extract_activity_type(data),
                data,
                fetched_at,
                cache_source="activity",
            )
        return FetchResult(
            data,
            self._metadata(cached=False, fetched_at=fetched_at, activity_id=activity_id),
        )

    def _fetch_activity_detail(
        self,
        activity_id: str,
        detail_type: str,
        options: ServiceOptions,
        fetcher: Callable[[Garmin], Any],
    ) -> FetchResult:
        if not options.no_cache and not options.refresh:
            cached = self.cache.get_activity_detail(activity_id, detail_type)
            if cached is not None:
                return FetchResult(
                    cached.data,
                    self._metadata(
                        cached=True,
                        fetched_at=cached.fetched_at,
                        activity_id=activity_id,
                        detail_type=detail_type,
                    ),
                )

        data = self._invoke(fetcher)
        fetched_at = utcnow_iso()
        if not options.no_cache:
            self.cache.set_activity_detail(activity_id, detail_type, data, fetched_at)
        return FetchResult(
            data,
            self._metadata(
                cached=False,
                fetched_at=fetched_at,
                activity_id=activity_id,
                detail_type=detail_type,
            ),
        )

    def activity_details(self, activity_id: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_activity_detail(
            activity_id,
            "details",
            options,
            lambda client: client.get_activity_details(activity_id),
        )

    def activity_splits(self, activity_id: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_activity_detail(
            activity_id,
            "splits",
            options,
            lambda client: {
                "splits": client.get_activity_splits(activity_id),
                "summaries": client.get_activity_split_summaries(activity_id),
            },
        )

    def activity_hr_zones(self, activity_id: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_activity_detail(
            activity_id,
            "hr_zones",
            options,
            lambda client: client.get_activity_hr_in_timezones(activity_id),
        )

    def activity_weather(self, activity_id: str, options: ServiceOptions) -> FetchResult:
        return self._fetch_activity_detail(
            activity_id,
            "weather",
            options,
            lambda client: client.get_activity_weather(activity_id),
        )

    def body_battery(self, start: str, end: str | None, options: ServiceOptions) -> FetchResult:
        end = end or start
        start_date, end_date = ensure_date_order(start, end)
        requested_days = [day.isoformat() for day in daterange(start_date, end_date)]
        use_cache = not options.no_cache and not options.refresh
        fetched_at = utcnow_iso()

        cached_days: dict[str, Any] = {}
        missing_days: list[str] = []
        for current_day in requested_days:
            if use_cache and parse_iso_date(current_day) < self._today():
                cached = self.cache.get_daily(current_day, "body_battery")
                if cached is not None and self._is_finalized_cached_day_record(
                    current_day, cached.fetched_at
                ):
                    cached_days[current_day] = cached.data
                    continue
            missing_days.append(current_day)

        if missing_days:
            fresh_payload = self._invoke(
                lambda client: client.get_body_battery(missing_days[0], missing_days[-1])
            )
            daily_map = {
                (entry.get("calendarDate") or missing_days[index]): entry
                for index, entry in enumerate(fresh_payload or [])
            }
            for current_day in missing_days:
                assembled = {
                    "summary": daily_map.get(current_day),
                    "events": self._invoke(
                        lambda client, day=current_day: client.get_body_battery_events(day)
                    ),
                    "intraday": self._invoke(
                        lambda client, day=current_day: client.get_all_day_stress(day)
                    ),
                }
                cached_days[current_day] = assembled
                if self._should_write_day_cache(current_day, options):
                    self.cache.set_daily(current_day, "body_battery", assembled, fetched_at)

        ordered = [{"date": day, **(cached_days[day] or {})} for day in requested_days]
        return FetchResult(
            ordered,
            self._metadata(
                cached=use_cache and not missing_days,
                fetched_at=fetched_at if missing_days else self.cache.get_daily(requested_days[0], "body_battery").fetched_at,
                start=start,
                end=end,
            ),
        )

    def gear(self, options: ServiceOptions) -> FetchResult:
        cache_key = "gear:all"
        if not options.no_cache and not options.refresh:
            cached = self.cache.get_range(cache_key)
            if cached is not None:
                return FetchResult(
                    cached.data,
                    self._metadata(cached=True, fetched_at=cached.fetched_at),
                )

        def fetch(client: Garmin) -> Any:
            profile = client.get_user_profile()
            profile_pk = (
                profile.get("userProfilePK")
                or profile.get("userProfilePk")
                or profile.get("id")
                or profile.get("userData", {}).get("userProfilePk")
                or profile.get("profileId")
            )
            if profile_pk is None:
                raise usage_error("Unable to determine the Garmin user profile id for gear queries.")
            return client.get_gear(str(profile_pk))

        data = self._invoke(fetch)
        fetched_at = utcnow_iso()
        if not options.no_cache:
            self.cache.set_range(cache_key, data, fetched_at)
        return FetchResult(data, self._metadata(cached=False, fetched_at=fetched_at))

    def gear_stats(self, gear_uuid: str, options: ServiceOptions) -> FetchResult:
        cache_key = f"gear_stats:{gear_uuid}"
        if not options.no_cache and not options.refresh:
            cached = self.cache.get_range(cache_key)
            if cached is not None:
                return FetchResult(
                    cached.data,
                    self._metadata(cached=True, fetched_at=cached.fetched_at, gear_uuid=gear_uuid),
                )

        data = self._invoke(
            lambda client: {
                "stats": client.get_gear_stats(gear_uuid),
                "activities": client.get_gear_activities(gear_uuid),
            }
        )
        fetched_at = utcnow_iso()
        if not options.no_cache:
            self.cache.set_range(cache_key, data, fetched_at)
        return FetchResult(
            data,
            self._metadata(cached=False, fetched_at=fetched_at, gear_uuid=gear_uuid),
        )

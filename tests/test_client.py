from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from freezegun import freeze_time

from garmin_cli.cache import CacheBackend
from garmin_cli.client import GarminService, ServiceOptions
from garmin_cli.config import AppConfig


@dataclass
class FakeAuth:
    client: object

    def load_client(self) -> object:
        return self.client


class FakeSdk:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.garth = None
        self.sleep_payload = {"calendarDate": "2026-03-16", "score": 90}

    def get_sleep_data(self, day: str) -> dict:
        self.calls.append(("get_sleep_data", (day,), {}))
        payload = dict(self.sleep_payload)
        payload["calendarDate"] = day
        return payload

    def connectapi(self, path: str, params: dict | None = None) -> list[dict]:
        self.calls.append(("connectapi", (path,), {"params": params or {}}))
        return [{"activityId": 1, "activityDate": params["startDate"]}]

    def get_activities(self, start: int = 0, limit: int = 20, activitytype: str | None = None) -> list[dict]:
        self.calls.append(("get_activities", (start, limit, activitytype), {}))
        return [{"activityId": 1, "activityDate": "2026-03-10", "activityName": "List summary"}]

    def get_activity(self, activity_id: str) -> dict:
        self.calls.append(("get_activity", (activity_id,), {}))
        return {"activityId": int(activity_id), "activityName": "Detailed activity", "summaryDTO": {"distance": 1000}}

    def get_body_battery(self, start: str, end: str) -> list[dict]:
        self.calls.append(("get_body_battery", (start, end), {}))
        if start == end:
            return [{"calendarDate": start, "chargedValue": 80}]
        return [{"calendarDate": start, "chargedValue": 80}, {"calendarDate": end, "chargedValue": 55}]

    def get_body_battery_events(self, day: str) -> list[dict]:
        self.calls.append(("get_body_battery_events", (day,), {}))
        return [{"event": "sleep"}]

    def get_all_day_stress(self, day: str) -> dict:
        self.calls.append(("get_all_day_stress", (day,), {}))
        return {"bodyBatteryValuesArray": [80, 79]}

    def get_user_profile(self) -> dict:
        self.calls.append(("get_user_profile", tuple(), {}))
        return {"id": 1234, "userData": {}}

    def get_gear(self, user_profile_number: str) -> dict:
        self.calls.append(("get_gear", (user_profile_number,), {}))
        return {"gear": [{"uuid": "shoe-1"}]}


def build_service(tmp_path: Path, sdk: FakeSdk) -> GarminService:
    return GarminService(
        auth=FakeAuth(sdk),
        cache=CacheBackend(tmp_path / "cache.db"),
        config=AppConfig(timezone="UTC", cache_dir=str(tmp_path)),
        sleep_fn=lambda _: None,
    )


def test_past_daily_data_uses_cache(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    options = ServiceOptions()

    with freeze_time("2026-03-17T08:00:00Z"):
        first = service.sleep("2026-03-16", options)
        second = service.sleep("2026-03-16", options)

    assert first.metadata["cached"] is False
    assert second.metadata["cached"] is True
    assert sdk.calls.count(("get_sleep_data", ("2026-03-16",), {})) == 1


def test_today_daily_data_bypasses_cache(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    options = ServiceOptions()

    with freeze_time("2026-03-16T08:00:00Z"):
        service.sleep("2026-03-16", options)
        service.sleep("2026-03-16", options)

    assert sdk.calls.count(("get_sleep_data", ("2026-03-16",), {})) == 2


def test_today_daily_data_is_not_reused_as_final_history(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    options = ServiceOptions()

    with freeze_time("2026-03-16T08:00:00Z"):
        service.sleep("2026-03-16", options)

    with freeze_time("2026-03-17T08:00:00Z"):
        first_yesterday = service.sleep("2026-03-16", options)
        second_yesterday = service.sleep("2026-03-16", options)

    assert sdk.calls.count(("get_sleep_data", ("2026-03-16",), {})) == 2
    assert first_yesterday.metadata["cached"] is False
    assert second_yesterday.metadata["cached"] is True


def test_activities_uses_search_endpoint_for_date_ranges(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    options = ServiceOptions()

    with freeze_time("2026-03-20T08:00:00Z"):
        result = service.activities(
            start="2026-03-10",
            end="2026-03-12",
            activity_type="running",
            limit=5,
            options=options,
        )

    assert result.data[0]["activityId"] == 1
    path_call = next(call for call in sdk.calls if call[0] == "connectapi")
    assert path_call[1][0] == "/activitylist-service/activities/search/activities"
    assert path_call[2]["params"]["limit"] == "5"
    assert path_call[2]["params"]["activityType"] == "running"


def test_body_battery_combines_summary_events_and_intraday(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    options = ServiceOptions()

    with freeze_time("2026-03-20T08:00:00Z"):
        result = service.body_battery("2026-03-18", None, options)

    assert result.data[0]["summary"]["chargedValue"] == 80
    assert result.data[0]["events"][0]["event"] == "sleep"
    assert "bodyBatteryValuesArray" in result.data[0]["intraday"]


def test_body_battery_does_not_cache_same_day_snapshot_as_final(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    options = ServiceOptions()

    with freeze_time("2026-03-20T08:00:00Z"):
        service.body_battery("2026-03-20", None, options)

    with freeze_time("2026-03-21T08:00:00Z"):
        first = service.body_battery("2026-03-20", None, options)
        second = service.body_battery("2026-03-20", None, options)

    assert sdk.calls.count(("get_body_battery", ("2026-03-20", "2026-03-20"), {})) == 2
    assert first.metadata["cached"] is False
    assert second.metadata["cached"] is True


def test_activity_fetch_ignores_cached_list_summary(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    options = ServiceOptions()

    service.activities(start=None, end=None, activity_type=None, limit=5, options=options)
    first = service.activity("1", options)
    second = service.activity("1", options)

    assert first.data["activityName"] == "Detailed activity"
    assert "summaryDTO" in first.data
    assert first.metadata["cached"] is False
    assert second.metadata["cached"] is True
    assert sdk.calls.count(("get_activity", ("1",), {})) == 1


def test_gear_uses_profile_id_fallback(tmp_path: Path) -> None:
    sdk = FakeSdk()
    service = build_service(tmp_path, sdk)
    result = service.gear(ServiceOptions())
    assert result.data["gear"][0]["uuid"] == "shoe-1"
    assert ("get_gear", ("1234",), {}) in sdk.calls

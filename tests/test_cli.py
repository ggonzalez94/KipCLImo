from __future__ import annotations

import json
from pathlib import Path

import pytest

from garmin_cli.cache import CacheBackend
from garmin_cli.cli import app
from garmin_cli.client import FetchResult
from garmin_cli.config import AppConfig
from garmin_cli.errors import general_error
from garmin_cli.schema import SchemaRegistry
from garmin_cli.state import AppState, GlobalOptions


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def sleep(self, day: str, options) -> FetchResult:
        self.calls.append(("sleep", (day,), {"options": options}))
        return FetchResult({"calendarDate": day, "score": 91}, {"cached": False, "fetched_at": "now"})

    def activities(self, **kwargs) -> FetchResult:
        self.calls.append(("activities", tuple(), kwargs))
        return FetchResult([{"activityId": 1}], {"cached": False, "fetched_at": "now"})

    def personal_records(self) -> FetchResult:
        self.calls.append(("personal-records", tuple(), {}))
        return FetchResult({"records": []}, {"cached": False, "fetched_at": "now"})

    def status(self) -> FetchResult:
        return FetchResult({"authenticated": True}, {"cached": False, "fetched_at": "now"})


class FakeAuth:
    pass


def build_fake_state(tmp_path: Path, registry, service: FakeService) -> AppState:
    state = AppState(
        options=GlobalOptions(output="json", no_cache=False, refresh=False, fields=[], verbose=False),
        config=AppConfig(timezone="UTC", cache_dir=str(tmp_path)),
        cache=CacheBackend(tmp_path / "cache.db"),
        auth=FakeAuth(),
        registry=registry,
    )
    state._service = service
    return state


def test_schema_command_lists_registered_commands(runner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import garmin_cli.cli as cli_module

    service = FakeService()
    monkeypatch.setattr(cli_module, "build_state", lambda options, registry: build_fake_state(tmp_path, registry, service))
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "sleep" in payload["data"]["commands"]
    assert "activities" in payload["data"]["commands"]


def test_schema_unknown_command_is_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    import garmin_cli.cli as cli_module
    import sys

    service = FakeService()
    monkeypatch.setattr(cli_module, "build_state", lambda options, registry: build_fake_state(tmp_path, registry, service))
    monkeypatch.setattr(sys, "argv", ["garmin", "schema", "unknown-command"])
    with pytest.raises(SystemExit) as exc_info:
        cli_module.run()
    assert exc_info.value.code == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "NOT_FOUND"


def test_sleep_command_calls_service(runner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import garmin_cli.cli as cli_module

    service = FakeService()
    monkeypatch.setattr(cli_module, "build_state", lambda options, registry: build_fake_state(tmp_path, registry, service))
    result = runner.invoke(app, ["sleep", "2026-03-16"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["score"] == 91
    assert service.calls[0][0] == "sleep"


def test_root_flags_apply_to_commands(runner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import garmin_cli.cli as cli_module

    service = FakeService()
    monkeypatch.setattr(cli_module, "build_state", lambda options, registry: build_fake_state(tmp_path, registry, service))
    result = runner.invoke(app, ["--fields", "activityId", "activities"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"] == [{"activityId": 1}]


def test_global_flags_can_appear_after_the_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    import garmin_cli.cli as cli_module
    import sys

    service = FakeService()
    monkeypatch.setattr(cli_module, "build_state", lambda options, registry: build_fake_state(tmp_path, registry, service))
    monkeypatch.setattr(sys, "argv", ["garmin", "activities", "--fields", "activityId"])
    cli_module.run()
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"] == [{"activityId": 1}]


def test_run_maps_errors_to_json(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import garmin_cli.cli as cli_module

    def explode(*args, **kwargs):
        raise general_error("broken")

    monkeypatch.setattr(cli_module, "app", explode)
    with pytest.raises(SystemExit) as exc_info:
        cli_module.run()
    payload = json.loads(capsys.readouterr().out)
    assert exc_info.value.code == 1
    assert payload["error"]["message"] == "broken"


def test_run_maps_usage_errors_to_exit_code_2(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    import garmin_cli.cli as cli_module
    import sys

    monkeypatch.setattr(cli_module, "_LAST_OUTPUT_FORMAT", None)
    monkeypatch.setattr(sys, "argv", ["garmin", "sleep"])
    with pytest.raises(SystemExit) as exc_info:
        cli_module.run()
    payload = json.loads(capsys.readouterr().out)
    assert exc_info.value.code == 2
    assert payload["error"]["code"] == "USAGE_ERROR"


def test_build_state_uses_configured_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import garmin_cli.cli as cli_module

    configured_cache_dir = tmp_path / "profile-cache"
    monkeypatch.setattr(
        cli_module,
        "load_config",
        lambda: AppConfig(timezone="UTC", cache_dir=str(configured_cache_dir)),
    )
    state = cli_module.build_state(
        GlobalOptions(output="json", no_cache=False, refresh=False, fields=[], verbose=False),
        SchemaRegistry(),
    )
    assert state.cache.db_path == configured_cache_dir / "cache.db"

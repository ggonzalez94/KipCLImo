from __future__ import annotations

import json
from pathlib import Path

import pytest

from garmin_cli.cache import CacheBackend
from garmin_cli.cli import app
from garmin_cli.config import AppConfig, save_config
from garmin_cli.schema import SchemaRegistry
from garmin_cli.state import AppState, GlobalOptions


def _build_state(tmp_path: Path, registry: SchemaRegistry) -> AppState:
    config = AppConfig(timezone="UTC", cache_dir=str(tmp_path))
    return AppState(
        options=GlobalOptions(output="json", no_cache=False, refresh=False, fields=[], verbose=False),
        config=config,
        cache=CacheBackend(tmp_path / "cache.db"),
        auth=None,
        registry=registry,
    )


def test_config_show_returns_full_config(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module
    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: _build_state(tmp_path, reg))
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert "profile" in payload["data"]
    assert payload["data"]["profile"]["onboarding_completed"] is False


def test_config_set_scalar_value(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state
    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set", "profile.primary_goal", "Run a 10K"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["primary_goal"] == "Run a 10K"


def test_config_set_boolean_coercion(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state
    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set", "profile.onboarding_completed", "true"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["onboarding_completed"] is True


def test_config_set_top_level_key(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state
    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set", "timezone", "America/New_York"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["timezone"] == "America/New_York"


def test_config_set_list(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state
    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set-list", "profile.disciplines", "running", "cycling"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["disciplines"] == ["running", "cycling"]


def test_config_reset_profile(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        state.config.profile["disciplines"] = ["running"]
        state.config.profile["onboarding_completed"] = True
        save_config(state.config)
        return state
    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "reset-profile"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["onboarding_completed"] is False
    assert payload["data"]["profile"]["disciplines"] == []


def test_config_commands_in_schema(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module
    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: _build_state(tmp_path, reg))
    result = runner.invoke(app, ["schema"])
    payload = json.loads(result.stdout)
    commands = payload["data"]["commands"]
    assert "config show" in commands
    assert "config set" in commands
    assert "config set-list" in commands
    assert "config reset-profile" in commands

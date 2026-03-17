from __future__ import annotations

import json
from pathlib import Path

from garmin_cli.config import AppConfig, load_config, save_config


def test_appconfig_has_profile_with_default():
    config = AppConfig()
    assert config.profile == {
        "disciplines": [],
        "primary_goal": None,
        "onboarding_completed": False,
    }


def test_save_config_includes_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    config = AppConfig(cache_dir=str(tmp_path))
    config.profile["disciplines"] = ["running", "cycling"]
    config.profile["primary_goal"] = "Run a marathon"
    config.profile["onboarding_completed"] = True
    save_config(config)
    raw = json.loads((tmp_path / "config.json").read_text())
    assert raw["profile"]["disciplines"] == ["running", "cycling"]
    assert raw["profile"]["primary_goal"] == "Run a marathon"
    assert raw["profile"]["onboarding_completed"] is True


def test_load_config_reads_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "config.json").write_text(json.dumps({
        "timezone": "UTC",
        "units": "metric",
        "cache_dir": str(tmp_path),
        "races": [],
        "hr_zones": {"source": "garmin", "custom": None},
        "profile": {
            "disciplines": ["gym"],
            "primary_goal": "General fitness",
            "onboarding_completed": True,
        },
    }))
    config = load_config()
    assert config.profile["disciplines"] == ["gym"]
    assert config.profile["onboarding_completed"] is True


def test_load_config_missing_profile_gives_default(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "config.json").write_text(json.dumps({
        "timezone": "UTC",
        "units": "metric",
        "cache_dir": str(tmp_path),
        "races": [],
        "hr_zones": {"source": "garmin", "custom": None},
    }))
    config = load_config()
    assert config.profile["onboarding_completed"] is False
    assert config.profile["disciplines"] == []


def test_save_load_roundtrip_preserves_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    config = AppConfig(cache_dir=str(tmp_path))
    config.profile["disciplines"] = ["running"]
    config.profile["primary_goal"] = "PR 10K"
    config.profile["onboarding_completed"] = True
    save_config(config)
    loaded = load_config()
    assert loaded.profile == config.profile

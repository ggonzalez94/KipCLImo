"""Configuration and filesystem paths."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_HOME = Path("~/.garmin-cli").expanduser()


@dataclass(slots=True)
class RaceConfig:
    name: str
    date: str
    distance_km: float


@dataclass(slots=True)
class AppConfig:
    timezone: str = os.environ.get("TZ", "UTC")
    units: str = "metric"
    cache_dir: str = str(DEFAULT_HOME)
    races: list[RaceConfig] = field(default_factory=list)
    hr_zones: dict[str, Any] = field(
        default_factory=lambda: {"source": "garmin", "custom": None}
    )

    @property
    def home_dir(self) -> Path:
        return Path(self.cache_dir).expanduser()


def home_dir() -> Path:
    return Path(os.environ.get("GARMIN_HOME", str(DEFAULT_HOME))).expanduser()


def config_path() -> Path:
    return Path(os.environ.get("GARMIN_CONFIG", str(home_dir() / "config.json"))).expanduser()


def cache_path(config: AppConfig | None = None) -> Path:
    if env_path := os.environ.get("GARMIN_CACHE_DB"):
        return Path(env_path).expanduser()
    if config is not None:
        return config.home_dir / "cache.db"
    return home_dir() / "cache.db"


def token_store_path() -> Path:
    return Path(
        os.environ.get("GARMIN_TOKENS", os.environ.get("GARTH_HOME", str(home_dir() / "tokens")))
    ).expanduser()


def ensure_runtime_dirs() -> None:
    home_dir().mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    ensure_runtime_dirs()
    path = config_path()
    if not path.exists():
        return AppConfig(cache_dir=str(home_dir()))

    data = json.loads(path.read_text())
    races = [RaceConfig(**race) for race in data.get("races", [])]
    return AppConfig(
        timezone=data.get("timezone", os.environ.get("TZ", "UTC")),
        units=data.get("units", "metric"),
        cache_dir=data.get("cache_dir", str(home_dir())),
        races=races,
        hr_zones=data.get("hr_zones", {"source": "garmin", "custom": None}),
    )


def save_config(config: AppConfig) -> Path:
    ensure_runtime_dirs()
    path = config_path()
    payload = {
        "timezone": config.timezone,
        "units": config.units,
        "cache_dir": config.cache_dir,
        "races": [
            {"name": race.name, "date": race.date, "distance_km": race.distance_km}
            for race in config.races
        ],
        "hr_zones": config.hr_zones,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path

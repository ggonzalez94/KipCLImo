"""Config management commands."""

from __future__ import annotations

import json

import typer

from ..config import load_config, save_config
from ..output import emit_success
from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import get_state


def _parse_value(raw: str):
    """Parse a CLI string value: json.loads with fallback to string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def _set_nested(data: dict, key: str, value):
    """Set a value in a nested dict using dot-notation key."""
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _config_as_dict(config) -> dict:
    """Convert AppConfig to a plain dict for output."""
    return {
        "timezone": config.timezone,
        "units": config.units,
        "cache_dir": config.cache_dir,
        "races": [
            {"name": r.name, "date": r.date, "distance_km": r.distance_km}
            for r in config.races
        ],
        "hr_zones": config.hr_zones,
        "profile": config.profile,
    }


def _apply_dict_to_config(config, config_dict: dict) -> None:
    """Sync a modified dict back onto the AppConfig object."""
    config.timezone = config_dict.get("timezone", config.timezone)
    config.units = config_dict.get("units", config.units)
    config.cache_dir = config_dict.get("cache_dir", config.cache_dir)
    config.hr_zones = config_dict.get("hr_zones", config.hr_zones)
    config.profile = config_dict.get("profile", config.profile)


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    # --- config show ---
    registry.register(
        CommandSpec(
            name="config show",
            category="config",
            summary="Display current configuration.",
            description="Returns the full config file as a JSON envelope.",
            auth_required=False,
            cache_strategy="none",
            examples=["garmin config show"],
        )
    )

    @app.command("show")
    def config_show(ctx: typer.Context) -> None:
        state = get_state(ctx)
        emit_success(
            _config_as_dict(state.config),
            {"cached": False, "fetched_at": None, "command": "config show"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    # --- config set ---
    registry.register(
        CommandSpec(
            name="config set",
            category="config",
            summary="Set a scalar config value using dot-notation.",
            description="Values are parsed as JSON (booleans, numbers, null) with fallback to string.",
            auth_required=False,
            cache_strategy="none",
            arguments=[
                ParameterSpec("key", "argument", "string", "Dot-notation config key.", required=True),
                ParameterSpec("value", "argument", "string", "Value to set.", required=True),
            ],
            examples=[
                'garmin config set profile.primary_goal "Run a marathon"',
                "garmin config set profile.onboarding_completed true",
            ],
        )
    )

    @app.command("set")
    def config_set(
        ctx: typer.Context,
        key: str = typer.Argument(..., help="Dot-notation config key."),
        value: str = typer.Argument(..., help="Value to set."),
    ) -> None:
        state = get_state(ctx)
        config_dict = _config_as_dict(state.config)
        _set_nested(config_dict, key, _parse_value(value))
        _apply_dict_to_config(state.config, config_dict)
        save_config(state.config)
        updated = load_config()
        emit_success(
            _config_as_dict(updated),
            {"cached": False, "fetched_at": None, "command": "config set"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    # --- config set-list ---
    registry.register(
        CommandSpec(
            name="config set-list",
            category="config",
            summary="Set a list config value.",
            description="Accepts multiple values and stores them as a JSON array.",
            auth_required=False,
            cache_strategy="none",
            arguments=[
                ParameterSpec("key", "argument", "string", "Dot-notation config key.", required=True),
                ParameterSpec("values", "argument", "string[]", "Values for the list.", required=True),
            ],
            examples=["garmin config set-list profile.disciplines running cycling"],
        )
    )

    @app.command("set-list")
    def config_set_list(
        ctx: typer.Context,
        key: str = typer.Argument(..., help="Dot-notation config key."),
        values: list[str] = typer.Argument(..., help="Values for the list."),
    ) -> None:
        state = get_state(ctx)
        config_dict = _config_as_dict(state.config)
        _set_nested(config_dict, key, [_parse_value(v) for v in values])
        _apply_dict_to_config(state.config, config_dict)
        save_config(state.config)
        updated = load_config()
        emit_success(
            _config_as_dict(updated),
            {"cached": False, "fetched_at": None, "command": "config set-list"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    # --- config reset-profile ---
    registry.register(
        CommandSpec(
            name="config reset-profile",
            category="config",
            summary="Reset user profile to defaults.",
            description="Clears disciplines, primary goal, and sets onboarding_completed to false.",
            auth_required=False,
            cache_strategy="none",
            examples=["garmin config reset-profile"],
        )
    )

    @app.command("reset-profile")
    def config_reset_profile(ctx: typer.Context) -> None:
        state = get_state(ctx)
        state.config.profile = {
            "disciplines": [],
            "primary_goal": None,
            "onboarding_completed": False,
        }
        save_config(state.config)
        updated = load_config()
        emit_success(
            _config_as_dict(updated),
            {"cached": False, "fetched_at": None, "command": "config reset-profile"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

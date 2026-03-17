"""Heart-rate and HRV commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="heart-rate",
            category="heart",
            summary="Fetch daily heart-rate data.",
            description="Returns resting, min/max, and time-series heart-rate data for a date.",
            cache_strategy="daily:heart_rate",
            arguments=[ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)],
            examples=["garmin heart-rate 2026-03-16"],
        )
    )

    @app.command("heart-rate")
    def heart_rate(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
        emit_result(
            ctx,
            "heart-rate",
            get_state(ctx).service().heart_rate(date, get_state(ctx).service_options),
        )

    registry.register(
        CommandSpec(
            name="hrv",
            category="heart",
            summary="Fetch HRV data for a date.",
            description="Returns nightly and baseline HRV data for the selected date.",
            cache_strategy="daily:hrv",
            arguments=[ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)],
            examples=["garmin hrv 2026-03-16"],
        )
    )

    @app.command("hrv")
    def hrv(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
        emit_result(ctx, "hrv", get_state(ctx).service().hrv(date, get_state(ctx).service_options))

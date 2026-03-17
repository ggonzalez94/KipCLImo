"""Recovery commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="stress",
            category="recovery",
            summary="Fetch stress data for a date.",
            description="Returns Garmin daily stress metrics for the selected date.",
            cache_strategy="daily:stress",
            arguments=[ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)],
            examples=["garmin stress 2026-03-16"],
        )
    )

    @app.command("stress")
    def stress(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
        emit_result(
            ctx,
            "stress",
            get_state(ctx).service().stress(date, get_state(ctx).service_options),
        )

    registry.register(
        CommandSpec(
            name="body-battery",
            category="recovery",
            summary="Fetch body battery data for one or more dates.",
            description="Returns daily summaries, body battery events, and intraday stress/body battery data.",
            cache_strategy="daily:body_battery",
            arguments=[
                ParameterSpec("start", "argument", "date", "Start date in YYYY-MM-DD.", required=True),
                ParameterSpec("end", "argument", "date", "Optional end date in YYYY-MM-DD.", required=False),
            ],
            examples=["garmin body-battery 2026-03-15 2026-03-16"],
        )
    )

    @app.command("body-battery")
    def body_battery(
        ctx: typer.Context,
        start: str = typer.Argument(...),
        end: str | None = typer.Argument(None),
    ) -> None:
        emit_result(
            ctx,
            "body-battery",
            get_state(ctx).service().body_battery(start, end, get_state(ctx).service_options),
        )

    registry.register(
        CommandSpec(
            name="respiration",
            category="recovery",
            summary="Fetch respiration data for a date.",
            description="Returns Garmin daily respiration metrics for the selected date.",
            cache_strategy="daily:respiration",
            arguments=[ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)],
            examples=["garmin respiration 2026-03-16"],
        )
    )

    @app.command("respiration")
    def respiration(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
        emit_result(
            ctx,
            "respiration",
            get_state(ctx).service().respiration(date, get_state(ctx).service_options),
        )

    registry.register(
        CommandSpec(
            name="spo2",
            category="recovery",
            summary="Fetch pulse ox data for a date.",
            description="Returns Garmin daily SpO2 metrics for the selected date.",
            cache_strategy="daily:spo2",
            arguments=[ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)],
            examples=["garmin spo2 2026-03-16"],
        )
    )

    @app.command("spo2")
    def spo2(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
        emit_result(ctx, "spo2", get_state(ctx).service().spo2(date, get_state(ctx).service_options))

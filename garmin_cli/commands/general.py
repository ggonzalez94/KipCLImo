"""General summary commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="user-summary",
            category="general",
            summary="Fetch the Garmin daily summary for a date.",
            description="Returns daily steps, calories, intensity minutes, stress, and other summary metrics.",
            cache_strategy="daily:user_summary",
            arguments=[ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)],
            examples=["garmin user-summary 2026-03-16"],
        )
    )

    @app.command("user-summary")
    def user_summary(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
        emit_result(
            ctx,
            "user-summary",
            get_state(ctx).service().user_summary(date, get_state(ctx).service_options),
        )

    registry.register(
        CommandSpec(
            name="steps",
            category="general",
            summary="Fetch daily step counts over a range.",
            description="Returns daily step aggregates between two dates.",
            cache_strategy="range:steps",
            arguments=[
                ParameterSpec("start", "argument", "date", "Start date in YYYY-MM-DD.", required=True),
                ParameterSpec("end", "argument", "date", "End date in YYYY-MM-DD.", required=True),
            ],
            examples=["garmin steps 2026-03-01 2026-03-16"],
        )
    )

    @app.command("steps")
    def steps(
        ctx: typer.Context,
        start: str = typer.Argument(...),
        end: str = typer.Argument(...),
    ) -> None:
        emit_result(
            ctx,
            "steps",
            get_state(ctx).service().steps(start, end, get_state(ctx).service_options),
        )

    registry.register(
        CommandSpec(
            name="personal-records",
            category="general",
            summary="Fetch Garmin personal records.",
            description="Returns Garmin personal records for the authenticated athlete.",
            cache_strategy="none",
            examples=["garmin personal-records"],
        )
    )

    @app.command("personal-records")
    def personal_records(ctx: typer.Context) -> None:
        emit_result(ctx, "personal-records", get_state(ctx).service().personal_records())

"""Sleep commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="sleep",
            category="sleep",
            summary="Fetch sleep data for a date.",
            description="Returns sleep score, stages, timing, and supporting Garmin sleep metrics.",
            cache_strategy="daily:sleep",
            arguments=[
                ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)
            ],
            examples=["garmin sleep 2026-03-16"],
        )
    )

    @app.command("sleep")
    def sleep(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
        emit_result(ctx, "sleep", get_state(ctx).service().sleep(date, get_state(ctx).service_options))

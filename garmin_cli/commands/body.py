"""Body composition commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="body-composition",
            category="body",
            summary="Fetch body composition over a date range.",
            description="Returns Garmin body composition metrics over one or more days.",
            cache_strategy="range:body_composition",
            arguments=[
                ParameterSpec("start", "argument", "date", "Start date in YYYY-MM-DD.", required=True),
                ParameterSpec("end", "argument", "date", "Optional end date in YYYY-MM-DD.", required=False),
            ],
            examples=["garmin body-composition 2026-03-01 2026-03-16"],
        )
    )

    @app.command("body-composition")
    def body_composition(
        ctx: typer.Context,
        start: str = typer.Argument(...),
        end: str | None = typer.Argument(None),
    ) -> None:
        emit_result(
            ctx,
            "body-composition",
            get_state(ctx).service().body_composition(start, end, get_state(ctx).service_options),
        )

    registry.register(
        CommandSpec(
            name="weigh-ins",
            category="body",
            summary="Fetch raw weigh-in records for a range.",
            description="Returns Garmin weigh-ins and timestamps over a date range.",
            cache_strategy="range:weigh_ins",
            arguments=[
                ParameterSpec("start", "argument", "date", "Start date in YYYY-MM-DD.", required=True),
                ParameterSpec("end", "argument", "date", "End date in YYYY-MM-DD.", required=True),
            ],
            examples=["garmin weigh-ins 2026-03-01 2026-03-16"],
        )
    )

    @app.command("weigh-ins")
    def weigh_ins(
        ctx: typer.Context,
        start: str = typer.Argument(...),
        end: str = typer.Argument(...),
    ) -> None:
        emit_result(
            ctx,
            "weigh-ins",
            get_state(ctx).service().weigh_ins(start, end, get_state(ctx).service_options),
        )

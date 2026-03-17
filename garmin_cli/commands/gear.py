"""Gear commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="gear",
            category="gear",
            summary="Fetch Garmin gear.",
            description="Returns all configured Garmin gear for the authenticated athlete.",
            cache_strategy="range:gear",
            examples=["garmin gear"],
        )
    )

    @app.command("gear")
    def gear(ctx: typer.Context) -> None:
        emit_result(ctx, "gear", get_state(ctx).service().gear(get_state(ctx).service_options))

    registry.register(
        CommandSpec(
            name="gear-stats",
            category="gear",
            summary="Fetch Garmin gear stats for a gear UUID.",
            description="Returns gear stats and linked activities for a specific gear UUID.",
            cache_strategy="range:gear_stats",
            arguments=[ParameterSpec("uuid", "argument", "string", "Garmin gear UUID.", required=True)],
            examples=["garmin gear-stats 123e4567-e89b-12d3-a456-426614174000"],
        )
    )

    @app.command("gear-stats")
    def gear_stats(ctx: typer.Context, uuid: str = typer.Argument(...)) -> None:
        emit_result(
            ctx,
            "gear-stats",
            get_state(ctx).service().gear_stats(uuid, get_state(ctx).service_options),
        )

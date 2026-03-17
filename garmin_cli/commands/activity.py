"""Activity commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="activities",
            category="activity",
            summary="List Garmin activities.",
            description="Returns activity summaries, optionally constrained by date range and activity type.",
            cache_strategy="range:activities",
            options=[
                ParameterSpec("start", "option", "date", "Start date in YYYY-MM-DD.", default=None),
                ParameterSpec("end", "option", "date", "End date in YYYY-MM-DD.", default=None),
                ParameterSpec("type", "option", "string", "Activity type filter.", default=None),
                ParameterSpec("limit", "option", "integer", "Maximum number of activities to return.", default=20),
            ],
            examples=["garmin activities --start 2026-03-10 --end 2026-03-16 --type running --limit 10"],
        )
    )

    @app.command("activities")
    def activities(
        ctx: typer.Context,
        start: str | None = typer.Option(None, help="Start date in YYYY-MM-DD."),
        end: str | None = typer.Option(None, help="End date in YYYY-MM-DD."),
        activity_type: str | None = typer.Option(None, "--type", help="Activity type filter."),
        limit: int = typer.Option(20, min=1, help="Maximum number of activities to return."),
    ) -> None:
        emit_result(
            ctx,
            "activities",
            get_state(ctx).service().activities(
                start=start,
                end=end,
                activity_type=activity_type,
                limit=limit,
                options=get_state(ctx).service_options,
            ),
        )

    activity_commands = [
        (
            "activity",
            "Fetch a single Garmin activity summary.",
            "Returns the activity summary for an activity id.",
            "none",
            lambda service, activity_id, options: service.activity(activity_id, options),
        ),
        (
            "activity-details",
            "Fetch a single Garmin activity details payload.",
            "Returns detailed charts, metrics, and polyline data for an activity id.",
            "activity_detail:details",
            lambda service, activity_id, options: service.activity_details(activity_id, options),
        ),
        (
            "activity-splits",
            "Fetch lap splits for an activity.",
            "Returns raw splits plus Garmin split summaries for an activity id.",
            "activity_detail:splits",
            lambda service, activity_id, options: service.activity_splits(activity_id, options),
        ),
        (
            "activity-hr-zones",
            "Fetch HR time-in-zone data for an activity.",
            "Returns heart-rate zone distribution for an activity id.",
            "activity_detail:hr_zones",
            lambda service, activity_id, options: service.activity_hr_zones(activity_id, options),
        ),
        (
            "activity-weather",
            "Fetch weather data for an activity.",
            "Returns Garmin weather metadata for an activity id.",
            "activity_detail:weather",
            lambda service, activity_id, options: service.activity_weather(activity_id, options),
        ),
    ]

    for name, summary, description, cache_strategy, handler in activity_commands:
        registry.register(
            CommandSpec(
                name=name,
                category="activity",
                summary=summary,
                description=description,
                cache_strategy=cache_strategy,
                arguments=[
                    ParameterSpec("activity_id", "argument", "string", "Garmin activity id.", required=True)
                ],
                examples=[f"garmin {name} 123456789"],
            )
        )

        def make_command(command_name: str, operation):
            @app.command(command_name)
            def command(ctx: typer.Context, activity_id: str = typer.Argument(...)) -> None:
                emit_result(
                    ctx,
                    command_name,
                    operation(get_state(ctx).service(), activity_id, get_state(ctx).service_options),
                )

        make_command(name, handler)

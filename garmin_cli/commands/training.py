"""Training commands."""

from __future__ import annotations

import typer

from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    day_commands = [
        (
            "training-readiness",
            "Fetch training readiness for a date.",
            "Returns Garmin training readiness and contributing factors for a date.",
            "daily:training_readiness",
            lambda service, cdate, options: service.training_readiness(cdate, options),
        ),
        (
            "training-status",
            "Fetch training status for a date.",
            "Returns Garmin training status, load, and status labels for a date.",
            "daily:training_status",
            lambda service, cdate, options: service.training_status(cdate, options),
        ),
        (
            "vo2max",
            "Fetch VO2max-related scores for a date.",
            "Returns VO2max data derived from Garmin score endpoints.",
            "daily:vo2max",
            lambda service, cdate, options: service.vo2max(cdate, options),
        ),
        (
            "fitness-age",
            "Fetch fitness age for a date.",
            "Returns Garmin fitness age data for a date.",
            "daily:fitness_age",
            lambda service, cdate, options: service.fitness_age(cdate, options),
        ),
    ]

    for name, summary, description, cache_strategy, handler in day_commands:
        registry.register(
            CommandSpec(
                name=name,
                category="training",
                summary=summary,
                description=description,
                cache_strategy=cache_strategy,
                arguments=[ParameterSpec("date", "argument", "date", "Calendar date in YYYY-MM-DD.", required=True)],
                examples=[f"garmin {name} 2026-03-16"],
            )
        )

        def make_day_command(command_name: str, operation):
            @app.command(command_name)
            def command(ctx: typer.Context, date: str = typer.Argument(...)) -> None:
                emit_result(
                    ctx,
                    command_name,
                    operation(get_state(ctx).service(), date, get_state(ctx).service_options),
                )

        make_day_command(name, handler)

    registry.register(
        CommandSpec(
            name="race-predictions",
            category="training",
            summary="Fetch race predictions.",
            description="Returns latest or historical race predictions for supported race distances.",
            cache_strategy="range:race_predictions",
            options=[
                ParameterSpec("start", "option", "date", "Start date in YYYY-MM-DD.", default=None),
                ParameterSpec("end", "option", "date", "End date in YYYY-MM-DD.", default=None),
                ParameterSpec("latest", "option", "boolean", "Force latest predictions.", default=False),
            ],
            examples=["garmin race-predictions --latest", "garmin race-predictions --start 2026-01-01 --end 2026-03-01"],
        )
    )

    @app.command("race-predictions")
    def race_predictions(
        ctx: typer.Context,
        start: str | None = typer.Option(None, help="Start date in YYYY-MM-DD."),
        end: str | None = typer.Option(None, help="End date in YYYY-MM-DD."),
        latest: bool = typer.Option(False, help="Fetch the latest predictions."),
    ) -> None:
        emit_result(
            ctx,
            "race-predictions",
            get_state(ctx).service().race_predictions(
                start=start,
                end=end,
                latest=latest,
                options=get_state(ctx).service_options,
            ),
        )

    registry.register(
        CommandSpec(
            name="endurance-score",
            category="training",
            summary="Fetch endurance score.",
            description="Returns daily or weekly endurance score data.",
            cache_strategy="daily:endurance_score|range:endurance_score",
            arguments=[
                ParameterSpec("start", "argument", "date", "Start date in YYYY-MM-DD.", required=True),
                ParameterSpec("end", "argument", "date", "Optional end date in YYYY-MM-DD.", required=False),
            ],
            examples=["garmin endurance-score 2026-03-16", "garmin endurance-score 2026-03-01 2026-03-16"],
        )
    )

    @app.command("endurance-score")
    def endurance_score(
        ctx: typer.Context,
        start: str = typer.Argument(...),
        end: str | None = typer.Argument(None),
    ) -> None:
        emit_result(
            ctx,
            "endurance-score",
            get_state(ctx).service().endurance_score(start, end, get_state(ctx).service_options),
        )

"""CLI entrypoint."""

from __future__ import annotations

import logging
import sys

import click
import typer

from .auth import AuthManager
from .cache import CacheBackend
from .config import cache_path, ensure_runtime_dirs, load_config
from .errors import GarminCliError, map_exception, usage_error
from .output import emit_error, resolve_output_format
from .schema import CommandSpec, ParameterSpec, SchemaRegistry
from .state import AppState, GlobalOptions
from .utils import parse_fields
from .commands import activity, auth_cmds, body, gear, general, heart, recovery, sleep, training

_LAST_OUTPUT_FORMAT: str | None = None
_GLOBAL_FLAG_ARITY = {
    "--output": 1,
    "-o": 1,
    "--fields": 1,
    "-f": 1,
    "--no-cache": 0,
    "--refresh": 0,
    "--verbose": 0,
    "-v": 0,
}


def build_state(options: GlobalOptions, registry: SchemaRegistry) -> AppState:
    ensure_runtime_dirs()
    config = load_config()
    cache = CacheBackend(cache_path(config))
    auth = AuthManager()
    return AppState(
        options=options,
        config=config,
        cache=cache,
        auth=auth,
        registry=registry,
    )


def create_app() -> typer.Typer:
    registry = SchemaRegistry()
    app = typer.Typer(
        add_completion=False,
        no_args_is_help=True,
        help="Agent-friendly Garmin Connect CLI.",
    )
    cache_app = typer.Typer(help="Inspect and manage the SQLite cache.")
    app.add_typer(cache_app, name="cache")

    @app.callback()
    def main(
        ctx: typer.Context,
        output: str | None = typer.Option(None, "--output", "-o", help="Output format: json or human."),
        no_cache: bool = typer.Option(False, help="Bypass the SQLite cache."),
        refresh: bool = typer.Option(False, help="Fetch fresh data and update the cache."),
        fields: str | None = typer.Option(None, "--fields", "-f", help="Comma-separated field selection."),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    ) -> None:
        global _LAST_OUTPUT_FORMAT
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.WARNING,
            format="%(levelname)s %(message)s",
        )
        options = GlobalOptions(
            output=resolve_output_format(output),
            no_cache=no_cache,
            refresh=refresh,
            fields=parse_fields(fields),
            verbose=verbose,
        )
        _LAST_OUTPUT_FORMAT = options.output
        ctx.obj = build_state(options, registry)

    registry.register(
        CommandSpec(
            name="cache stats",
            category="cache",
            summary="Inspect cache table counts and freshness metadata.",
            description="Returns cache size, per-table totals, and metric breakdowns.",
            auth_required=False,
            cache_strategy="none",
            examples=["garmin cache stats"],
        )
    )

    @cache_app.command("stats")
    def cache_stats(ctx: typer.Context) -> None:
        state: AppState = ctx.find_root().obj
        from .output import emit_success

        emit_success(
            state.cache.stats(),
            {"cached": False, "fetched_at": None, "command": "cache stats"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    registry.register(
        CommandSpec(
            name="cache clear",
            category="cache",
            summary="Delete cached rows.",
            description="Clears the full cache, rows before a date, or a specific daily metric.",
            auth_required=False,
            cache_strategy="none",
            options=[
                ParameterSpec("before", "option", "date", "Delete rows before this date.", default=None),
                ParameterSpec("metric", "option", "string", "Delete only this daily metric.", default=None),
            ],
            examples=["garmin cache clear --before 2026-01-01", "garmin cache clear --metric hrv"],
        )
    )

    @cache_app.command("clear")
    def cache_clear(
        ctx: typer.Context,
        before: str | None = typer.Option(None, help="Delete entries before this YYYY-MM-DD date."),
        metric: str | None = typer.Option(None, help="Delete only a specific daily metric."),
    ) -> None:
        state: AppState = ctx.find_root().obj
        from .output import emit_success

        emit_success(
            state.cache.clear(before=before, metric=metric),
            {"cached": False, "fetched_at": None, "command": "cache clear"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    auth_cmds.register(app, registry)
    sleep.register(app, registry)
    heart.register(app, registry)
    recovery.register(app, registry)
    activity.register(app, registry)
    training.register(app, registry)
    body.register(app, registry)
    general.register(app, registry)
    gear.register(app, registry)
    return app


app = create_app()


def normalize_global_flags(argv: list[str]) -> list[str]:
    """Allow global flags both before and after the subcommand."""

    global_args: list[str] = []
    other_args: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--":
            other_args.extend(argv[index:])
            break
        if arg in _GLOBAL_FLAG_ARITY:
            global_args.append(arg)
            arity = _GLOBAL_FLAG_ARITY[arg]
            if arity == 1:
                if index + 1 >= len(argv):
                    other_args.append(arg)
                    index += 1
                    continue
                global_args.append(argv[index + 1])
                index += 2
                continue
            index += 1
            continue
        other_args.append(arg)
        index += 1
    return [*global_args, *other_args]


def run() -> None:
    try:
        app(standalone_mode=False, args=normalize_global_flags(sys.argv[1:]))
    except GarminCliError as exc:
        output = _LAST_OUTPUT_FORMAT or resolve_output_format(None)
        emit_error(exc, output_format=output)
        raise SystemExit(exc.exit_code) from exc
    except click.UsageError as exc:
        mapped = usage_error(exc.format_message())
        output = _LAST_OUTPUT_FORMAT or resolve_output_format(None)
        emit_error(mapped, output_format=output)
        raise SystemExit(mapped.exit_code) from exc
    except click.ClickException as exc:
        mapped = map_exception(exc)
        output = _LAST_OUTPUT_FORMAT or resolve_output_format(None)
        emit_error(mapped, output_format=output)
        raise SystemExit(mapped.exit_code) from exc
    except Exception as exc:  # pragma: no cover - final guardrail
        mapped = map_exception(exc)
        output = _LAST_OUTPUT_FORMAT or resolve_output_format(None)
        emit_error(mapped, output_format=output)
        raise SystemExit(mapped.exit_code) from exc


if __name__ == "__main__":
    run()

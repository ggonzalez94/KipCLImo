"""Auth and system commands."""

from __future__ import annotations

import sys

import typer

from ..client import FetchResult
from ..errors import not_found_error
from ..output import emit_success
from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import emit_result, get_state


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    registry.register(
        CommandSpec(
            name="login",
            category="auth",
            summary="Authenticate with Garmin Connect and persist OAuth tokens.",
            description="Interactive login with token storage under ~/.garmin-cli/tokens by default.",
            auth_required=False,
            cache_strategy="none",
            options=[
                ParameterSpec("email", "option", "string", "Garmin email address.", default=None),
                ParameterSpec("password", "option", "string", "Garmin password.", default=None),
            ],
            examples=["garmin login --email runner@example.com"],
        )
    )

    @app.command("login")
    def login(
        ctx: typer.Context,
        email: str | None = typer.Option(None, help="Garmin email address."),
        password: str | None = typer.Option(None, help="Garmin password."),
    ) -> None:
        if email is None and sys.stdin.isatty():
            email = typer.prompt("Garmin email")
        if password is None and sys.stdin.isatty():
            password = typer.prompt("Garmin password", hide_input=True)
        result = get_state(ctx).service().login(email, password)
        emit_result(ctx, "login", result)

    registry.register(
        CommandSpec(
            name="status",
            category="auth",
            summary="Check authentication and cache status.",
            description="Verifies token validity and reports cache metadata.",
            auth_required=False,
            cache_strategy="none",
            examples=["garmin status"],
        )
    )

    @app.command("status")
    def status(ctx: typer.Context) -> None:
        emit_result(ctx, "status", get_state(ctx).service().status())

    registry.register(
        CommandSpec(
            name="schema",
            category="system",
            summary="Describe commands, arguments, and output contracts.",
            description="Runtime schema introspection for agents.",
            auth_required=False,
            cache_strategy="none",
            arguments=[
                ParameterSpec(
                    "command_name",
                    "argument",
                    "string",
                    "Optional command name to inspect.",
                    required=False,
                )
            ],
            examples=["garmin schema", "garmin schema activities"],
        )
    )

    @app.command("schema")
    def schema(ctx: typer.Context, command_name: str | None = typer.Argument(None)) -> None:
        state = get_state(ctx)
        if command_name:
            spec = state.registry.get(command_name)
            if spec is None:
                raise not_found_error(f"Unknown command: {command_name}")
            data = {"command": command_name, "schema": spec}
        else:
            data = state.registry.as_dict()
        emit_success(
            data,
            {"cached": False, "fetched_at": None, "command": "schema"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

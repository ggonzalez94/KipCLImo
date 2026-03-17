"""Shared command helpers."""

from __future__ import annotations

import typer

from ..client import FetchResult
from ..output import emit_success
from ..state import AppState


def get_state(ctx: typer.Context) -> AppState:
    root = ctx.find_root()
    assert isinstance(root.obj, AppState)
    return root.obj


def emit_result(ctx: typer.Context, command_name: str, result: FetchResult) -> None:
    state = get_state(ctx)
    metadata = {"command": command_name, **result.metadata}
    emit_success(
        result.data,
        metadata,
        output_format=state.options.output,
        fields=state.options.fields,
    )

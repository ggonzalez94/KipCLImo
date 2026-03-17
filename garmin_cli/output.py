"""Rendering helpers for JSON and human output."""

from __future__ import annotations

import os
import sys
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.table import Table

from .errors import GarminCliError
from .utils import json_ready, select_fields, stable_json_dumps


def resolve_output_format(requested: str | None) -> str:
    env_override = os.environ.get("GARMIN_OUTPUT")
    if requested in {"json", "human"}:
        return requested
    if env_override in {"json", "human"}:
        return env_override
    return "human" if sys.stdout.isatty() else "json"


def success_envelope(data: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "data": json_ready(data),
        "metadata": json_ready(metadata),
    }


def error_envelope(error: GarminCliError) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {"code": error.code, "message": error.message},
        "metadata": json_ready(error.metadata),
    }


def emit_success(
    data: Any,
    metadata: dict[str, Any],
    *,
    output_format: str,
    fields: list[str],
) -> None:
    selected = select_fields(json_ready(data), fields)
    envelope = success_envelope(selected, metadata)
    if output_format == "json":
        print(stable_json_dumps(envelope))
        return

    console = Console()
    metadata_table = Table(show_header=True, header_style="bold")
    metadata_table.add_column("Key")
    metadata_table.add_column("Value")
    for key, value in envelope["metadata"].items():
        metadata_table.add_row(str(key), str(value))
    console.print(metadata_table)
    console.print(JSON.from_data(envelope["data"]))


def emit_error(error: GarminCliError, *, output_format: str) -> None:
    envelope = error_envelope(error)
    if output_format == "json":
        print(stable_json_dumps(envelope))
        return

    console = Console(stderr=True)
    console.print(f"[bold red]{error.code}[/bold red]: {error.message}")
    if error.metadata:
        console.print(JSON.from_data(envelope["metadata"]))

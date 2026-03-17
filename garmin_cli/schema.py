"""Self-describing command registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ParameterSpec:
    name: str
    kind: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CommandSpec:
    name: str
    category: str
    summary: str
    description: str
    auth_required: bool = True
    cache_strategy: str = "none"
    arguments: list[ParameterSpec] = field(default_factory=list)
    options: list[ParameterSpec] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


GLOBAL_FLAGS = [
    ParameterSpec(
        name="output",
        kind="option",
        type="string",
        description="Output format (`json` or `human`).",
        default="auto",
        enum=["json", "human", "auto"],
    ),
    ParameterSpec(
        name="no-cache",
        kind="option",
        type="boolean",
        description="Bypass the SQLite cache and do not update it.",
        default=False,
    ),
    ParameterSpec(
        name="refresh",
        kind="option",
        type="boolean",
        description="Fetch fresh data and update cache entries.",
        default=False,
    ),
    ParameterSpec(
        name="fields",
        kind="option",
        type="string",
        description="Comma-separated field selection.",
        default=None,
    ),
    ParameterSpec(
        name="verbose",
        kind="option",
        type="boolean",
        description="Enable debug logging on stderr.",
        default=False,
    ),
]


class SchemaRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandSpec] = {}

    def register(self, spec: CommandSpec) -> None:
        self._commands[spec.name] = spec

    def get(self, command_name: str) -> CommandSpec | None:
        return self._commands.get(command_name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "global_flags": [asdict(flag) for flag in GLOBAL_FLAGS],
            "commands": {
                name: asdict(spec) for name, spec in sorted(self._commands.items())
            },
        }

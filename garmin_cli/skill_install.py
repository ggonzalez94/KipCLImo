"""Install the Garmin skill into agent-specific skill directories."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .errors import usage_error


@dataclass(slots=True)
class InstallResult:
    source: Path
    destination: Path
    method: str


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def source_skill_dir() -> Path:
    return project_root() / "skills" / "garmin-coach"


def default_target_dir(agent: str) -> Path:
    agent = agent.lower()
    if agent == "custom":
        raise usage_error("Custom installs require an explicit destination root.")
    if agent == "openclaw":
        return Path(
            os.environ.get(
                "OPENCLAW_SKILLS_DIR",
                "~/.openclaw/workspace/skills",
            )
        ).expanduser()
    if agent == "codex":
        codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
        return codex_home / "skills"
    if agent == "claude":
        return Path(os.environ.get("CLAUDE_SKILLS_DIR", "~/.claude/skills")).expanduser()
    raise usage_error(f"Unsupported agent target: {agent}")


def install_skill(
    *,
    agent: str,
    destination_root: Path | None = None,
    method: str = "auto",
    force: bool = False,
) -> InstallResult:
    source = source_skill_dir()
    if not source.exists():
        raise usage_error(f"Skill source not found: {source}")

    destination_root = destination_root or default_target_dir(agent)
    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source.name

    if destination.exists() or destination.is_symlink():
        if not force:
            raise usage_error(
                f"Destination already exists: {destination}. Re-run with --force to replace it."
            )
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)

    chosen_method = method
    if method == "auto":
        chosen_method = "symlink"

    if chosen_method == "symlink":
        try:
            destination.symlink_to(source, target_is_directory=True)
        except OSError:
            chosen_method = "copy"

    if chosen_method == "copy":
        shutil.copytree(source, destination)

    return InstallResult(source=source, destination=destination, method=chosen_method)

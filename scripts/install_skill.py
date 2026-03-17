#!/usr/bin/env python3
"""Install the garmin-coach skill into an agent skill directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from garmin_cli.skill_install import install_skill


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent",
        choices=["openclaw", "codex", "claude", "custom"],
        default="openclaw",
        help="Agent target to install into.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Override the destination skill root directory.",
    )
    parser.add_argument(
        "--method",
        choices=["auto", "symlink", "copy"],
        default="auto",
        help="Installation method. Auto prefers symlink and falls back to copy.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing installed skill.",
    )
    args = parser.parse_args()

    result = install_skill(
        agent=args.agent,
        destination_root=args.dest,
        method=args.method,
        force=args.force,
    )
    print(
        f"Installed {result.source.name} into {result.destination} using {result.method}."
    )


if __name__ == "__main__":
    main()

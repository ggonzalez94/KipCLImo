"""Authentication helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from garminconnect import Garmin

from .config import token_store_path
from .errors import auth_error


def _is_token_dir(path: Path) -> bool:
    return (path / "oauth1_token.json").exists() and (path / "oauth2_token.json").exists()


def _secure_token_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    for token_file in path.glob("*.json"):
        os.chmod(token_file, 0o600)


class AuthManager:
    """Create authenticated Garmin clients and manage token storage."""

    def __init__(self, token_dir: Path | None = None):
        self.token_dir = token_dir or token_store_path()

    def resolve_existing_token_dir(self) -> Path:
        candidates = [
            Path(os.environ["GARMIN_TOKENS"]).expanduser()
            for _ in [0]
            if os.environ.get("GARMIN_TOKENS")
        ]
        if os.environ.get("GARTH_HOME"):
            candidates.append(Path(os.environ["GARTH_HOME"]).expanduser())
        candidates.extend(
            [
                self.token_dir.expanduser(),
                Path("~/.garminconnect").expanduser(),
                Path("~/.garth").expanduser(),
            ]
        )
        for candidate in candidates:
            if _is_token_dir(candidate):
                return candidate
        raise FileNotFoundError("No Garmin token store found")

    def login(self, email: str | None = None, password: str | None = None) -> dict[str, Any]:
        email = email or os.environ.get("GARMIN_EMAIL")
        password = password or os.environ.get("GARMIN_PASSWORD")
        if not email or not password:
            raise auth_error(
                "Email and password are required. Use flags or GARMIN_EMAIL/GARMIN_PASSWORD."
            )

        client = Garmin(email, password)
        client.login()
        self.token_dir.mkdir(parents=True, exist_ok=True)
        client.garth.dump(str(self.token_dir))
        _secure_token_dir(self.token_dir)
        profile = client.get_user_profile()
        return {
            "token_dir": str(self.token_dir),
            "display_name": client.display_name,
            "full_name": client.get_full_name(),
            "measurement_system": client.get_unit_system(),
            "profile": profile,
        }

    def load_client(self) -> Garmin:
        token_dir = self.resolve_existing_token_dir()
        client = Garmin()
        client.login(tokenstore=str(token_dir))
        return client

    def status(self) -> dict[str, Any]:
        token_dir = self.resolve_existing_token_dir()
        client = Garmin()
        client.login(tokenstore=str(token_dir))
        profile = client.get_user_profile()
        return {
            "authenticated": True,
            "token_dir": str(token_dir),
            "display_name": client.display_name,
            "full_name": client.get_full_name(),
            "measurement_system": client.get_unit_system(),
            "profile": profile,
        }

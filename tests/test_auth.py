from __future__ import annotations

from pathlib import Path

import pytest

from garmin_cli.auth import AuthManager


def write_tokens(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "oauth1_token.json").write_text("{}")
    (path / "oauth2_token.json").write_text("{}")


def test_resolve_existing_token_dir_prefers_explicit_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    explicit = tmp_path / "explicit"
    fallback = tmp_path / "fallback"
    write_tokens(explicit)
    write_tokens(fallback)
    monkeypatch.setenv("GARMIN_TOKENS", str(explicit))
    manager = AuthManager(token_dir=fallback)
    assert manager.resolve_existing_token_dir() == explicit


def test_resolve_existing_token_dir_raises_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GARMIN_TOKENS", raising=False)
    monkeypatch.delenv("GARTH_HOME", raising=False)
    manager = AuthManager(token_dir=tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        manager.resolve_existing_token_dir()


def test_resolve_existing_token_dir_uses_garminconnect_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    garminconnect_dir = tmp_path / ".garminconnect"
    write_tokens(garminconnect_dir)
    monkeypatch.setenv("HOME", str(tmp_path))
    manager = AuthManager(token_dir=tmp_path / "missing")
    assert manager.resolve_existing_token_dir() == garminconnect_dir

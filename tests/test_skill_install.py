from __future__ import annotations

from pathlib import Path

from garmin_cli.skill_install import install_skill


def test_install_skill_copy(tmp_path: Path) -> None:
    result = install_skill(
        agent="openclaw",
        destination_root=tmp_path,
        method="copy",
        force=True,
    )
    assert result.destination.exists()
    assert (result.destination / "SKILL.md").exists()
    assert result.method == "copy"


def test_install_skill_symlink(tmp_path: Path) -> None:
    result = install_skill(
        agent="openclaw",
        destination_root=tmp_path,
        method="symlink",
        force=True,
    )
    assert result.destination.is_symlink()


def test_install_skill_custom_target(tmp_path: Path) -> None:
    result = install_skill(
        agent="custom",
        destination_root=tmp_path,
        method="copy",
        force=True,
    )
    assert (result.destination / "SKILL.md").exists()

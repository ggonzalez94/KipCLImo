from __future__ import annotations

from collections.abc import Callable

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def noop_sleep() -> Callable[[float], None]:
    return lambda _: None

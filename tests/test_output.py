from __future__ import annotations

import json

from garmin_cli.errors import general_error
from garmin_cli.output import emit_error, emit_success, resolve_output_format


def test_emit_success_json_and_fields(capsys) -> None:
    emit_success(
        {"summary": {"score": 92, "duration": 480}, "extra": "ignored"},
        {"cached": True, "command": "sleep"},
        output_format="json",
        fields=["summary.score"],
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["data"] == {"summary": {"score": 92}}
    assert payload["metadata"]["cached"] is True


def test_emit_error_json(capsys) -> None:
    emit_error(general_error("boom", command="sleep"), output_format="json")
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error"]["message"] == "boom"
    assert payload["metadata"]["command"] == "sleep"


def test_resolve_output_format_prefers_explicit(monkeypatch) -> None:
    monkeypatch.setenv("GARMIN_OUTPUT", "human")
    assert resolve_output_format("json") == "json"

# Agent Instructions

## Repository overview

KipCLImo is a thin, agent-friendly CLI wrapping the Garmin Connect API. It is a pure data-access layer — 27 commands that return raw Garmin data in a stable JSON envelope. Coaching intelligence lives in the `garmin-coach` skill (`skills/garmin-coach/`), not in the CLI itself.

## Conventions

- Keep code, docs, comments, and commit messages in English.
- The `garmin-coach` skill is also written in English, but it instructs agents to:
  - default unattended reports to Spanish
  - answer in the language the user is currently using during interactive chat
- Prefer extending the existing service and schema registry instead of adding one-off CLI behavior directly in command handlers.
- Preserve the stable JSON envelope and exit-code semantics.

## Architecture

```
CLI (Typer) → AppState → GarminService → Cache (SQLite) / Auth (garth) / Garmin SDK
```

- **`garmin_cli/client.py`** — `GarminService` is the core layer. All API calls, cache reads/writes, and retry logic live here. Three internal patterns: `_fetch_day()` for daily metrics, `_fetch_range()` for range queries, `_fetch_activity_detail()` for per-activity data.
- **`garmin_cli/cache.py`** — SQLite with 4 tables: `daily_cache`, `activity_cache`, `activity_detail_cache`, `range_cache`. Past dates are immutable (served from cache). Today always fetches fresh.
- **`garmin_cli/output.py`** — Every command returns `{"status": "ok", "data": ..., "metadata": {...}}` or `{"status": "error", ...}`. Do not change this envelope shape.
- **`garmin_cli/errors.py`** — Exit codes 0-5 are stable and consumed by agents. `map_exception()` translates SDK errors at the boundary.
- **`garmin_cli/schema.py`** — `SchemaRegistry` provides runtime introspection via `garmin schema`. Every command must be registered here.
- **`garmin_cli/commands/`** — One module per category. Each exports `register(app, registry)`. Commands use `get_state(ctx).service().<method>()` and `emit_result()`.

## Adding a new command

1. Add the service method to `GarminService` in `client.py`, using `_fetch_day`, `_fetch_range`, or `_fetch_activity_detail`.
2. Add the command to the appropriate module in `commands/`, calling `registry.register(CommandSpec(...))` and using `emit_result()`.
3. Add the command to `skills/garmin-coach/references/cli.md` so agents discover it.
4. Add a test in `tests/`.

## Key rules

- The CLI must remain agent-agnostic — no MCP, no protocol coupling, just subprocess stdin/stdout/stderr.
- No composite commands — if analysis requires multiple API calls, that logic belongs in the skill or the agent, not the CLI.
- `--fields` flag exists for context-window discipline. Agents should use it on large payloads.
- Rate-limit retries (2s, 5s, 15s backoff) are handled in `GarminService._invoke()`. Do not add retry logic elsewhere.
- All dates are ISO 8601 (`YYYY-MM-DD`). Today detection uses the configured timezone.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

Tests use hand-rolled stubs (not `unittest.mock`) for the Garmin SDK. See `tests/test_client.py` for the `FakeAuth`/`FakeSdk` pattern.

## Dependencies

- `garminconnect` — Garmin Connect API wrapper
- `typer` — CLI framework
- `rich` — Human-readable output formatting
- `garth` — OAuth token management (used by garminconnect)

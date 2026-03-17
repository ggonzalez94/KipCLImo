# Multi-Discipline Onboarding Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add config commands, guided onboarding, and discipline-specific coaching skills to KipCLImo.

**Architecture:** Config commands (`garmin config show/set/set-list/reset-profile`) provide the data layer. The `garmin-coach` skill drives onboarding conversationally and loads discipline-specific reference files based on user profile. Running-specific metrics move from SKILL.md to `references/running.md`; new `cycling.md`, `gym.md`, and `goals.md` references are added.

**Tech Stack:** Python 3.11+, Typer, SQLite (unchanged), Markdown skills

**Spec:** `docs/superpowers/specs/2026-03-17-multi-discipline-onboarding-design.md`

---

## Task 1: Add `profile` field to `AppConfig`

**Files:**
- Modify: `garmin_cli/config.py:15-30` (AppConfig dataclass)
- Modify: `garmin_cli/config.py:63-77` (load_config)
- Modify: `garmin_cli/config.py:80-94` (save_config)
- Test: `tests/test_config.py` (new file)

- [ ] **Step 1: Write failing tests for profile in config**

Create `tests/test_config.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from garmin_cli.config import AppConfig, load_config, save_config


def test_appconfig_has_profile_with_default():
    config = AppConfig()
    assert config.profile == {
        "disciplines": [],
        "primary_goal": None,
        "onboarding_completed": False,
    }


def test_save_config_includes_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    config = AppConfig(cache_dir=str(tmp_path))
    config.profile["disciplines"] = ["running", "cycling"]
    config.profile["primary_goal"] = "Run a marathon"
    config.profile["onboarding_completed"] = True
    save_config(config)
    raw = json.loads((tmp_path / "config.json").read_text())
    assert raw["profile"]["disciplines"] == ["running", "cycling"]
    assert raw["profile"]["primary_goal"] == "Run a marathon"
    assert raw["profile"]["onboarding_completed"] is True


def test_load_config_reads_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "config.json").write_text(json.dumps({
        "timezone": "UTC",
        "units": "metric",
        "cache_dir": str(tmp_path),
        "races": [],
        "hr_zones": {"source": "garmin", "custom": None},
        "profile": {
            "disciplines": ["gym"],
            "primary_goal": "General fitness",
            "onboarding_completed": True,
        },
    }))
    config = load_config()
    assert config.profile["disciplines"] == ["gym"]
    assert config.profile["onboarding_completed"] is True


def test_load_config_missing_profile_gives_default(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "config.json").write_text(json.dumps({
        "timezone": "UTC",
        "units": "metric",
        "cache_dir": str(tmp_path),
        "races": [],
        "hr_zones": {"source": "garmin", "custom": None},
    }))
    config = load_config()
    assert config.profile["onboarding_completed"] is False
    assert config.profile["disciplines"] == []


def test_save_load_roundtrip_preserves_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))
    config = AppConfig(cache_dir=str(tmp_path))
    config.profile["disciplines"] = ["running"]
    config.profile["primary_goal"] = "PR 10K"
    config.profile["onboarding_completed"] = True
    save_config(config)
    loaded = load_config()
    assert loaded.profile == config.profile
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `AppConfig` has no `profile` field

- [ ] **Step 3: Add profile field to AppConfig**

In `garmin_cli/config.py`, add to the `AppConfig` dataclass (after `hr_zones`):

```python
    profile: dict[str, Any] = field(
        default_factory=lambda: {
            "disciplines": [],
            "primary_goal": None,
            "onboarding_completed": False,
        }
    )
```

- [ ] **Step 4: Update `load_config` to deserialize profile**

In `garmin_cli/config.py`, update the `load_config` function. Add `profile` to the returned `AppConfig`:

```python
    return AppConfig(
        timezone=data.get("timezone", os.environ.get("TZ", "UTC")),
        units=data.get("units", "metric"),
        cache_dir=data.get("cache_dir", str(home_dir())),
        races=races,
        hr_zones=data.get("hr_zones", {"source": "garmin", "custom": None}),
        profile=data.get("profile", {
            "disciplines": [],
            "primary_goal": None,
            "onboarding_completed": False,
        }),
    )
```

- [ ] **Step 5: Update `save_config` to serialize profile**

In `garmin_cli/config.py`, add `"profile": config.profile` to the `payload` dict in `save_config`, after `"hr_zones"`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Run full test suite**

Run: `pytest -v`
Expected: All existing tests still pass

- [ ] **Step 8: Commit**

```bash
git add garmin_cli/config.py tests/test_config.py
git commit -m "feat(config): add profile field to AppConfig with save/load support"
```

---

## Task 2: Create `config` CLI commands

**Files:**
- Create: `garmin_cli/commands/config_cmds.py`
- Modify: `garmin_cli/cli.py:19` (import), `garmin_cli/cli.py:48-57` (wiring)
- Test: `tests/test_config_cmds.py` (new file)

- [ ] **Step 1: Write failing tests for config commands**

Create `tests/test_config_cmds.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from garmin_cli.cache import CacheBackend
from garmin_cli.cli import app
from garmin_cli.config import AppConfig, save_config
from garmin_cli.schema import SchemaRegistry
from garmin_cli.state import AppState, GlobalOptions


def _build_state(tmp_path: Path, registry: SchemaRegistry) -> AppState:
    config = AppConfig(timezone="UTC", cache_dir=str(tmp_path))
    return AppState(
        options=GlobalOptions(output="json", no_cache=False, refresh=False, fields=[], verbose=False),
        config=config,
        cache=CacheBackend(tmp_path / "cache.db"),
        auth=None,
        registry=registry,
    )


def test_config_show_returns_full_config(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module

    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: _build_state(tmp_path, reg))
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert "profile" in payload["data"]
    assert payload["data"]["profile"]["onboarding_completed"] is False


def test_config_set_scalar_value(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module

    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))

    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state

    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set", "profile.primary_goal", "Run a 10K"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["primary_goal"] == "Run a 10K"


def test_config_set_boolean_coercion(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module

    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))

    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state

    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set", "profile.onboarding_completed", "true"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["onboarding_completed"] is True  # boolean, not string


def test_config_set_list(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module

    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))

    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state

    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set-list", "profile.disciplines", "running", "cycling"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["disciplines"] == ["running", "cycling"]


def test_config_reset_profile(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module

    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))

    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        state.config.profile["disciplines"] = ["running"]
        state.config.profile["onboarding_completed"] = True
        save_config(state.config)
        return state

    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "reset-profile"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["profile"]["onboarding_completed"] is False
    assert payload["data"]["profile"]["disciplines"] == []


def test_config_set_top_level_key(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module

    monkeypatch.setenv("GARMIN_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("GARMIN_HOME", str(tmp_path))

    def make_state(opts, reg):
        state = _build_state(tmp_path, reg)
        save_config(state.config)
        return state

    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: make_state(opts, reg))
    result = runner.invoke(app, ["config", "set", "timezone", "America/New_York"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["timezone"] == "America/New_York"


def test_config_commands_in_schema(runner, monkeypatch, tmp_path):
    import garmin_cli.cli as cli_module

    monkeypatch.setattr(cli_module, "build_state", lambda opts, reg: _build_state(tmp_path, reg))
    result = runner.invoke(app, ["schema"])
    payload = json.loads(result.stdout)
    commands = payload["data"]["commands"]
    assert "config show" in commands
    assert "config set" in commands
    assert "config set-list" in commands
    assert "config reset-profile" in commands
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_cmds.py -v`
Expected: FAIL — no `config` subcommand exists

- [ ] **Step 3: Create `config_cmds.py`**

Create `garmin_cli/commands/config_cmds.py`:

```python
"""Config management commands."""

from __future__ import annotations

import json

import typer

from ..config import load_config, save_config
from ..output import emit_success
from ..schema import CommandSpec, ParameterSpec, SchemaRegistry
from .common import get_state


def _parse_value(raw: str):
    """Parse a CLI string value: json.loads with fallback to string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def _set_nested(data: dict, key: str, value):
    """Set a value in a nested dict using dot-notation key."""
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _config_as_dict(config) -> dict:
    """Convert AppConfig to a plain dict for output."""
    return {
        "timezone": config.timezone,
        "units": config.units,
        "cache_dir": config.cache_dir,
        "races": [
            {"name": r.name, "date": r.date, "distance_km": r.distance_km}
            for r in config.races
        ],
        "hr_zones": config.hr_zones,
        "profile": config.profile,
    }


def _apply_dict_to_config(config, config_dict: dict) -> None:
    """Sync a modified dict back onto the AppConfig object."""
    config.timezone = config_dict.get("timezone", config.timezone)
    config.units = config_dict.get("units", config.units)
    config.cache_dir = config_dict.get("cache_dir", config.cache_dir)
    config.hr_zones = config_dict.get("hr_zones", config.hr_zones)
    config.profile = config_dict.get("profile", config.profile)


def register(app: typer.Typer, registry: SchemaRegistry) -> None:
    # --- config show ---
    registry.register(
        CommandSpec(
            name="config show",
            category="config",
            summary="Display current configuration.",
            description="Returns the full config file as a JSON envelope.",
            auth_required=False,
            cache_strategy="none",
            examples=["garmin config show"],
        )
    )

    @app.command("show")
    def config_show(ctx: typer.Context) -> None:
        state = get_state(ctx)
        emit_success(
            _config_as_dict(state.config),
            {"cached": False, "fetched_at": None, "command": "config show"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    # --- config set ---
    registry.register(
        CommandSpec(
            name="config set",
            category="config",
            summary="Set a scalar config value using dot-notation.",
            description="Values are parsed as JSON (booleans, numbers, null) with fallback to string.",
            auth_required=False,
            cache_strategy="none",
            arguments=[
                ParameterSpec("key", "argument", "string", "Dot-notation config key.", required=True),
                ParameterSpec("value", "argument", "string", "Value to set.", required=True),
            ],
            examples=[
                'garmin config set profile.primary_goal "Run a marathon"',
                "garmin config set profile.onboarding_completed true",
            ],
        )
    )

    @app.command("set")
    def config_set(
        ctx: typer.Context,
        key: str = typer.Argument(..., help="Dot-notation config key."),
        value: str = typer.Argument(..., help="Value to set."),
    ) -> None:
        state = get_state(ctx)
        config_dict = _config_as_dict(state.config)
        _set_nested(config_dict, key, _parse_value(value))
        _apply_dict_to_config(state.config, config_dict)
        save_config(state.config)
        updated = load_config()
        emit_success(
            _config_as_dict(updated),
            {"cached": False, "fetched_at": None, "command": "config set"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    # --- config set-list ---
    registry.register(
        CommandSpec(
            name="config set-list",
            category="config",
            summary="Set a list config value.",
            description="Accepts multiple values and stores them as a JSON array.",
            auth_required=False,
            cache_strategy="none",
            arguments=[
                ParameterSpec("key", "argument", "string", "Dot-notation config key.", required=True),
                ParameterSpec("values", "argument", "string[]", "Values for the list.", required=True),
            ],
            examples=["garmin config set-list profile.disciplines running cycling"],
        )
    )

    @app.command("set-list")
    def config_set_list(
        ctx: typer.Context,
        key: str = typer.Argument(..., help="Dot-notation config key."),
        values: list[str] = typer.Argument(..., help="Values for the list."),
    ) -> None:
        state = get_state(ctx)
        config_dict = _config_as_dict(state.config)
        _set_nested(config_dict, key, [_parse_value(v) for v in values])
        _apply_dict_to_config(state.config, config_dict)
        save_config(state.config)
        updated = load_config()
        emit_success(
            _config_as_dict(updated),
            {"cached": False, "fetched_at": None, "command": "config set-list"},
            output_format=state.options.output,
            fields=state.options.fields,
        )

    # --- config reset-profile ---
    registry.register(
        CommandSpec(
            name="config reset-profile",
            category="config",
            summary="Reset user profile to defaults.",
            description="Clears disciplines, primary goal, and sets onboarding_completed to false.",
            auth_required=False,
            cache_strategy="none",
            examples=["garmin config reset-profile"],
        )
    )

    @app.command("reset-profile")
    def config_reset_profile(ctx: typer.Context) -> None:
        state = get_state(ctx)
        state.config.profile = {
            "disciplines": [],
            "primary_goal": None,
            "onboarding_completed": False,
        }
        save_config(state.config)
        updated = load_config()
        emit_success(
            _config_as_dict(updated),
            {"cached": False, "fetched_at": None, "command": "config reset-profile"},
            output_format=state.options.output,
            fields=state.options.fields,
        )
```

- [ ] **Step 4: Wire config sub-typer in `cli.py`**

In `garmin_cli/cli.py`:

Add import at line 19 (alongside existing command imports):
```python
from .commands import activity, auth_cmds, body, config_cmds, gear, general, heart, recovery, sleep, training
```

After the `cache_app` creation (after line 56), add:
```python
    config_app = typer.Typer(help="View and update configuration.")
    app.add_typer(config_app, name="config")
```

After the existing `register()` calls (after line 146), add:
```python
    config_cmds.register(config_app, registry)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config_cmds.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Run full test suite**

Run: `pytest -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add garmin_cli/commands/config_cmds.py garmin_cli/cli.py tests/test_config_cmds.py
git commit -m "feat(config): add config show/set/set-list/reset-profile commands"
```

---

## Task 3: Update `references/cli.md` with config commands

**Files:**
- Modify: `skills/garmin-coach/references/cli.md`

- [ ] **Step 1: Add config commands to cli.md**

Add after the gear commands in the "High-value commands" section:

```markdown

## Config commands

- `garmin config show` — display current config (including profile and disciplines)
- `garmin config set <key> <value>` — set a config value (dot-notation, e.g., `profile.primary_goal`)
- `garmin config set-list <key> <values...>` — set a list value (e.g., `profile.disciplines running cycling`)
- `garmin config reset-profile` — reset profile to defaults and re-trigger onboarding
```

- [ ] **Step 2: Commit**

```bash
git add skills/garmin-coach/references/cli.md
git commit -m "docs(skill): add config commands to CLI reference"
```

---

## Task 4: Extract running-specific content into `references/running.md`

> **Note:** After this task, SKILL.md will have running-specific references in the weekly report template (Section 4, Section 5) that reference metrics now in `running.md`. This is intentional — Task 8 rewrites the templates to be discipline-aware and resolves the inconsistency.

**Files:**
- Create: `skills/garmin-coach/references/running.md`
- Modify: `skills/garmin-coach/SKILL.md`

- [ ] **Step 1: Create `references/running.md`**

Move the running-specific sections from SKILL.md into this new file. The content comes from the current SKILL.md sections: "Running Biomechanics", "Cardiac Drift", and "Intensity Distribution".

```markdown
# Running

Coaching heuristics for running-specific metrics. Loaded when the user's profile includes `running`.

## Biomechanics

- **Cadence:** 170–185 spm optimal. Below 160 = likely overstriding.
- **Ground contact time (GCT):** lower is better. <240ms good. >280ms flag it.
- **Vertical oscillation:** lower = more efficient. <8cm good. >10cm = "bouncing."
- **Stride length:** individual metric. Increasing at same cadence = genuine improvement. Increasing with lower cadence = possibly overstriding.
- **GCT balance:** should be close to 50/50. Imbalance >2% may indicate compensation.
- Always contextualize by pace — form metrics change with speed.

## Cardiac Drift

- Calculate from activity splits: (avg HR last third) / (avg HR first third) - 1
- <5% in steady-state run: excellent aerobic fitness
- 5–10%: normal
- >10%: dehydration, insufficient base, or fatigue

## Intensity Distribution (80/20)

- Zone 1–2: should be ~80% of weekly time
- Zone 3: the "grey zone" — minimize this. Too hard to recover, too easy to improve.
- Zone 4–5: should be ~20% of weekly time
- If zone 3 > 30% of training time, flag it

## Workout Analysis

- For key runs, analyze splits: even pacing? negative split? fade?
- Calculate cardiac drift from first-third vs last-third avg HR
- Top sessions by training effect: distance, pace, avg/max HR, cadence, GCT, vertical oscillation
- For the weekly report biomechanics section: report week averages for cadence, GCT, vertical oscillation, stride length. Compare vs 4-week average. Spotlight the ONE metric moving most notably.
```

- [ ] **Step 2: Remove running-specific sections from SKILL.md**

Remove these sections from SKILL.md:
- "Running Biomechanics (the user cares about these)" (lines 85–92)
- "Cardiac Drift" (lines 94–99)
- "Intensity Distribution (80/20)" (lines 101–106)

Replace with a one-liner in the Key Metrics section:
```markdown
### Running, Cycling, and Gym Metrics

Loaded from discipline-specific references. See the "Loading References" section below.
```

- [ ] **Step 3: Commit**

```bash
git add skills/garmin-coach/references/running.md skills/garmin-coach/SKILL.md
git commit -m "refactor(skill): extract running metrics into references/running.md"
```

---

## Task 5: Create `references/cycling.md`

**Files:**
- Create: `skills/garmin-coach/references/cycling.md`

- [ ] **Step 1: Write cycling reference**

Use the @skill-creator skill to write this reference. It should cover the topics listed in the spec: power metrics, cycling cadence, HR decoupling, climbing analysis, endurance ride analysis. Follow the same tone and format as `running.md`.

- [ ] **Step 2: Verify content covers all spec topics**

Confirm the file includes sections for:
- Power metrics (FTP, normalized power, intensity factor, TSS)
- Cycling cadence (optimal ranges, climbing vs flat)
- Heart rate decoupling (aerobic efficiency for rides)
- Climbing analysis (VAM, power-to-weight)
- Endurance ride analysis (pacing, nutrition signals from power fade)

- [ ] **Step 3: Commit**

```bash
git add skills/garmin-coach/references/cycling.md
git commit -m "feat(skill): add cycling discipline reference"
```

---

## Task 6: Create `references/gym.md`

**Files:**
- Create: `skills/garmin-coach/references/gym.md`

- [ ] **Step 1: Write gym reference**

Use the @skill-creator skill to write this reference. It should cover: volume tracking, progressive overload, complementary strength for endurance athletes, recovery impact. Follow the same tone and format as `running.md`.

- [ ] **Step 2: Verify content covers all spec topics**

Confirm the file includes sections for:
- Volume tracking (sets x reps x load per muscle group)
- Progressive overload signals
- Complementary strength for runners/cyclists (what to look for)
- Recovery impact on training readiness

- [ ] **Step 3: Commit**

```bash
git add skills/garmin-coach/references/gym.md
git commit -m "feat(skill): add gym discipline reference"
```

---

## Task 7: Create `references/goals.md`

**Files:**
- Create: `skills/garmin-coach/references/goals.md`

- [ ] **Step 1: Write goals reference**

Use the @skill-creator skill to write this reference. It must contain the full goal catalog from the spec (running, cycling, gym goals in Spanish) and for each goal, a "coaching emphasis" section that tells the agent what to prioritize. Follow the structure shown in the spec's `goals.md` section.

- [ ] **Step 2: Verify content covers all spec goals**

Confirm the file includes coaching emphasis for each goal:

Running:
- Correr más rápido (PR focus)
- Prepararse para una carrera
- Construir base aeróbica
- Volver de una lesión
- Mantener consistencia

Cycling:
- Mejorar FTP / potencia sostenida
- Prepararse para un evento
- Construir resistencia para rutas largas
- Mantener consistencia y salud

Gym:
- Complementar rendimiento en running o ciclismo
- Fitness general y composición corporal
- Prevención de lesiones / movilidad

- [ ] **Step 3: Commit**

```bash
git add skills/garmin-coach/references/goals.md
git commit -m "feat(skill): add goals reference with coaching emphasis"
```

---

## Task 8: Rewrite SKILL.md with onboarding and discipline-aware templates

**Files:**
- Modify: `skills/garmin-coach/SKILL.md`

This is the core skill rewrite. Use the @skill-creator skill for this task.

- [ ] **Step 1: Rewrite SKILL.md**

The new SKILL.md must contain these sections (in order):

1. **YAML front matter** — update description to mention multi-discipline support
2. **Persona** — update from "running coach" to "training coach" covering running, cycling, and gym
3. **Language policy** — unchanged
4. **Operating model** — unchanged
5. **Onboarding** (new) — full onboarding flow from spec Section 2:
   - Trigger: check `garmin config show`, run onboarding if `onboarding_completed` is false or profile missing
   - Conversation flow in Spanish by default: introduce → disciplines → goal (with custom option) → if event goal, ask for date → persist via config commands → confirm
   - Goal suggestions per discipline (from spec)
   - Profile update instructions (no need to re-run full onboarding)
   - Nudge behavior
6. **Loading references** (new) — instructions for the agent:
   - Read user profile with `garmin config show`
   - Load `references/running.md`, `references/cycling.md`, `references/gym.md` matching `profile.disciplines`
   - Always load `references/goals.md`
7. **CLI usage** — unchanged, still points to `references/cli.md`
8. **Shared metrics** — HRV, training load/ACWR, training status, sleep, body battery (keep these — they're universal)
9. **Morning brief template** — unchanged (recovery is universal)
10. **Weekly report template** — make Sections 4 and 5 discipline-aware:
    - Section 4 "Key Workout Analysis": "for runs, analyze per `running.md`; for rides, per `cycling.md`; for gym, per `gym.md`"
    - Section 5: rename to "Discipline-Specific Analysis" — defer to loaded discipline references
11. **Race readiness check** — unchanged
12. **Compare to last week** — unchanged
13. **Shoe mileage check** — unchanged
14. **Analysis priorities** — update fourth tier from "running mechanics" to "discipline-specific mechanics"
15. **Guardrails** — unchanged

- [ ] **Step 2: Commit**

```bash
git add skills/garmin-coach/SKILL.md
git commit -m "feat(skill): add onboarding, multi-discipline support, and reference loading"
```

---

## Task 9: Final integration verification

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests pass

- [ ] **Step 2: Verify CLI config commands work end-to-end**

Run manually:
```bash
garmin config show
garmin config set-list profile.disciplines running cycling
garmin config set profile.primary_goal "Prepararse para un medio maratón"
garmin config set profile.onboarding_completed true
garmin config show
garmin config reset-profile
garmin config show
```

Verify JSON envelopes are correct and config.json persists changes.

- [ ] **Step 3: Verify schema includes config commands**

Run: `garmin schema`
Expected: `config show`, `config set`, `config set-list`, `config reset-profile` all present

- [ ] **Step 4: Verify skill file structure**

Check that all files exist:
```bash
ls skills/garmin-coach/SKILL.md
ls skills/garmin-coach/references/cli.md
ls skills/garmin-coach/references/running.md
ls skills/garmin-coach/references/cycling.md
ls skills/garmin-coach/references/gym.md
ls skills/garmin-coach/references/goals.md
```

- [ ] **Step 5: Push**

```bash
git push
```

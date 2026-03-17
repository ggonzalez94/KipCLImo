# Multi-Discipline Support & Guided Onboarding

**Date:** 2026-03-17
**Status:** Design approved

---

## Summary

Expand KipCLImo from a running-only tool to support multiple sport disciplines (running, cycling, gym). Add a guided onboarding flow driven by the agent skill that personalizes the coaching experience based on the user's disciplines and primary goal. Restructure the skill into a base file plus discipline-specific references.

---

## 1. Config Commands

Four new commands under `garmin config`, following existing CLI conventions (JSON envelope, exit codes, schema registry).

### Commands

| Command | Arguments | Description |
|---|---|---|
| `garmin config show` | — | Return full config as JSON envelope |
| `garmin config set` | `<key> <value>` | Set a scalar config value using dot-notation keys |
| `garmin config set-list` | `<key> <values...>` | Set a list config value |
| `garmin config reset-profile` | — | Clear `profile` block, set `onboarding_completed: false` |

### Implementation

- New file: `garmin_cli/commands/config_cmds.py`
- Follows the `register(app, registry)` pattern used by all command modules
- Wiring in `cli.py`:
  1. Create `config_app = typer.Typer(name="config", ...)`
  2. Call `app.add_typer(config_app, name="config")`
  3. Call `config_cmds.register(config_app, registry)` alongside the other `register()` calls
- `config set` uses dot-notation to traverse nested keys (e.g., `profile.primary_goal`). Intermediate keys are created if they don't exist. Values are parsed via `json.loads()` with fallback to string — this ensures booleans (`true`/`false`), numbers, and `null` are stored as their JSON types, not as strings.
- `config set-list` accepts variadic args and stores as a JSON array
- `config reset-profile` resets the `profile` field to its default value: `{"disciplines": [], "primary_goal": null, "onboarding_completed": false}`
- All commands read/write through `AppConfig` in `config.py` — no direct file manipulation in command handlers

### Schema Registry Entries

All four config commands are registered with `CommandSpec`:
- `category`: `"config"`
- `auth_required`: `False`
- `cache_strategy`: `"none"`

### Required Changes to `config.py`

- Add `profile` field to `AppConfig` dataclass: `profile: dict[str, Any] = field(default_factory=lambda: {"disciplines": [], "primary_goal": None, "onboarding_completed": False})`
- Update `load_config()` to deserialize the `profile` key from JSON (with default if missing)
- Update `save_config()` to serialize the `profile` field into the JSON payload — the current implementation manually enumerates fields and would silently drop `profile` without this change

### Config Schema

`~/.garmin-cli/config.json` gains a `profile` block:

```json
{
  "timezone": "America/New_York",
  "units": "metric",
  "cache_dir": "~/.garmin-cli",
  "races": [],
  "hr_zones": { "source": "garmin", "custom": null },
  "profile": {
    "disciplines": ["running", "cycling"],
    "primary_goal": "Correr un medio maratón",
    "onboarding_completed": true
  }
}
```

- `disciplines`: list of strings, valid values: `running`, `cycling`, `gym`
- `primary_goal`: free-text string (user can pick from suggestions or write their own)
- `onboarding_completed`: boolean, drives onboarding trigger in the skill

`AppConfig` in `config.py` gains a `profile` field (dataclass or dict). Missing `profile` key is equivalent to `onboarding_completed: false`.

---

## 2. Onboarding Flow

The onboarding is entirely agent-driven, defined in the skill. The CLI provides the config commands; the skill provides the conversation logic.

### Trigger

When the agent reads `garmin config show` and sees `profile` is missing or `onboarding_completed` is `false`, it runs onboarding before doing anything else.

### Conversation (in Spanish by default)

1. **Introduce** — the agent introduces itself as a training coach and explains it needs a few things to personalize the experience.
2. **Disciplines** — ask which disciplines the user practices. Options: running, cycling, gym. User can pick multiple.
3. **Primary goal** — based on selected disciplines, present relevant goal suggestions. User picks one OR writes their own. If the goal is an event, the coach should ask when that event is happening. This is important to help the user prepare for the event.
4. **Persist** — agent calls:
   - `garmin config set-list profile.disciplines running cycling`
   - `garmin config set profile.primary_goal "Correr un medio maratón"`
   - `garmin config set profile.onboarding_completed true`
5. **Confirm** — summarize what was configured. Tell the user they can change it anytime by asking.

### Goal Suggestions

Presented based on selected disciplines:

**Running:**
- Correr más rápido en una distancia específica (PR)
- Prepararse para una carrera (5K / 10K / medio maratón / maratón / ultra)
- Construir base aeróbica / aumentar volumen semanal de forma segura
- Volver de una lesión sin recaídas
- Mantener consistencia y salud (sin objetivo específico)

**Cycling:**
- Mejorar FTP / potencia sostenida
- Prepararse para un evento (gran fondo, carrera, tour)
- Construir resistencia para rutas largas
- Mantener consistencia y salud

**Gym / Strength:**
- Complementar rendimiento en running o ciclismo
- Fitness general y composición corporal
- Prevención de lesiones / movilidad

If none apply, the user can type their own goal as free text.

### Profile Updates

No need to re-run full onboarding. If the user says "quiero cambiar mi objetivo" or "empecé a hacer ciclismo", the agent calls the appropriate `garmin config set` / `garmin config set-list` command directly.

### Nudge Behavior

If the user asks something discipline-specific before completing onboarding, the agent answers the question but nudges them to complete onboarding so future advice is personalized.

---

## 3. Skill Architecture

### File Structure

```
skills/garmin-coach/
├── SKILL.md                  # Base: persona, language, onboarding, report templates,
│                             #   recovery/readiness, analysis priorities, guardrails
├── references/
│   ├── cli.md                # Command inventory (exists today, add config commands)
│   ├── running.md            # Running: biomechanics, pacing, cardiac drift, intensity
│   ├── cycling.md            # Cycling: power, FTP, cadence, climbing, endurance
│   ├── gym.md                # Gym: volume, progression, complementary strength
│   └── goals.md              # Goal catalog + coaching emphasis per goal
```

### How the Agent Loads References

The skill instructs the agent:

> Read the user's profile with `garmin config show`.
> Load the discipline references that match `profile.disciplines`.
> Always load `goals.md` to understand how the primary goal shapes your advice.

A runner+cyclist loads `running.md` + `cycling.md` + `goals.md`.
A pure runner loads `running.md` + `goals.md`.
The agent never reads discipline references that don't apply.

### What Moves Out of SKILL.md

The current SKILL.md has running-specific content that moves to `references/running.md`:

- Running Biomechanics section (cadence, GCT, vertical oscillation, stride length, GCT balance)
- Cardiac Drift section
- Intensity Distribution (80/20) section
- Running-specific parts of report templates (splits analysis, form spotlight)

### What Stays in SKILL.md

- Persona and language policy
- Onboarding section (new)
- Operating model and CLI usage
- Shared metrics: HRV, training load/ACWR, training status, sleep, body battery
- Report templates (morning brief + weekly report) — made discipline-aware
- Race readiness check, compare to last week, shoe mileage check
- Analysis priorities and guardrails

### Discipline-Aware Report Templates

Report templates stay in SKILL.md but become adaptive:

- **Morning brief:** unchanged — recovery and readiness are universal
- **Weekly report Section 4 (Key Workout Analysis):** the skill says "for runs, analyze splits and cardiac drift per `running.md`; for rides, analyze power and pacing per `cycling.md`; for gym sessions, analyze volume and progression per `gym.md`"
- **Weekly report Section 5:** renamed from "Running Form / Biomechanics" to "Discipline-Specific Analysis" — the skill defers to the loaded discipline references for what to spotlight

### goals.md Structure

```markdown
# Goals

## How Goals Shape Coaching

The user's primary goal determines what you emphasize when synthesizing advice.
Always reference the goal when making recommendations.

## Running Goals

### Correr más rápido (PR focus)
Emphasis: interval quality, pace progression, race predictions trend, VO2max trajectory.

### Prepararse para una carrera
Emphasis: long run progression, endurance score, race predictions vs target, taper readiness, weekly volume ramp.

### Construir base aeróbica
Emphasis: volume trends, intensity distribution (protect 80/20), aerobic HR drift improvement, consistency.

### Volver de una lesión
Emphasis: conservative load monitoring, ACWR below 1.2, recovery signals, asymmetry/GCT balance, flag any rapid volume jumps.

### Mantener consistencia
Emphasis: consistency streaks, recovery balance, avoid overreaching, general health signals.

## Cycling Goals
[same pattern]

## Gym Goals
[same pattern]
```

### references/running.md

Contains everything currently in SKILL.md that is running-specific:

- Running biomechanics (cadence, GCT, vertical oscillation, stride length, GCT balance with thresholds)
- Cardiac drift (calculation formula, thresholds)
- Intensity distribution (80/20 rule, zone 3 flag)
- Running-specific workout analysis guidance (splits, pacing patterns, negative split detection)

### references/cycling.md

New content covering:

- Power metrics (FTP, normalized power, intensity factor, TSS)
- Cycling cadence (optimal ranges, climbing vs flat)
- Heart rate decoupling (aerobic efficiency for rides)
- Climbing analysis (VAM, power-to-weight)
- Endurance ride analysis (pacing, nutrition signals from power fade)

### references/gym.md

New content covering:

- Volume tracking (sets x reps x load per muscle group)
- Progressive overload signals
- Complementary strength for runners/cyclists (what to look for)
- Recovery impact on training readiness

---

## 4. What Does NOT Change

- JSON envelope shape
- Exit codes
- Cache tables or cache logic
- Auth flow
- Any existing commands
- The `garmin` CLI entry point
- The install flow (`python scripts/install_skill.py`)

---

## 5. Build Sequence

### Phase 1: Config commands
- Add `profile` field to `AppConfig` dataclass with default
- Update `load_config()` to deserialize `profile` (default if missing)
- Update `save_config()` to serialize `profile` into the JSON payload
- Create `commands/config_cmds.py` with `show`, `set`, `set-list`, `reset-profile`
- Wire `config_app` sub-typer in `cli.py` and call `config_cmds.register(config_app, registry)`
- Register all four commands in schema registry
- Update `references/cli.md` with new config commands
- Add tests: set, set-list (with type coercion), show, reset-profile, dot-notation, missing profile default

### Phase 2: Skill restructure
- Extract running-specific content from SKILL.md into `references/running.md`
- Write `references/cycling.md`
- Write `references/gym.md`
- Write `references/goals.md`
- Update SKILL.md: add onboarding section, make templates discipline-aware, add reference-loading instructions

### Phase 3: Integration test
- Manual test: run onboarding with an agent end-to-end

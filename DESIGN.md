# garmin-cli — Design Document

> AI-powered training analytics for advanced amateur runners.
> Not a plan manager — an insights engine.

**Date:** 2026-03-16
**Status:** Design phase

---

## 1. Product Vision

An advanced amateur runner generates rich data from their Garmin watch but lacks the
time or expertise to synthesize it into actionable insight. Garmin's own analysis is
generic and buried in an app designed for everyone.

**garmin-cli** is a thin, agent-friendly CLI that wraps the Garmin Connect API, paired
with an AI coaching layer (via OpenClaw or any LLM agent) that interprets the data
through the lens of *your* training. It answers: "Is what I'm doing working? What
should I adjust?"

### Target User

- Advanced amateur runner (knows what VO2max, ACWR, cadence mean)
- Already has a training routine and plan
- Tracks everything with a Garmin watch
- Wants insight, not prescription
- Has other things in life — needs information delivered, not sought

### What This Is NOT

- Not a training plan generator
- Not a periodization manager
- Not a Garmin Connect replacement (no social, courses, or device management)

---

## 2. System Architecture

```
┌───────────────────────────────────────────────────────┐
│               AI AGENT LAYER (any agent)              │
│     OpenClaw / Claude Code / any LLM agent            │
│                                                       │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │Morning Brief│  │ Weekly   │  │  Interactive     │  │
│  │ 7am daily   │  │ Report   │  │  Chat / Query    │  │
│  │ (OC cron)   │  │(OC cron) │  │  (any agent)     │  │
│  └──────┬──────┘  └────┬─────┘  └───────┬─────────┘  │
│         └──────────────┼────────────────┘             │
│                        │                              │
│              CLI subprocess calls                     │
└────────────────────────┼──────────────────────────────┘
                         │
┌────────────────────────┼──────────────────────────────┐
│                  garmin-cli (Python)                   │
│                                                       │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │  Auth     │  │ Commands  │  │ Output Formatter │   │
│  │  Manager  │  │  27 cmds  │  │ JSON / Human     │   │
│  │  (garth)  │  │ (1:1 API) │  │ stable envelope  │   │
│  └──────────┘  └─────┬─────┘  └──────────────────┘   │
│                      │                                │
│  ┌───────────────────┴────────────────┐               │
│  │ SQLite Cache                       │               │
│  │ ~/.garmin-cli/cache.db             │               │
│  │                                    │               │
│  │ Past dates → serve from cache      │               │
│  │ Today → always fetch fresh         │               │
│  │ --no-cache → bypass                │               │
│  │ --refresh → force fetch + update   │               │
│  └───────────────────┬────────────────┘               │
│                      │                                │
│               python-garminconnect                    │
└──────────────────────┼────────────────────────────────┘
                       │
                ┌──────┴──────┐
                │ Garmin API  │
                │ connect.    │
                │ garmin.com  │
                └─────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| CLI vs MCP | CLI only | Agent-agnostic. Works with OpenClaw, Claude Code, any agent. Replaces existing garmin MCP. |
| Thin vs smart CLI | Thin (1:1 API) | Intelligence lives in the AI prompt, not the CLI. CLI is a data access layer. |
| Output format | JSON default | Machine-readable first. `--human` flag for terminal use. Auto-detect TTY. |
| Cache | SQLite | Enables trend queries, reduces API calls, faster than 120+ round-trips for weekly report. |
| Python framework | Typer | Modern, type hints, auto-generated help, built on Click. |
| Auth | garth OAuth tokens | File-based persistence at `~/.garmin-cli/tokens`. No browser needed after first login. |

---

## 3. CLI Design

### 3.1 Global Flags

| Flag | Short | Default | Description |
|---|---|---|---|
| `--output` | `-o` | auto | Output format: `json`, `human`. Auto-detects: JSON when piped, human when TTY. Env var fallback: `GARMIN_OUTPUT=json\|human`. |
| `--no-cache` | | off | Bypass SQLite cache, hit Garmin API |
| `--refresh` | | off | Fetch fresh data AND update cache |
| `--fields` | `-f` | all | Comma-separated field selection (context window discipline) |
| `--verbose` | `-v` | off | Debug info to stderr |

**Output auto-detection (per agent-cli-design):**
- stdout is a TTY (you in terminal) → human-readable
- stdout is piped (agent subprocess) → JSON
- `--output json` or `-o json` → force JSON
- `--output human` or `-o human` → force human
- `GARMIN_OUTPUT=json` env var → override default

### 3.2 JSON Envelope

Every command returns a stable envelope. Agents can always parse the same structure.

**Success:**
```json
{
  "status": "ok",
  "data": { ... },
  "metadata": {
    "cached": true,
    "fetched_at": "2026-03-16T07:00:12Z",
    "command": "sleep",
    "date": "2026-03-16"
  }
}
```

**Error:**
```json
{
  "status": "error",
  "error": {
    "code": "AUTH_ERROR",
    "message": "Token expired. Run `garmin login` to re-authenticate."
  },
  "metadata": {}
}
```

### 3.3 Exit Codes

| Code | Meaning | Agent action |
|---|---|---|
| 0 | Success | Parse data |
| 1 | General error | Read error.message |
| 2 | Usage / input error | Fix command syntax |
| 3 | Auth error | Run `garmin login` |
| 4 | Not found | Data not available for this date/ID |
| 5 | Rate limited (429) | Wait and retry |

### 3.4 Command Inventory

All dates use ISO 8601 format: `YYYY-MM-DD`. "Today" is the default when date is optional.

#### Auth & System

| Command | Arguments | Description |
|---|---|---|
| `garmin login` | `[--email] [--password]` | Interactive login + token storage. Supports `GARMIN_EMAIL` / `GARMIN_PASSWORD` env vars. |
| `garmin status` | | Check auth status, token validity, last sync time |
| `garmin schema [command]` | `[command_name]` | Runtime introspection. Returns JSON with all commands, flags, types, descriptions. |

#### Sleep

| Command | Arguments | Returns |
|---|---|---|
| `garmin sleep <date>` | date (required) | Sleep score, duration, stages (deep/light/REM/awake %), start/end times, HRV during sleep, respiration, SpO2, restless moments |

#### Heart Rate & HRV

| Command | Arguments | Returns |
|---|---|---|
| `garmin heart-rate <date>` | date | Resting HR, min/max HR, HR time-series, zone time breakdown |
| `garmin hrv <date>` | date | Last night avg, weekly avg, 5-min high, baseline (low/balanced), status |

#### Recovery

| Command | Arguments | Returns |
|---|---|---|
| `garmin stress <date>` | date | Avg stress, max stress, stress time-series, rest/activity stress duration |
| `garmin body-battery <start> [end]` | start, optional end | Daily charged/drained values, time-series, events (sleep/activity impact) |
| `garmin respiration <date>` | date | Avg sleep/waking respiration, highest/lowest |
| `garmin spo2 <date>` | date | Avg SpO2, lowest SpO2, readings time-series |

#### Activity

| Command | Arguments | Returns |
|---|---|---|
| `garmin activities` | `[--start] [--end] [--type running\|cycling\|...] [--limit 20]` | List of activities with summary: name, type, distance, duration, avg HR, avg pace, training effect, training load |
| `garmin activity <id>` | activity_id | Full activity summary: distance, duration, pace, HR (avg/max), cadence, GCT, vertical oscillation, stride length, power, training effect (aerobic/anaerobic), calories, elevation, weather |
| `garmin activity-details <id>` | activity_id | Detailed metrics + chart data + GPS polyline. Use `--fields` to limit. |
| `garmin activity-splits <id>` | activity_id | Per-lap: distance, time, pace, HR, cadence, elevation |
| `garmin activity-hr-zones <id>` | activity_id | Time in each HR zone for this activity |
| `garmin activity-weather <id>` | activity_id | Temperature, humidity, wind, conditions during activity |

#### Training Metrics

| Command | Arguments | Returns |
|---|---|---|
| `garmin training-readiness <date>` | date | Readiness score (0-100), contributing factors: sleep score, sleep history, recovery time, HRV status, training load, stress history |
| `garmin training-status <date>` | date | Status label (Productive/Maintaining/Peaking/Recovery/Unproductive/Detraining/Overreaching), acute load, chronic load, load focus (aerobic/anaerobic shortage/surplus) |
| `garmin vo2max <date>` | date | VO2max value, fitness level descriptor |
| `garmin race-predictions` | `[--start] [--end] [--latest]` | Predicted finish times: 5K, 10K, half marathon, marathon |
| `garmin endurance-score <start> [end]` | start, optional end | Endurance score value, daily/weekly stats |
| `garmin fitness-age <date>` | date | Fitness age vs chronological age, contributing components |

#### Body Composition

| Command | Arguments | Returns |
|---|---|---|
| `garmin body-composition <start> [end]` | start, optional end | Weight, BMI, body fat %, body water, bone mass, muscle mass, metabolic age, visceral fat |
| `garmin weigh-ins <start> <end>` | start, end | Raw weigh-in records with timestamps |

#### General

| Command | Arguments | Returns |
|---|---|---|
| `garmin user-summary <date>` | date | Steps, distance, calories (total/active), floors, intensity minutes (moderate/vigorous), resting HR, avg stress, body battery high/low |
| `garmin steps <start> <end>` | start, end | Daily step counts, distances, averages over range |
| `garmin personal-records` | | PRs: fastest km, fastest mile, longest run, fastest 5K/10K/HM/M |

#### Gear

| Command | Arguments | Returns |
|---|---|---|
| `garmin gear` | | All gear with name, type, date added, total distance, total activities |
| `garmin gear-stats <uuid>` | gear UUID | Detailed stats + activity list for specific gear |

---

## 4. SQLite Cache Design

**Location:** `~/.garmin-cli/cache.db`

### Schema

```sql
-- Daily metrics (one row per date per metric type)
CREATE TABLE daily_cache (
    date       TEXT NOT NULL,      -- YYYY-MM-DD
    metric     TEXT NOT NULL,      -- sleep, hrv, stress, heart_rate, body_battery,
                                   -- training_readiness, training_status, vo2max,
                                   -- user_summary, respiration, spo2, fitness_age
    data       TEXT NOT NULL,      -- JSON blob (raw Garmin API response)
    fetched_at TEXT NOT NULL,      -- ISO 8601 timestamp
    PRIMARY KEY (date, metric)
);

-- Activity summaries (from list queries)
CREATE TABLE activity_cache (
    activity_id TEXT PRIMARY KEY,
    date        TEXT NOT NULL,     -- activity date for indexing
    type        TEXT,              -- running, cycling, etc.
    summary     TEXT NOT NULL,     -- JSON blob (activity summary)
    fetched_at  TEXT NOT NULL
);

-- Activity details (detailed metrics, splits, HR zones)
CREATE TABLE activity_detail_cache (
    activity_id TEXT NOT NULL,
    detail_type TEXT NOT NULL,     -- details, splits, hr_zones, weather
    data        TEXT NOT NULL,     -- JSON blob
    fetched_at  TEXT NOT NULL,
    PRIMARY KEY (activity_id, detail_type)
);

-- Range queries (race predictions, endurance score, etc.)
CREATE TABLE range_cache (
    cache_key   TEXT PRIMARY KEY,  -- e.g., "race_predictions:latest" or "steps:2026-03-09:2026-03-16"
    data        TEXT NOT NULL,     -- JSON blob
    fetched_at  TEXT NOT NULL
);

-- Index for date-range queries on daily data
CREATE INDEX idx_daily_date ON daily_cache(date);
CREATE INDEX idx_daily_metric ON daily_cache(metric, date);
CREATE INDEX idx_activity_date ON activity_cache(date);
```

### Cache Rules

| Scenario | Behavior |
|---|---|
| Requesting past date (before today) | Serve from cache if exists. Past data is immutable. |
| Requesting today | Always fetch fresh (data still updating throughout the day). |
| `--no-cache` flag | Skip cache entirely, hit API, do NOT update cache. |
| `--refresh` flag | Fetch fresh from API AND update cache (useful for correcting stale data). |
| Cache miss (past date) | Fetch from API, store in cache, return. |
| Range queries | Cache the range result. Individual day data also cached from daily calls. |

### Maintenance

```sql
-- CLI command: garmin cache stats
-- Shows: total rows, DB size, oldest entry, metric breakdown

-- CLI command: garmin cache clear [--before DATE] [--metric TYPE]
-- Selective or full cache clearing
```

---

## 5. Authentication

### Flow

```
First time:
  garmin login --email user@example.com --password ***
      │
      ├─ garth.login(email, password)
      ├─ Handle MFA if required (prompt user)
      ├─ Save OAuth tokens to ~/.garmin-cli/tokens/
      └─ Verify: fetch user profile

Subsequent runs:
  Any garmin command
      │
      ├─ Load tokens from ~/.garmin-cli/tokens/
      ├─ garth auto-refreshes if needed
      └─ If refresh fails → exit code 3, "Run garmin login"
```

### Environment Variables

| Variable | Purpose |
|---|---|
| `GARMIN_EMAIL` | Login email (avoids interactive prompt) |
| `GARMIN_PASSWORD` | Login password (avoids interactive prompt) |
| `GARMIN_TOKENS` | Custom token storage path (default: `~/.garmin-cli/tokens`) |

### Security

- Tokens stored as files in `~/.garmin-cli/tokens/` with 600 permissions
- Password never stored — only OAuth tokens
- Token files are garth-format (OAuth refresh tokens, ~1 year validity)
- `.gitignore` includes token directory

---

## 6. Error Handling

### Garmin API Errors

| Error | Exception | CLI Behavior | Exit Code |
|---|---|---|---|
| Auth expired | `GarminConnectAuthenticationError` | "Token expired. Run `garmin login`" | 3 |
| Rate limited (429) | `GarminConnectTooManyRequestsError` | "Rate limited. Retry in {backoff}s" with auto-retry (3 attempts, exponential backoff) | 5 (if all retries fail) |
| Network error | `GarminConnectConnectionError` | "Connection failed: {details}" | 1 |
| No data | HTTP 204 / empty response | `{"status": "ok", "data": null, "metadata": {"note": "No data for this date"}}` | 0 |
| Invalid input | Typer validation | "Invalid date format. Use YYYY-MM-DD" | 2 |

### Rate Limit Strategy

```
Attempt 1 → fail 429 → wait 2s
Attempt 2 → fail 429 → wait 5s
Attempt 3 → fail 429 → wait 15s
Attempt 4 → give up, exit code 5
```

All retries logged to stderr. JSON output only emitted on final result.

---

## 7. Configuration

**Location:** `~/.garmin-cli/config.json`

```json
{
  "timezone": "America/New_York",
  "units": "metric",
  "cache_dir": "~/.garmin-cli",
  "races": [
    {
      "name": "Brooklyn Half Marathon",
      "date": "2026-05-15",
      "distance_km": 21.1
    }
  ],
  "hr_zones": {
    "source": "garmin",
    "custom": null
  }
}
```

The `races` array enables the race readiness feature. When an agent asks "Am I ready
for my race?", the CLI (or the skill prompt) can reference the configured race date
and distance.

---

## 8. OpenClaw Skill: garmin-coach

**Location:** `~/.openclaw/workspace/skills/garmin-coach/SKILL.md`

### Skill Design Philosophy

The skill is where the coaching intelligence lives. The CLI provides raw data;
the skill tells the AI how to interpret it, what to look for, and how to
communicate insights to a runner.

### SKILL.md Structure

```markdown
---
name: garmin_coach
description: "AI running coach that analyzes Garmin training data. Use when the user
asks about their health, workouts, sleep, training, recovery, running form, race
readiness, or wants their morning brief or weekly report. Wraps the garmin-cli tool."
---

# Garmin Coach Skill

You are a knowledgeable running coach analyzing the user's Garmin training data.
The user is an advanced amateur runner who already has a training plan. Your job is
to provide insight, not prescription. Help them understand what their data means and
what's working or not.

## Persona

- Speak like a smart, experienced running coach — direct, data-informed, no fluff
- Use actual numbers from the data, not vague qualifiers
- Highlight what's notable (good or concerning), skip what's normal
- When something is trending, say the direction and magnitude
- Be honest about bad signals — don't sugarcoat

## CLI Commands Available

[Full command reference with examples — all 27 commands listed with
when to use each and what fields matter most for coaching]

## Key Metrics Interpretation Guide

### HRV (Heart Rate Variability)
- Higher is generally better, but TREND matters more than absolute value
- 7-day rolling average is the key metric — compare lastNightAvg to weeklyAvg
- Drop below baseline = cumulative fatigue or illness incoming
- Consistently above baseline = good recovery, ready for harder work

### Training Load (ACWR — Acute:Chronic Workload Ratio)
- Sweet spot: 0.8–1.3
- Below 0.8: undertraining / detraining risk
- 1.0–1.3: building fitness safely
- Above 1.3: elevated injury risk
- Above 1.5: danger zone — call it out clearly

### Training Status
- Productive → good: fitness is improving
- Maintaining → neutral: holding steady
- Peaking → great: fitness is at its highest
- Recovery → expected after hard block or race
- Unproductive → warning: training hard but fitness declining
- Detraining → warning: losing fitness
- Overreaching → danger: too much too fast

### Sleep
- Score 80+ is good, 90+ is excellent
- Deep sleep: 15-20% is ideal, >20% is great
- REM: 20-25% is ideal
- Consistency across the week matters more than one great night

### Body Battery
- Morning charge >75: well recovered
- Morning charge 50-75: adequate
- Morning charge <50: poorly recovered — flag it
- Declining morning charges over days = cumulative fatigue

### Running Biomechanics (the user cares about these)
- Cadence: 170-185 spm optimal. Below 160 = likely overstriding.
- Ground contact time (GCT): lower is better. <240ms good. >280ms flag it.
- Vertical oscillation: lower = more efficient. <8cm good. >10cm = "bouncing"
- Stride length: individual metric. Increasing at same cadence = genuine improvement.
  Increasing with lower cadence = possibly overstriding.
- GCT balance: should be close to 50/50. Imbalance >2% may indicate compensation.
- Always contextualize by pace — form metrics change with speed.

### Cardiac Drift
- Calculate from activity splits: (avg HR last third) / (avg HR first third) - 1
- <5% in steady-state run: excellent aerobic fitness
- 5-10%: normal
- >10%: dehydration, insufficient base, or fatigue

### Intensity Distribution (80/20)
- Zone 1-2: should be ~80% of weekly time
- Zone 3: the "grey zone" — minimize this. Too hard to recover, too easy to improve.
- Zone 4-5: should be ~20% of weekly time
- If zone 3 > 30% of training time, flag it

## Morning Brief Template

Pull: sleep, hrv, training-readiness, training-status, body-battery, stress,
yesterday's activities (if any).

Format: 4-5 sentences, conversational, data-dense. Structure:
1. Sleep headline (score, duration, notable stages)
2. Recovery signal (HRV vs baseline, readiness score, what's dragging it)
3. Training load status (ACWR, load focus, any gaps)
4. Today's nudge (based on readiness + load: push, maintain, or rest)

If yesterday had a workout, weave in a one-line assessment.

## Weekly Report Template

Pull: 7 days of activities, sleep, HRV, training readiness, training status,
body battery, stress, steps. Plus: race predictions, VO2max, endurance score.
For each run: activity details, splits, HR zones.

### Section 1: Volume & Consistency
- Total distance (km), total time, number of sessions
- Delta vs last week (% change)
- Delta vs 4-week rolling average
- Days trained vs days planned (if known)

### Section 2: Intensity Distribution
- Total time in each HR zone across all activities
- Polarization check: % easy (zone 1-2) vs % hard (zone 4-5) vs % grey (zone 3)
- Flag if zone 3 exceeds 30%

### Section 3: Training Load & Fitness
- Acute Training Load (this week)
- Chronic Training Load
- ACWR ratio + interpretation
- Garmin training status label
- Load focus: aerobic vs anaerobic (flag shortages)

### Section 4: Key Workout Analysis
- Top 2-3 sessions by training effect
- For each: distance, pace, avg/max HR, cadence, GCT, vertical oscillation
- Splits analysis: even pacing? negative split? fade?
- Cardiac drift calculation
- What went well / what was hard

### Section 5: Running Form / Biomechanics
- Week averages: cadence, GCT, vertical oscillation, stride length
- Trend vs 4-week average for each metric
- SPOTLIGHT: pick the ONE metric moving most notably (good or bad)
  and explain what it means and how to work on it
- Note any correlations (e.g., cadence up → GCT down)

### Section 6: Recovery & Readiness
- Sleep: avg score, avg duration, deep sleep %, night-to-night consistency
- HRV: avg this week, trend (rising/falling/stable), vs baseline
- Resting HR: avg, trend
- Body battery: avg morning charge, trend
- Overall recovery verdict: well recovered / adequate / fatigued

### Section 7: Race Readiness Pulse
- Current race predictions (5K, 10K, HM, M)
- VO2max: current value and trend (4-week)
- Endurance score trend
- If race configured: weeks remaining, one-line readiness assessment

### Section 8: The Coach's Note
- 3-5 sentences synthesizing everything above
- What's working well (reinforce)
- What to watch (early warnings)
- One specific focus for next week

## Race Readiness Check

When user asks "Am I ready for [race]?", pull:
- race-predictions (compare predicted time to goal)
- vo2max (trend over past 4 weeks)
- training-status (current status + ACWR)
- endurance-score (trend)
- Last 3-4 long runs (distance, pace, HR, cardiac drift)
- Sleep + HRV trends (past 2 weeks)
- Body composition trend (if relevant)

Synthesize into: current fitness assessment, strengths, concerns,
and a realistic prediction with confidence level.

## Compare to Last Week

Pull identical data sets for this week and last week.
Present as a side-by-side comparison with deltas.
Highlight the 3 most significant changes (good or bad).
```

---

## 9. OpenClaw Cron Configuration

### Morning Brief (daily at 7am)

```bash
openclaw cron add \
  --name "Garmin Morning Brief" \
  --cron "0 7 * * *" \
  --tz "America/New_York" \
  --session isolated \
  --message "Generate my morning training brief. Use the garmin-coach skill. Pull today's sleep, HRV, training readiness, training status, body battery, stress, and yesterday's activities. Synthesize into a 4-5 sentence brief following the morning brief template." \
  --announce \
  --channel whatsapp \
  --to "+1XXXXXXXXXX"
```

### Weekly Report (Monday 8am)

```bash
openclaw cron add \
  --name "Garmin Weekly Report" \
  --cron "0 8 * * 1" \
  --tz "America/New_York" \
  --session isolated \
  --model opus \
  --thinking high \
  --message "Generate my weekly training report. Use the garmin-coach skill. Pull the past 7 days of activities, sleep, HRV, training readiness, training status, body battery, and stress. For each run, pull activity details, splits, and HR zones. Also pull race predictions, VO2max, and endurance score. Generate the full weekly report following all 8 sections in the template. Include 4-week rolling comparisons where specified." \
  --announce \
  --channel whatsapp \
  --to "+1XXXXXXXXXX"
```

---

## 10. Ad-Hoc Features

### Race Readiness Check

Triggered by natural language: "Am I ready for my half marathon?"

The agent (via skill) will:
1. Read race config from `~/.garmin-cli/config.json`
2. Pull: race predictions, VO2max (4-week), training status, endurance score,
   last 3-4 long runs with details, 2-week sleep + HRV trends
3. Synthesize into a readiness assessment

### Compare to Last Week

Triggered by: "Compare this week to last week" or "How does this week compare?"

The agent will:
1. Pull identical data for current and prior week
2. Compute deltas: volume, intensity distribution, sleep quality, HRV, training load
3. Present 3 most significant changes with context

### Shoe Mileage Check

Triggered by: "How are my shoes?" or "shoe mileage"

The agent will:
1. Pull `garmin gear` → filter running shoes
2. Surface total km per pair
3. Flag shoes approaching replacement threshold (~600-800km)

---

## 11. Project Structure

```
garmin-cli/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── DESIGN.md              ← this file
├── garmin_cli/
│   ├── __init__.py
│   ├── cli.py              # Typer app, command registration
│   ├── auth.py             # Login, token management
│   ├── cache.py            # SQLite cache layer
│   ├── client.py           # Garmin API client (wraps garminconnect)
│   ├── output.py           # JSON envelope + human formatter
│   ├── config.py           # Config file management
│   └── commands/
│       ├── __init__.py
│       ├── auth_cmds.py    # login, status, schema
│       ├── sleep.py        # sleep
│       ├── heart.py        # heart-rate, hrv
│       ├── recovery.py     # stress, body-battery, respiration, spo2
│       ├── activity.py     # activities, activity, details, splits, hr-zones, weather
│       ├── training.py     # readiness, status, vo2max, race-predictions, endurance, fitness-age
│       ├── body.py         # body-composition, weigh-ins
│       ├── general.py      # user-summary, steps, personal-records
│       └── gear.py         # gear, gear-stats
├── skills/
│   └── garmin-coach/
│       └── SKILL.md        # OpenClaw coaching skill
├── tests/
│   ├── test_cache.py
│   ├── test_output.py
│   ├── test_auth.py
│   └── test_commands/
│       └── ...
└── scripts/
    └── setup-cron.sh       # Helper to configure OpenClaw cron jobs
```

### Dependencies

```toml
[project]
name = "garmin-cli"
requires-python = ">=3.11"
dependencies = [
    "garminconnect>=0.2.40,<0.3",
    "typer>=0.15",
    "rich>=13.0",          # Human-readable output formatting
]

[project.scripts]
garmin = "garmin_cli.cli:app"
```

---

## 12. Build Sequence

### Phase 1: Foundation (auth + infrastructure)
- [ ] Project scaffolding (pyproject.toml, package structure)
- [ ] Auth module (login, token persistence, status check)
- [ ] Output module (JSON envelope, human formatter, TTY detection)
- [ ] SQLite cache module (schema creation, read/write, cache rules)
- [ ] Client module (garminconnect wrapper with cache integration)
- [ ] Schema introspection command

### Phase 2: Core Health Commands
- [ ] `sleep`
- [ ] `heart-rate`
- [ ] `hrv`
- [ ] `stress`
- [ ] `body-battery`
- [ ] `user-summary`

### Phase 3: Activity & Training Commands
- [ ] `activities` (list with filters)
- [ ] `activity` (single activity summary)
- [ ] `activity-details`
- [ ] `activity-splits`
- [ ] `activity-hr-zones`
- [ ] `activity-weather`
- [ ] `training-readiness`
- [ ] `training-status`
- [ ] `vo2max`
- [ ] `race-predictions`
- [ ] `endurance-score`
- [ ] `fitness-age`

### Phase 4: Remaining Commands + Config
- [ ] `body-composition`, `weigh-ins`
- [ ] `steps`, `personal-records`
- [ ] `gear`, `gear-stats`
- [ ] `respiration`, `spo2`
- [ ] Config module (races, timezone, etc.)
- [ ] Cache management commands (stats, clear)

### Phase 5: OpenClaw Integration
- [ ] Write SKILL.md with full coaching guidelines
- [ ] Test skill with interactive chat
- [ ] Configure morning brief cron job
- [ ] Configure weekly report cron job
- [ ] Test end-to-end: cron → CLI calls → AI synthesis → delivery

---

## 13. Data Flow Diagrams

### Morning Brief (daily)

```
7:00 AM
  │
  ▼
OpenClaw Cron fires
  │
  ▼
Isolated agent session starts
  │
  ▼
Agent reads SKILL.md (coaching guidelines + templates)
  │
  ▼
Agent calls garmin-cli (6-8 subprocess calls):
  │
  ├─ garmin sleep 2026-03-16        → cache miss (today) → API → cache
  ├─ garmin hrv 2026-03-16          → cache miss (today) → API → cache
  ├─ garmin training-readiness 2026-03-16 → API → cache
  ├─ garmin training-status 2026-03-16    → API → cache
  ├─ garmin body-battery 2026-03-15 2026-03-16 → partial cache hit
  ├─ garmin stress 2026-03-15       → cache hit (yesterday)
  └─ garmin activities --start 2026-03-15 --end 2026-03-16
  │
  ▼
Agent synthesizes 4-5 sentence brief
  │
  ▼
OpenClaw delivers via announce → WhatsApp/Telegram
```

### Weekly Report (Monday)

```
Monday 8:00 AM
  │
  ▼
OpenClaw Cron fires (model: opus, thinking: high)
  │
  ▼
Isolated agent session starts
  │
  ▼
Agent calls garmin-cli (~30-40 calls, most cached):
  │
  ├─ garmin activities --start Mon --end Sun           (1 call)
  ├─ For each of 7 days: sleep, hrv, training-readiness (21 calls, 14 cached)
  ├─ For each run: activity-details, splits, hr-zones   (3 × N runs)
  ├─ garmin training-status Sun                         (1 call)
  ├─ garmin body-battery Mon Sun                        (1 call)
  ├─ garmin steps Mon Sun                               (1 call)
  ├─ garmin race-predictions --latest                   (1 call)
  ├─ garmin vo2max Sun                                  (1 call)
  └─ garmin endurance-score Mon Sun                     (1 call)
  │
  ├─ For 4-week rolling: repeat daily queries for 3 prior weeks
  │  (mostly ALL cached from prior morning briefs + reports)
  │
  ▼
Agent generates 8-section report
  │
  ▼
OpenClaw delivers via announce → WhatsApp/Telegram
```

### Interactive Chat Query

```
User (any channel): "How's my running form lately?"
  │
  ▼
Agent (reads SKILL.md → biomechanics interpretation)
  │
  ▼
Agent calls:
  ├─ garmin activities --start 4-weeks-ago --end today --type running
  ├─ For recent 5-6 runs: garmin activity <id>
  │  (extracts: cadence, GCT, vert osc, stride length per run)
  │
  ▼
Agent computes trends, identifies notable changes
  │
  ▼
Agent responds with analysis:
  "Over the past 4 weeks, your cadence has crept up from 168 to 174 spm —
   good trend. GCT dropped from 265ms to 248ms, which tracks with the
   cadence improvement. Your vertical oscillation is stable at 8.5cm.
   The one thing to watch: your GCT balance shifted from 50.2/49.8 to
   51.5/48.5 — a slight asymmetry developing on the left side. Worth
   monitoring, could be a shoe issue or early fatigue pattern."
```

---

## 14. Testing Strategy

### Unit Tests
- Output envelope formatting (JSON + human)
- Cache logic (hit/miss/bypass/refresh/today-always-fresh)
- Date parsing and validation
- Error mapping (exception → exit code + error envelope)
- Config loading and defaults

### Integration Tests
- Auth flow (with mocked garth)
- Each command with mocked garminconnect responses
- Cache integration (write on miss, read on hit, bypass on flag)
- Rate limit retry logic

### End-to-End Tests
- Full CLI invocation with real Garmin account (manual/CI with secrets)
- Cache persistence across invocations
- Schema command output validation

---

## 15. What's NOT in Scope (v1)

| Deferred | Rationale |
|---|---|
| Training plan generation | Users already have plans. This is an insight tool, not a planner. |
| Periodization management | Same — users manage their own mesocycles. |
| Workout creation/upload | Write operations beyond auth are risky. Read-first. |
| Social features | Not relevant to solo training analysis. |
| Course/route management | Not relevant to training analytics. |
| Device management | Out of scope for an analytics tool. |
| Real-time / live tracking | API doesn't support it. |
| Composite CLI commands | Intelligence stays in the AI layer, not the CLI. |
| Web UI / dashboard | CLI + AI delivery is the product. |
| Multi-user support | Personal tool for one runner. |

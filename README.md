# KipCLImo

**AI-powered training analytics for runners, cyclists, and gym athletes.**

KipCLImo is a thin, agent-friendly CLI that wraps the Garmin Connect API and pairs it with an AI coaching skill. Your Garmin watch collects the data — KipCLImo lets any AI agent read it, interpret it, and deliver actionable insight straight to you.

It answers one question: *"Is what I'm doing working — and what should I adjust?"*

### What you get

- **Guided onboarding** — the coach asks what disciplines you practice (running, cycling, gym) and what your primary goal is, then personalizes all future advice.
- **Morning brief** — a 4-sentence daily snapshot of your sleep, recovery, training load, and readiness delivered to WhatsApp/Telegram at 7am.
- **Weekly report** — an 8-section deep dive into volume, intensity distribution, key workouts, discipline-specific analysis, and race readiness every Monday.
- **Interactive chat** — ask your agent anything: *"How's my running form lately?"*, *"Am I ready for my half marathon?"*, *"How's my FTP trending?"*, *"Compare this week to last week."*

### Who it's for

You're an advanced amateur athlete. You know what VO2max, ACWR, FTP, and cadence mean. You have a training plan — you don't need another one. You need someone to look at your data and tell you what matters.

---

## Quick Start — Tell Your Agent to Install It

If you use [OpenClaw](https://openclaw.com), Claude Code, or any file-based agent, paste this:

```
Clone and install KipCLImo:

git clone https://github.com/ggonzalez94/KipCLImo.git
cd KipCLImo
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

Then authenticate with Garmin:

garmin login --email <your-garmin-email>

Then install the coaching skill:

python scripts/install_skill.py --agent openclaw

Verify everything works:

garmin status
garmin schema
garmin sleep 2026-03-16
```

That's it. Your agent now has a `garmin-coach` skill and a full CLI to fetch your data.

---

## Components

### 1. The CLI (`garmin`)

A pure data-access layer — 27+ commands that map 1:1 to the Garmin Connect API, plus config commands for profile management. No intelligence, no opinions, just data in a stable JSON envelope.

```bash
garmin sleep 2026-03-16
garmin training-readiness 2026-03-16
garmin activities --start 2026-03-10 --end 2026-03-16 --type running
garmin activity-splits 123456789
garmin race-predictions --latest
garmin config show
garmin config set-list profile.disciplines running cycling
```

**Key design choices:**

| Feature | How it works |
|---|---|
| Output | JSON by default when piped (agent mode). Human-readable when in a terminal. `--output json\|human` to force. |
| Cache | SQLite at `~/.garmin-cli/cache.db`. Past dates are immutable and served from cache. Today always fetches fresh. `--no-cache` and `--refresh` for overrides. |
| Field selection | `--fields cadence,averageHR` to trim payloads and save agent context window. |
| Schema introspection | `garmin schema` returns every command, argument, type, and cache strategy as JSON. Agents can discover the API at runtime. |
| Error envelope | Structured JSON errors with stable exit codes (0-5). Agents branch on exit code, not string parsing. |
| Auth | OAuth tokens via [garth](https://github.com/matin/garth). File-based at `~/.garmin-cli/tokens/`. Auto-reuses existing garth/garminconnect token stores. |

### 2. The Skill (`skills/garmin-coach/`)

This is where the coaching intelligence lives. It's a portable, file-based skill that tells any LLM agent *how* to interpret your Garmin data. On first use, it runs a guided onboarding to learn your disciplines and goals.

```
skills/garmin-coach/
├── SKILL.md                  # Persona, onboarding, report templates, shared metrics
└── references/
    ├── cli.md                # Command inventory for the agent
    ├── running.md            # Running: biomechanics, cardiac drift, intensity, splits
    ├── cycling.md            # Cycling: power/FTP, cadence, HR decoupling, climbing
    ├── gym.md                # Gym: volume, progressive overload, recovery impact
    └── goals.md              # Goal catalog with coaching emphasis per goal
```

The skill covers:
- **Guided onboarding** — asks about disciplines (running, cycling, gym) and primary goal. Personalizes all future advice.
- **Discipline-specific analysis** — the agent loads only the references matching your profile. A runner gets biomechanics and cardiac drift; a cyclist gets power and FTP analysis; a gym user gets volume and overload tracking.
- **Report templates** — structured pull-lists and output formats for daily and weekly reports, adapted to your disciplines.
- **Persona** — direct, data-informed coaching voice. Numbers over adjectives. Honest about bad signals.

Install to any agent that uses directory-based skills:

```bash
python scripts/install_skill.py --agent openclaw   # symlink (default)
python scripts/install_skill.py --agent codex
python scripts/install_skill.py --agent claude
python scripts/install_skill.py --agent custom --dest /path/to/skills
```

### 3. Scheduled Reports (OpenClaw cron)

Automate delivery with the setup script:

```bash
GARMIN_OPENCLAW_CHANNEL=whatsapp \
GARMIN_OPENCLAW_TO=+15555555555 \
GARMIN_TIMEZONE=America/New_York \
scripts/setup-cron.sh
```

Creates two cron jobs:
- **7:00 AM daily** — morning brief
- **8:00 AM Monday** — weekly report

---

## Full Command Reference

| Category | Commands |
|---|---|
| Auth & System | `login`, `status`, `schema` |
| Config | `config show`, `config set`, `config set-list`, `config reset-profile` |
| Sleep | `sleep` |
| Heart Rate & HRV | `heart-rate`, `hrv` |
| Recovery | `stress`, `body-battery`, `respiration`, `spo2` |
| Activity | `activities`, `activity`, `activity-details`, `activity-splits`, `activity-hr-zones`, `activity-weather` |
| Training | `training-readiness`, `training-status`, `vo2max`, `race-predictions`, `endurance-score`, `fitness-age` |
| Body Composition | `body-composition`, `weigh-ins` |
| General | `user-summary`, `steps`, `personal-records` |
| Gear | `gear`, `gear-stats` |
| Cache | `cache stats`, `cache clear` |

Run `garmin schema` for the machine-readable version with full argument specs.

---

## Development

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=garmin_cli
```

### Project structure

```
garmin_cli/
├── cli.py              # Typer app, global flags, entry point
├── client.py           # GarminService — all API calls + cache logic
├── cache.py            # SQLite cache (4 tables)
├── auth.py             # OAuth token management (garth)
├── output.py           # JSON envelope + Rich human formatter
├── schema.py           # Self-describing command registry
├── config.py           # Config file (~/.garmin-cli/config.json)
├── errors.py           # Exit codes, error taxonomy, exception mapping
├── state.py            # Per-invocation dependency container
├── utils.py            # Date helpers, JSON serialization, field selection
├── skill_install.py    # Multi-agent skill installer
└── commands/           # One module per command category
```

### Architecture

```
Agent / Terminal ──subprocess──▸ garmin-cli (Typer)
                                    │
                         ┌──────────┼──────────┐
                         ▼          ▼          ▼
                     AuthManager  Cache    GarminService
                     (garth)    (SQLite)   (garminconnect)
                                    │
                                    ▼
                              Garmin Connect API
```

The CLI is deliberately thin — a 1:1 data access layer. All coaching intelligence lives in the `garmin-coach` skill, not in the CLI. This keeps the tool agent-agnostic: it works with OpenClaw, Claude Code, Codex, or any LLM that can call subprocesses.

### Built on

- [cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect) — Python wrapper for the Garmin Connect API
- [matin/garth](https://github.com/matin/garth) — OAuth token management for Garmin SSO

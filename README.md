# garmin-cli

`garmin-cli` is an agent-friendly Garmin Connect CLI for training analytics. It wraps the public `garminconnect` Python package, adds a stable JSON envelope, applies field selection for token efficiency, and persists immutable history in SQLite so agents can build repeated daily and weekly analyses without re-fetching the same data.

## Features

- JSON-first CLI with a stable success/error envelope
- Auto-detected human output for terminal usage
- SQLite cache with safe freshness rules:
  - Past dates are served from cache when available
  - Today is always fetched fresh
  - `--no-cache` bypasses reads and writes
  - `--refresh` forces a re-fetch and cache update
- Runtime `schema` command for agent introspection
- Portable file-based skill for OpenClaw and other agent systems

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Authentication

First login:

```bash
garmin login --email you@example.com
```

Or use environment variables:

```bash
export GARMIN_EMAIL="you@example.com"
export GARMIN_PASSWORD="super-secret"
garmin login
```

Token storage defaults to `~/.garmin-cli/tokens`. If you already have a valid `GARTH_HOME` token store from another Garmin tool, `garmin-cli` can reuse it automatically.

## Core Usage

```bash
garmin status
garmin schema
garmin sleep 2026-03-16
garmin activities --start 2026-03-10 --end 2026-03-16 --type running --limit 10
garmin activity-details 123456789 --fields summaryDTO,detailedMetrics
garmin race-predictions --latest
```

Machine-readable output is the default when stdout is not a TTY:

```bash
garmin user-summary 2026-03-16 | jq
```

Force a format explicitly:

```bash
garmin --output json sleep 2026-03-16
garmin --output human activities --limit 5
```

## Cache Commands

```bash
garmin cache stats
garmin cache clear
garmin cache clear --before 2026-01-01
garmin cache clear --metric hrv
```

## Skill Installation

The source of truth for the agent skill lives in [`skills/garmin-coach`](skills/garmin-coach).

Install it into OpenClaw:

```bash
python scripts/install_skill.py --agent openclaw
```

Install it into Codex:

```bash
python scripts/install_skill.py --agent codex
```

Install it into any other file-based skill directory:

```bash
python scripts/install_skill.py --agent custom --dest /path/to/agent/skills
```

Copy instead of symlink:

```bash
python scripts/install_skill.py --agent openclaw --method copy
```

Override the target path:

```bash
python scripts/install_skill.py --agent openclaw --dest /custom/skills/root
```

The skill itself is plain file-based `SKILL.md` content, so it remains compatible with agent systems that use directory-based skills.

## OpenClaw Cron Setup

Set the delivery target and create the daily and weekly automations:

```bash
GARMIN_OPENCLAW_CHANNEL=whatsapp \
GARMIN_OPENCLAW_TO=+15555555555 \
GARMIN_TIMEZONE=America/New_York \
scripts/setup-cron.sh
```

The helper creates:

- A 7:00 AM morning brief
- An 8:00 AM Monday weekly report

Both prompts instruct the agent to deliver the final report in Spanish.

## Development

Install dev dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

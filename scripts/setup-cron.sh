#!/usr/bin/env bash
set -euo pipefail

CHANNEL="${GARMIN_OPENCLAW_CHANNEL:-${1:-}}"
RECIPIENT="${GARMIN_OPENCLAW_TO:-${2:-}}"
TIMEZONE="${GARMIN_TIMEZONE:-America/New_York}"

if [[ -z "${CHANNEL}" || -z "${RECIPIENT}" ]]; then
  echo "Usage: GARMIN_OPENCLAW_CHANNEL=whatsapp GARMIN_OPENCLAW_TO=+15555555555 scripts/setup-cron.sh"
  echo "   or: scripts/setup-cron.sh whatsapp +15555555555"
  exit 1
fi

openclaw cron add \
  --name "Garmin Morning Brief" \
  --cron "0 10 * * *" \
  --tz "${TIMEZONE}" \
  --session isolated \
  --message "Use the garmin-coach skill. Generate my morning training brief from Garmin data. Pull today's sleep, HRV, training readiness, training status, body battery, stress, and yesterday's activities. Follow the morning brief template. Deliver the final brief in Spanish." \
  --announce \
  --channel "${CHANNEL}" \
  --to "${RECIPIENT}"

openclaw cron add \
  --name "Garmin Weekly Report" \
  --cron "0 10 * * 1" \
  --tz "${TIMEZONE}" \
  --session isolated \
  --model opus \
  --thinking high \
  --message "Use the garmin-coach skill. Generate my weekly Garmin training report. Pull the last 7 days of activities, sleep, HRV, training readiness, training status, body battery, stress, steps, race predictions, VO2max, and endurance score. For each run, inspect activity details, splits, and HR zones. Follow the weekly report template. Deliver the final report in Spanish." \
  --announce \
  --channel "${CHANNEL}" \
  --to "${RECIPIENT}"

echo "OpenClaw cron jobs created."

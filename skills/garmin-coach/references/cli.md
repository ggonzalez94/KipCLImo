# CLI Reference

Use `garmin-cli` as a thin data-access layer. Prefer narrow queries and field selection.

## High-value commands

- `garmin sleep <date>`
- `garmin heart-rate <date>`
- `garmin hrv <date>`
- `garmin stress <date>`
- `garmin body-battery <start> [end]`
- `garmin respiration <date>`
- `garmin spo2 <date>`
- `garmin activities [--start DATE] [--end DATE] [--type TYPE] [--limit N]`
- `garmin activity <id>`
- `garmin activity-details <id>`
- `garmin activity-splits <id>`
- `garmin activity-hr-zones <id>`
- `garmin activity-weather <id>`
- `garmin training-readiness <date>`
- `garmin training-status <date>`
- `garmin vo2max <date>`
- `garmin race-predictions [--latest] [--start DATE --end DATE]`
- `garmin endurance-score <start> [end]`
- `garmin fitness-age <date>`
- `garmin body-composition <start> [end]`
- `garmin weigh-ins <start> <end>`
- `garmin user-summary <date>`
- `garmin steps <start> <end>`
- `garmin personal-records`
- `garmin gear`
- `garmin gear-stats <uuid>`

## Query discipline

- For daily briefs, stay within today plus yesterday’s activities.
- For weekly reports, fetch the current week first, then a smaller comparison window if you need context.
- For running-form questions, start with recent running activities, then pull activity details only for the most relevant sessions.
- For race readiness, combine race predictions, VO2max, training status, endurance score, long-run details, and two-week recovery trends.

## Field selection

When payloads are large, use `--fields` to limit what you pull.

Examples:

```bash
garmin activity-details 123456789 --fields summaryDTO,detailedMetrics
garmin activities --start 2026-03-10 --end 2026-03-16 --fields activityId,activityName,activityType,startTimeLocal
```

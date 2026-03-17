# Repository Notes

- Keep code, docs, comments, and commit messages in English.
- The `garmin-coach` skill is also written in English, but it instructs agents to:
  - default unattended reports to Spanish
  - answer in the language the user is currently using during interactive chat
- Prefer extending the existing service and schema registry instead of adding one-off CLI behavior directly in command handlers.
- Preserve the stable JSON envelope and exit-code semantics.

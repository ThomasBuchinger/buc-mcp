# Configuration Sync via MCP Resources, Not HTTP

The sync script (`sync.sh`) fetches configuration files (skills, prompts, etc.) via MCP `resources/list` and `resources/read` calls, not by serving files on HTTP endpoints. Skills are already exposed as MCP resources through `SkillsDirectoryProvider`, so the sync script reuses that existing exposure.

Exposing files on dedicated HTTP routes (e.g. `/files/skills/...`) was rejected — if the internal file paths change, HTTP routes break and would need updating in two places (exposure + sync). Serving via MCP keeps everything in one place: the same provider that exposes skills to clients also serves them to the sync script, making the sync resilient to path changes.

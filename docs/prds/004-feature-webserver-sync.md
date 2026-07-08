# PRD: Merged Sync Script with Stateful MCP Protocol Support

## Problem Statement

Currently all popular Agents expect Skills to be in a local directory. The MCP protocol can expose Skills, but they are exposed as generic "Resources" objects and Agents do not recognize them as proper skills. Setting up Skills and MCP client configs on a local machine is error-prone and lacks centralization — there is no reproducible mechanism for an agent to discover and download Skills and configure MCP servers from a shared server.

Additionally, the `buc-skills` server uses stateless HTTP, which prevents it from working with the MCP proxy that requires session initialization. There are also two separate sync concerns (skills and MCP configs) that users must manage independently.

## Solution

A FastAPI server serves two endpoints: `/sync.sh` (a bash script) and `/mcps.json` (an MCP client config). The bash script is a single merged script with internal functions separating Skills sync (via MCP protocol) and MCP config sync (via HTTP). A single mode selection prompt determines which path runs. The script follows the MCP Streamable HTTP protocol for session-based communication. The server parses `mcps.json` and regenerates client configs for each agent type (opencode, claude) with proper URL substitution from the HTTP `Host` header.

## User Stories

1. As a user, I want to bootstrap my local skill environment by running a single `curl | bash` command, so that I can start using shared Skills without manual setup.
2. As a user, I want to configure MCP client configs by running a single `curl | bash` command, so that I can connect to remote MCP servers without manual configuration.
3. As a user, I want one unified script that handles both Skills sync and MCP config sync, so that I don't need to remember multiple scripts or URLs.
4. As a user, I want the script to detect which agent I'm using (opencode or claude), so that Skills land in the correct directory structure automatically.
5. As a user, I want the script to detect which agent I'm using, so that the MCP config file is written to the correct location for my agent.
6. As a user, I want a two-stage interactive flow — first choose a mode, then choose conflict resolution — so that decisions are structured and minimal.
7. As a user, I want to choose between syncing Skills or syncing MCP configs (not both at once), so that I can focus on one concern at a time.
8. As a user, I want three conflict resolution options — sync (skip differing files), dry-run (preview without writing), and force (overwrite) — so that I can control how conflicts are handled.
9. As a user, I want to see a numbered list or fzf fuzzy selection of available Skills, so that I can quickly select which ones to sync.
10. As a user, I want to see a numbered list or fzf fuzzy selection of available MCP servers, so that I can pick a subset to sync.
11. As a user, I want Skills to sync as complete units (SKILL.md + all resource files), so that I don't end up with partial or broken skills.
12. As a user, I want the script to show diffs for files that differ from the server, so that I can understand exactly what would change.
13. As a user, I want the script to skip files that differ when using `sync` conflict resolution, so that I don't accidentally overwrite local changes.
14. As a user, I want dry-run to show me the full merged result that would be written, so that I can verify the outcome before committing.
15. As a user, I want force to overwrite files without showing diffs, so that I can quickly apply all changes.
16. As a user, I want MCP configs to be merged additively into my existing config, so that my other servers are not lost when I sync.
17. As a developer, I want the script to use the MCP Streamable HTTP protocol for Skills sync, so that it works with the MCP proxy that requires session initialization.
18. As a developer, I want the script to follow the MCP protocol spec for session management — send `initialize` first, extract `mcp-session-id`, include it in subsequent requests — so that it is compatible with any conforming MCP server.
19. As a developer, I want the script to use fzf for interactive selection when available, so that users can quickly fuzzy-search through available skills or servers.
20. As a user, I want the script to fall back to a numbered list if `fzf` is not installed, so that I can still use the tool without extra dependencies.
21. As a user, I want the script to re-prompt me if I enter invalid input, so that I can correct my mistake without exiting the sync process.
22. As a user, I want to see a help message explaining the interactive flow, so that I understand how to use the script.
23. As a developer, I want the `/sync.sh` endpoint to inject `SERVER_URL` from the HTTP `Host` header into the script body, so that the same script works regardless of deployment.
24. As a developer, I want the `/mcps.json` endpoint to substitute the `Host` header URL into all server URLs, so that clients automatically point at the deployed server.
25. As a developer, I want the `/mcps.json` endpoint to accept `?agent=opencode` or `?agent=claude`, so that it generates agent-appropriate config format.
26. As a user of opencode, I want the script to write MCP configs to `.agents/opencode.json`, so that opencode picks up the configuration.
27. As a user of claude, I want the script to write MCP configs to `.claude/mcp.json`, so that claude picks up the configuration.
28. As a user of opencode, I want the server to return configs with `"type": "remote"` and key `"mcp"`, so that the format matches opencode's expectations.
29. As a user of claude, I want the server to return configs with `"type": "http"` and key `"mcpServers"`, so that the format matches claude's expectations.
30. As a user, I want the server to skip `$schema` in the generated config, so that optional fields don't clutter the output.
31. As a user, I want the server to skip `enabled` in the generated config, so that client-side enable/disable decisions are not imposed.
32. As a developer, I want the script to be a sourceable library of functions (no global execution), so that they can be tested in isolation.
33. As a developer, I want shared interaction functions (`select_skills`, `print_diff`, `prompt_yes_no`) to be reused by both the skills path and the MCP config path, so that code duplication is minimized.
34. As a developer, I want Skills to land in `{agent-dir}/skills/{skill-name}/SKILL.md` and `{agent-dir}/skills/{skill-name}/resources/{file}`, so that agents recognize them as proper skills.
35. As a developer, I want the `resources/` subdirectory structure to be preserved from the server, so that skill resources maintain their organization.
36. As a developer, I want the `buc-skills` server to use `stateless_http=False` for session support, so that it works with the MCP proxy.
37. As a developer, I want other MCP servers (`buc-coding`, `buc-kubernetes`, `buc-context7`) to remain `stateless_http=False` for client compatibility.
38. As a developer, I want the `/sync.sh` and `/mcps.json` endpoints on the same FastAPI application, so that deployment is simple and URL-agnostic.
39. As a user, I want to select individual skills one by one (no "select all" option), so that I'm deliberate about what I download.
40. As a user, I want to preview diffs for ALL files (new and existing) in dry-run mode, so that I see the complete picture of what would change.

## Implementation Decisions

- **`buc-skills` server**: Changes to `stateless_http=False` to support session-based HTTP transport. Other MCP servers (`buc-coding`, `buc-kubernetes`, `buc-context7`) remain `stateless_http=False`.
- **`/sync.sh` endpoint**: Serves a single merged bash script with internal functions separating Skills sync (MCP protocol) and MCP config sync (HTTP). Mode selection prompt determines which path runs.
- **`/mcps.json` endpoint**: Accepts `?agent=opencode` or `?agent=claude` query parameter. Parses the template `mcps.json`, substitutes the `Host` header URL, and regenerates the JSON from scratch for the requested agent type.
- **MCP Streamable HTTP session**: The sync script follows the MCP protocol spec — first POST sends `initialize` JSON-RPC (no session header), server returns `mcp-session-id` in response header, client includes this header in all subsequent requests.
- **Two-stage interactive flow**:
  1. Mode selection: Skills OR MCP configs (not both).
  2. Conflict resolution: `sync` (skip differing files, show warning), `dry-run` (show diffs without writing), `force` (overwrite without diffs).
- **Shared interaction functions**: `select_skills()`, `print_diff()`, `prompt_yes_no()` are reused by both the skills path and the MCP config path to minimize code duplication.
- **Skill selection**: Script groups MCP resources by skill name (`skill://<name>/...`). If `fzf` is installed, interactive fuzzy selection. If `fzf` is not installed, falls back to a numbered list. No "select all" option — users select individually.
- **MCP server selection**: After fetching `/mcps.json?agent=<detected>`, the script presents the available servers via fzf/numbered list and lets the user select a subset.
- **Additive merge**: When syncing MCP configs, selected servers from the server template are merged into the existing agent config file. Servers already in the config that are not selected are kept.
- **File layout**: `{agent-dir}/skills/{skill-name}/SKILL.md` and `{agent-dir}/skills/{skill-name}/resources/{file}`. The `resources/` subdirectory structure is preserved from the server.
- **Agent directories**: opencode uses `.agents/skills/` for skills and `.agents/opencode.json` for MCP configs. Claude uses `.claude/skills/` for skills and `.claude/mcp.json` for MCP configs.
- **Agent detection**: `detect_agent()` sets `CLIENT_AGENT` to `"opencode"` or `"claude"` (defaulting to `"opencode"` if unknown). `resolve_skills_dir()` then maps `CLIENT_AGENT` to the appropriate path.
- **URL-agnostic**: The script extracts `SERVER_URL` from the `Host` header (injected by the FastAPI endpoint). The `/mcps.json` endpoint also substitutes `Host` header into all server URLs.
- **Claude config format**: Server generates `mcpServers` key with `"type": "http"` (mapping from `"remote"` in the template).
- **Opencode config format**: Server generates `mcp` key with `"type": "remote"` (kept as-is from template).
- **Skip optional fields**: `$schema` and `enabled` are not included in generated configs — they are client decisions.
- **Code layout**: Server code stays in its existing location. Bash scripts go in `scripts/`. Bash tests (using `bats`) are mixed with the scripts in the same `scripts/` directory.
- **Interactive input validation**: Invalid input causes re-prompt. All prompts use either fzf or numbered list to minimize typing.

## Testing Decisions

- **`buc-skills` MCP server**: Use the same `Client` fixture pattern as `tests/test_mcp_coding.py` and `tests/test_mcp_kubernetes.py`. Verify `resources/list` returns expected skill URIs and `resources/read` returns correct content for at least one skill. No MCP protocol internals.
- **`/sync.sh` endpoint**: Python test that hits the endpoint and checks the response contains a valid `SERVER_URL` derived from the request's `Host` header.
- **`/mcps.json` endpoint**: Python test that hits the endpoint with `?agent=opencode` and verifies the response has the `mcp` key and `"type": "remote"` values. Another test with `?agent=claude` verifies the `mcpServers` key and `"type": "http"` values. Another test verifies that `Host` header URLs are substituted correctly.
- **Bash script unit tests**: The script must be structured as a sourceable library of functions (no global execution) so they can be tested in isolation. Use the `bats` (Bash Automated Testing System) framework. Mock external calls (curl, jq, diff) via test doubles:
  - `detect_agent()` — verify it sets `CLIENT_AGENT` correctly (`opencode`, `claude`, or defaults to `opencode`)
  - `resolve_skills_dir()` — verify it returns the correct path based on `CLIENT_AGENT`
  - `fetch_skill_list()` — verify JSON-RPC `resources/list` parsing and skill name grouping, including `mcp-session-id` header handling
  - `select_skills()` — verify fzf selection vs numbered list fallback
  - `sync_file()` — verify diff output, skip behavior on differing files, force overwrite
  - `write_file()` — verify directory creation and file write
  - `session_init()` — verify `initialize` request sends correct JSON and extracts `mcp-session-id` from response header
  - `sync_mcp_main()` — verify fetching `/mcps.json`, parsing, subset selection, and additive merge into config file
- **Integration test**: Minimal. One end-to-end test that starts the FastAPI server, fetches `/sync.sh`, and confirms the script is syntactically valid. Full bash integration is too fragile to maintain — unit tests cover the logic.

## Out of Scope

- `.agents/opencode.json` — local repo config, not syncable (only the `mcp` section is merged).
- HTTP file serving endpoints for individual skill files — MCP protocol is the transport.
- Collection grouping of Skills — may be added in a future PRD if needed.
- Authentication on `/sync.sh` or `/mcps.json` — both endpoints are public.
- Local MCP server configurations (stdio type) — the server template is parsed and regenerated, but only remote/HTTP servers are supported for sync.
- Session cleanup — the script does not send a `delete` request to terminate sessions (sessions expire after 1 day by default).

## Further Notes

- **PRD filename**: `0004-feature-webserver-sync.md` — follows the naming convention `{number}-feature-{short-name}.md`.
- **One script total**: `/sync.sh` serves `sync.sh` with internal functions for both Skills and MCP config sync.
- **Two server endpoints**: `/sync.sh` (bash script) and `/mcps.json` (MCP client config with Host header substitution and agent format generation).
- **Agent detection**: The script uses `detect_agent()` to set `CLIENT_AGENT` by checking for `.agents/skills/` (opencode) and `.claude/skills/` (claude), defaulting to opencode if unknown. `resolve_skills_dir()` then maps `CLIENT_AGENT` to the appropriate path.

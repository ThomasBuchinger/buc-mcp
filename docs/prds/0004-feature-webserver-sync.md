# PRD: Webserver for Centralized Skill Sync

## Problem Statement

Currently all popular Agents, expect Skills to be in a local directory. The MCP protocol can expose Skills, but, they are exposed as generic "Resources" objects and Agents do not regocnize them as proper skills. 
Setting up Skills on a local machine is error-prone and lacks centralization — there is no reproducible mechanism for an agent to discover and download Skills from a shared server.

## Solution

A FastAPI endpoint serves a bash script at `/sync.sh`. The script first detects the local agent (opencode or claude) via `detect_agent()`, then resolves the skills directory via `resolve_skills_dir()`. It presents the user with a numbered list of available Skills and syncs selected ones using MCP `resources/list` and `resources/read` calls. The server injects its own URL from the HTTP `Host` header, so the script is URL-agnostic.

## User Stories

1. As a user, I want to bootstrap my local skill environment by running a single `curl | bash` command, so that I can start using shared Skills without manual setup.
2. As a user, I want the script to detect which agent I'm using (Claude Code, agent-compatible agents, etc.), so that Skills land in the correct directory structure automatically.
3. As a user, I want to see a numbered list of available Skills and select which ones to sync, so that I only download what I need.
4. As a user, I want the script to use `fzf` for fuzzy selection when available, so that I can quickly select which skills I want.
5. As a user, I want to preview changes before they're applied, so that I can verify what would be downloaded without committing to it.
6. As a user, I want the script to show a `diff` when files differ, so that I can understand exactly what would change.
7. As a user, I want `--dry-run` and `--force` flags, so that I can simulate the sync.
8. As a user, I want Skills to sync as complete units (SKILL.md + all resources files), so that I don't end up with partial or broken skills.
9. As a developer, I want the script to be URL-agnostic by extracting the server URL from the `Host` header, so that the same script works regardless of deployment.
10. As a developer, I want to use Streamable HTTP (not SSE) for MCP calls, so that the bash script uses simple `curl POST → JSON` without complex stream parsing.
11. As a developer, I want `buc-skills` to use `stateless_http=True`, so that each MCP call is an independent POST without session tracking.
12. As a developer, I want the sync script to be separate from MCP client config sync, so that the two concerns remain cleanly decoupled.
13. As a user, I want the script to accept a `skills` parameter (e.g., `http://server/sync.sh | bash skills`), so that I can clearly indicate my intent.
14. As a user, I want a help message when passing an invalid command to the script, so that I understand the correct usage.
15. As a user, I want the script to gracefully fall back to a numbered list if `fzf` is not installed, so that I can still use the tool without extra dependencies.

## Implementation Decisions

- **`buc-skills` server**: Already exists and is working. Uses `stateless_http=True`. Other **MCP Servers** (`buc-coding`, `buc-kubernetes`, `buc-context7`) remain `stateless_http=False` for client compatibility.
- **`/sync.sh` route**: `@app.get("/sync.sh")` on the FastAPI root. Dynamically injects `SERVER_URL` from the `Host` header into the script body.
- **Skill selection**: Script groups MCP resources by skill name (`skill://<name>/...`). If `fzf` is installed, interactive fuzzy selection. If `fzf` is not installed, falls back to a numbered list. No "select all" option — users select individually.
- **Collection concept removed**: Individual skills are the unit of selection. Collections may be added later.
- **File layout**: `{agent-dir}/skills/{skill-name}/SKILL.md` and `{agent-dir}/skills/{skill-name}/resources/{file}`. The `resources/` subdirectory structure is preserved from the server.
- **Code layout**: Server code stays in its existing location. Bash scripts go in `scripts/`. Bash tests (using `bats`) are mixed with the scripts in the same `scripts/` directory.
- **Two scripts**: `sync.sh` (MCP-based, skills) and `mcpsync.sh` (HTTP-based, MCP client configs). Separation keeps complexity manageable.
- **Sync logic**: Check if files exist → diff if changed → exit (user must re-run with `--force` to overwrite). `--force` bypasses diff and writes. `--dry-run` has no effect — diffs always prevent writes without `--force`.
- **Agent directories**: The script uses a two-step process: `detect_agent()` sets `CLIENT_AGENT` to `"opencode"` or `"claude"` (defaulting to `"opencode"` if unknown), and `resolve_skills_dir()` returns the appropriate path (`.agents/skills/` for opencode, `.claude/skills/` for claude). This design makes it easy to add new agents in the future.

## Testing Decisions

- **`buc-skills` MCP server**: Add `tests/test_mcp_skills.py` using the same `Client` fixture pattern as `tests/test_mcp_coding.py` and `tests/test_mcp_kubernetes.py`. Verify `resources/list` returns expected skill URIs and `resources/read` returns correct content for at least one skill. No MCP protocol internals.
- **`/sync.sh` endpoint**: Python test that hits the endpoint and checks the response contains a valid `SERVER_URL` derived from the request's `Host` header.
- **Bash script unit tests**: The script must be structured as a sourceable library of functions (no global execution) so they can be tested in isolation. Use the `bats` (Bash Automated Testing System) framework. Mock external calls (curl, jq, diff) via test doubles:
  - `detect_agent()` — verify it sets `CLIENT_AGENT` correctly (`opencode`, `claude`, or defaults to `opencode`)
  - `resolve_skills_dir()` — verify it returns the correct path based on `CLIENT_AGENT`
  - `fetch_skill_list()` — verify JSON-RPC `resources/list` parsing and skill name grouping
  - `select_skills()` — verify fzf selection vs numbered list fallback
  - `sync_file()` — verify diff output, `--force` bypass, `--dry-run` skip
  - `write_file()` — verify directory creation and file write
- **Integration test**: Minimal. One end-to-end test that starts the FastAPI server, fetches `/sync.sh`, and confirms the script is syntactically valid. Full bash integration is too fragile to maintain — unit tests cover the logic.

## Out of Scope

- MCP client config sync (`mcps/mcps.json`) — handled by a separate `mcpsync.sh` script.
- `.agents/opencode.json` — local repo config, not syncable.
- HTTP file serving endpoints for individual skill files — MCP protocol is the transport.
- Collection grouping of Skills — may be added in a future PRD if needed.
- Authentication on `/sync.sh` — the script is public.

## Further Notes

- **PRD filename**: `0004-feature-webserver-sync.md` — follows the naming convention `{number}-feature-{short-name}.md`.
- **Two scripts total**: `sync.sh` (MCP-based, skills) and `mcpsync.sh` (HTTP-based, MCP configs).
- **Agent detection**: The script uses `detect_agent()` to set `CLIENT_AGENT` by checking for `.agents/skills/` (opencode) and `.claude/skills/` (claude), defaulting to opencode if unknown. `resolve_skills_dir()` then maps `CLIENT_AGENT` to the appropriate path.

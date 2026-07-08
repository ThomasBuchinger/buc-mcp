# PRD: Model Sync — Selective OpenAI-Compatible Model Provisioning for Opencode

## Problem Statement

Opencode users accessing an OpenAI-compatible model server at a fixed endpoint need a reproducible mechanism to discover available models and add them to their opencode.json provider configuration. Currently there is no tool to bridge the gap between a remote `/v1/models` API and the opencode provider structure, where models must be registered inside a provider entry with specific formatting (`npm`, `baseURL`, `apiKey`, and per-model display names).

The existing `sync.sh` script handles skills and MCP config sync. Model provisioning is a distinct but related concern — it uses the same interactive selection pattern but targets a different config section (the `provider` block instead of the `mcp` block) and communicates with a different API (`/v1/models` at a hardcoded URL instead of the MCP server).

## Solution

A third mode ("Models") inside the unified `sync.sh` script. The script fetches all available models from `http://10.0.0.190:32434/v1/models`, presents them with existing provider models pre-selected, lets the user toggle inclusion via fzf (multi-select) or numbered menu (toggle), then uses `yq` to update or create the `"local"` provider in `.agents/opencode.json`. The script is served via the same `curl URL/sync.sh | bash` invocation as the existing modes.

## User Stories

1. As an opencode user, I want to see all models available from the local model server, so that I can make informed decisions about which ones to use.
2. As an opencode user, I want existing models in my provider to be pre-selected when I run the sync, so that I don't lose them by accident.
3. As an opencode user, I want models with a `name` field to display as `"local / <name>"`, so that I can distinguish between similarly-named models.
4. As an opencode user, I want models without a `name` field to display as `"local / <id>"`, so that I still have meaningful names for all models.
5. As an opencode user, I want to use fzf fuzzy multi-select when choosing models, so that I can quickly narrow down a long list.
6. As an opencode user, if fzf is not available, I want a numbered menu where pressing a number toggles model inclusion, so that I can still select models without extra dependencies.
7. As an opencode user, I want unselected models to be removed from the provider, so that the config reflects exactly my current choices.
8. As an opencode user, I want a summary of changes shown before writing, so that I can verify additions and removals before they take effect.
9. As an opencode user, I want the sync to fail clearly if the model API is unreachable, so that I know the server is down instead of silently writing a stale config.
10. As an opencode user, I want the `"local"` provider to be created automatically if it doesn't exist, so that I don't need to manually set up the provider before using model sync.
11. As an opencode user, I want existing models to be preserved when I run the sync (since they are pre-selected by default), so that I don't accidentally remove models I still use.
12. As an opencode user, I want the `baseURL` set to `http://10.0.0.190:32434/v1` for the local provider, so that opencode knows where to send requests.
13. As an opencode user, I want the `apiKey` set to `"aaa"` for the local provider, so that requests include the expected credential.
14. As an opencode user, I want the provider to use `@ai-sdk/openai-compatible` as the npm package, so that opencode can communicate with the OpenAI-compatible API.
15. As an opencode user, I want the provider display name to be `"Local"`, so that the config is human-readable.
16. As an opencode user, I want the `$schema` field to be preserved in my existing config, so that my editor tooling keeps working.
17. As an opencode user, I want `yq` to be used for modifying opencode.json, so that only the `provider` block is touched and all other config sections survive the rewrite. (Note: comments are not representable in JSON output, so any `//` comments in the file are lost on write — same as the existing MCP sync mode.)
18. As an opencode user, I want model selection confirmation to be implicit — closing fzf or typing `0` in the numbered menu is sufficient, so that I don't need an extra confirmation step.
19. As an opencode user, I want to run model sync with the same `curl URL/sync.sh | bash` command as skills and MCP sync, so that I only need to remember one URL and one script.
20. As an opencode user, I want the sync to be a third mode alongside Skills and MCP configs, so that all sync concerns are unified in a single tool.
21. As a developer, I want the models mode served through the existing `/sync.sh` FastAPI endpoint (no new endpoint), so that there is exactly one script and one URL; the model API URL is hardcoded in the script body, not injected by the server.
22. As a developer, I want shared interaction functions (`select_skills`, `prompt`, `log`) to be reused by the models mode, so that code duplication is minimized.
23. As a developer, I want the models mode to follow the same sourceable-library pattern as the rest of sync.sh (no global execution), so that functions can be tested in isolation.
24. As a developer, I want the models API URL to be hardcoded in the script body as `MODEL_API_URL`, so that it can be overridden via environment variable if needed during testing or deployment.
25. As a reviewer, I want to see a summary of additions, removals, and unchanged models before any write happens, so that the diff is transparent and auditable.
26. As an opencode user, I want the provider to only contain models I explicitly select, so that the config stays clean and I know exactly which models opencode can access.

## Implementation Decisions

- **Unified script**: Model sync is a third mode ("models") inside the existing `sync.sh` script. The main flow presents three options: Skills, MCP configs, Models.
- **Hardcoded model API URL**: `MODEL_API_URL="http://10.0.0.190:32434/v1"` is hardcoded in the script body. This is separate from the MCP server URL which comes from the Host header injection.
- **Provider structure**: Models are written to a `"local"` provider entry under the `provider` block in opencode.json. The provider uses `npm: "@ai-sdk/openai-compatible"`, `name: "Local"`, `baseURL: "http://10.0.0.190:32434/v1"`, `apiKey: "aaa"`.
- **Model display names**: Models with a `name` field from `/v1/models` use `"local / <name>"`. Models without `name` use `"local / <id>"`. (The server is llama-swap; its `/v1/models` response carries human-readable labels in `name`, e.g. `"Gemma 4 26B (80tps-262k-Thinking-Vision) [Agent]"`.)
- **Interactive selection**: Existing models (from the current provider) are pre-selected. The user can toggle models on/off via fzf multi-select or a numbered toggle menu (fallback when fzf is unavailable). Pressing `0` in the numbered menu finishes selection.
- **yq for config modification**: `yq` is used to update the `provider` block in opencode.json, preserving `$schema` and other config sections. Only the `provider` block is modified. Comments cannot be preserved in JSON output (matching existing MCP sync behavior, which strips `//` comments before parsing).
- **Config location**: `.agents/opencode.json` — same as the existing sync script for MCP config sync.
- **Implicit confirmation**: Closing fzf or typing `0` in the numbered menu confirms the selection. No extra yes/no prompt.
- **Summary before write**: After selection, the script outputs which models are being added, which are being removed, and which remain unchanged. Then it writes.
- **Error handling**: If the model API is unreachable, the script prints a clear error and exits with a non-zero code. No stale config is written.
- **Provider auto-creation**: If the `"local"` provider doesn't exist in opencode.json, the script creates the full provider entry with the selected models.
- **No $schema addition**: Existing `$schema` is preserved by yq. A new `$schema` is not added if one doesn't exist.
- **All models shown**: No filtering — the server-curated model list is presented in full. fzf handles long lists.
- **No new FastAPI endpoint**: The models mode ships inside `sync.sh` and is served by the existing `/sync.sh` endpoint. `MODEL_API_URL` is hardcoded in the script body (env-overridable), so no server-side injection is needed.

## Testing Decisions

- **Bats unit tests for models functions** (mixed with sync.sh in `scripts/`):
  - `fetch_models()` — verify it fetches from MODEL_API_URL and parses the `/v1/models` response correctly, extracting `id` and `name` fields.
  - `select_models()` — verify fzf multi-select behavior and numbered toggle menu fallback. Verify existing models are pre-selected (real fzf selection state via the select-all+reload pattern; shown with `[x]` in the numbered menu).
  - `update_opencode_json()` — verify yq creates the provider if it doesn't exist, merges selected models, and removes unselected models from the provider.
  - `sync_model_main()` — verify the full flow: fetch, select, summarize, write.
  - Model display name generation — verify name-based naming (`"local / <name>"`) and fallback to id-based naming (`"local / <id>"`).
  - Summary output — verify the script prints added/removed/unchanged model counts and lists.
  - Error handling — verify the script exits with an error when the API is unreachable.
- **FastAPI endpoint test**: Python test that hits the existing `/sync.sh` endpoint and confirms the response contains `MODEL_API_URL="${MODEL_API_URL:-http://10.0.0.190:32434/v1}"` (i.e., the models mode ships in the served script).
- **Shared function tests**: Existing bats tests for `select_skills`, `prompt`, `log` remain valid since the models mode reuses them.

## Out of Scope

- Claude Code support — Claude users are assumed to use default models or configure via environment variables.
- Multiple model API endpoints — only the hardcoded `10.0.0.190:32434` is supported.
- Model API authentication — the API is assumed to be accessible without additional credentials (apiKey is hardcoded as `"aaa"`).
- Per-model configuration (context window limits, output token limits) — only model inclusion is managed.
- User-level opencode config (`~/.config/opencode/opencode.json`) — only `.agents/opencode.json` is supported.
- Provider renaming or multi-provider support — only the `"local"` provider is created/updated.
- Model versioning or rollback — no history tracking, the current selection is the source of truth.

## Further Notes

- **PRD filename**: `0006-feature-model-sync.md` — follows the naming convention `{number}-feature-{short-name}.md`. Number 6 skips 5 which is occupied by `0005-feature-kanban.md`.
- **One script total**: `sync.sh` contains all three sync modes (Skills, MCP configs, Models).
- **Dependencies**: `yq` is a new required dependency for the models mode (not used by skills or MCP sync modes). Existing dependencies (`curl`, `jq`) are unchanged.
- **Module breakdown**:
  - `sync.sh` — bash script with internal functions for all three sync modes. Shared functions: `detect_agent()`, `resolve_path()`, `prompt()`, `select_skills()`, `_select_multi()`, `log()`, `has_fzf()`, `_extract_json()`, `_mcp_post()`, `session_init()`, `fetch_resource_uris()`, `sync_file()`, `merge_configs()`, `merge_and_write()`. New functions for models mode: `fetch_models()`, `select_models()`, `humanize_display_name()`, `summarize_model_changes()`, `update_opencode_json()`, `sync_model_main()`.
  - `server.py` — unchanged. The existing `/sync.sh` endpoint serves the whole script, models mode included.

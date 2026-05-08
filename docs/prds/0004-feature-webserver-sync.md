# PRD: Webserver for Centralized Configuration Sync

## Overview
This feature introduces a webserver component to the existing FastMCP-based server. The goal is to centralize client-side configurations (Skills, MCP-configs, etc.) and provide a mechanism to synchronize these files to a user's local workspace via a single `curl` command. This ensures agents have a consistent and easily updatable environment.

## Problem Statement
Agents require various client-side configurations that are not always easily managed through the MCP protocol itself. Currently, setting up these configurations manually is error-prone and lacks centralization.

## User Impact
Users/Agents will be able to quickly bootstrap or update their local environment by running a single command. They can choose specific "collections" of configurations tailored to their specific project or agent needs, ensuring only relevant files are synced.

## Technical Scope
- **Webserver Integration**: Extend the existing Python FastMCP server to include a webserver component (using FastAPI) with custom routes.
- **Script Exposure**: Use `@mcp.custom_route("/sync.sh", methods=["GET"])` to serve the `sync.sh` script.
- **Data Transport**: Configuration files will NOT be served via HTTP; the `sync.sh` script will fetch them using MCP `resources/list` and `resources/read` calls.
- **Collection Management**: The script must provide a numbered list for users to select which collections (Skills, MCP-configs, etc.) to sync.
- **Agent Detection**: The script will detect the client-side agent by checking well-known configuration locations.
- **Sync Logic**: 
    - Check if files already exist.
    - If files differ, output a `diff`.
    - Support a `--force` flag to bypass checks and force synchronization.
    - Support a `--dry-run` flag to simulate the process without downloading.

## Implementation Milestones
- [ ] **Milestone 1: Webserver & Script Route**: Integrate the webserver and implement the `@mcp.custom_route("/sync.sh", methods=["GET"])` to serve the bash script.
- [ ] **Milestone 2: Sync Script Core**: Implement `sync.sh` with agent detection and the numbered list selection UI.
- [ ] **Milestone 3: MCP Client Integration**: Implement the logic in `sync.sh` to fetch file contents via `resources/list` and `resources/read` MCP calls.
- [ ] **Milestone 4: Advanced Sync Logic**: Add `diff` output, `--force` flag, and `--dry-run` flag to the script.
- [ ] **Milestone 5: Dynamic Collection Mapping**: Transition from a static map to a dynamic implementation where collections are determined by the directory names of the skills.
- [ ] **Milestone 6: Validation & Documentation**: Complete integration tests (verifying the `curl | bash` workflow) and update project documentation.

## Success Criteria
- Users can successfully run `curl http://buc-mcp/sync.sh | bash` to trigger the sync process.
- The script correctly detects different AI agent environments.
- The `diff` functionality accurately identifies mismatches between local and remote files.
- The `--dry-run` and `--force` flags behave as expected.

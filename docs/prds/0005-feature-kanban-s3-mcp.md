# PRD: Kanban Board MCP Server with S3 Backend

## Problem Statement

Users maintain Kanban boards as custom Markdown DSL files stored in an S3 bucket. AI agents need to read and modify these boards through the MCP protocol, but there is no MCP server to bridge agents with S3-hosted Kanban files. Direct S3 access from agents would expose credentials and lack conflict resolution, leading to update collisions when multiple agents edit the same board simultaneously.

## Solution

A new `buc-kanban` MCP server mounted on the existing FastAPI webserver, exposing tools to read and edit Kanban boards backed by S3 files. The server manages S3 authentication internally and uses ETags for optimistic concurrency control. A hardcoded board registry maps board names to S3 paths. The Kanban DSL is parsed, items are assigned global indices, and mutations are applied with conflict detection.

## User Stories

1. As an agent, I want to list all items on a Kanban board, so that I can understand its current state.
2. As an agent, I want to change the text of an existing item by index, so that I can update issue descriptions.
3. As an agent, I want to add a new item to a Kanban board, so that I can create new issues.
4. As an agent, I want to move an item from one section to another (e.g., TODO to Done), so that I can reflect status changes.
5. As an agent, I want the server to reject stale writes, so that I do not overwrite concurrent changes.
6. As an agent, I want stale write errors to include the current board state, so that I can recover and retry.
7. As an agent, I must call `list_items` before any mutating tool, so that the server knows I have fresh data.
8. As an agent, I get global indices across all sections, so that I do not need to track per-section numbering.
9. As an agent, I get the full updated `list_items` output after add and change_status, so that I always have the latest indices.
10. As an operator, I can define boards by editing a single Python constant in the MCP server code, so that board configuration is version-controlled in git.
11. As an operator, I can deploy the MCP server alongside existing servers in the same Kubernetes pod, so that no new infrastructure is needed.
12. As an operator, I can configure S3 credentials via environment variables, so that they integrate with existing secret management.
13. As an agent, I can work with boards that have arbitrary section names, so that the DSL is flexible across different boards.
14. As an agent, I can read items with or without `<br><br>`-delimited descriptions, so that the parser handles all valid formats.
15. As an agent, I can add an item at the beginning of the first section instead of the end, so that high-priority items can be inserted top.
16. As an operator, I can deploy multiple independent S3-based Kanban boards under different names, so that each board is addressable.
17. As an agent, I cannot add or remove sections from a board, so that the board structure remains stable.
18. As an agent, I cannot delete items from a board, so that history is preserved via status transitions instead.
19. As the server, I store ETags in memory per board, so that concurrent writes from the same session are detected.
20. As an agent, I get a consistent JSON format from all tools, so that parsing is predictable.

## Implementation Decisions

- **Package layout**: All kanban code in `src/kanban_s3/` package. Only minimal changes to `src/mcp.py` (import + mount) and `src/server.py` (mount + health).
- **New MCP server**: `buc-kanban` FastMCP instance exposed by `src/kanban_s3/__init__.py`.
- **Webserver mount**: Mounted at `/buc-kanban` on the FastAPI parent app in `src/server.py`.
- **Health registration**: Added to `register_health_routes` alongside existing servers.
- **Board registry**: Hardcoded dict in server code: `KANBAN_BOARDS = {"todo": "my-bucket/path/to/kanban.md", ...}`. No external config, env var, or runtime registration.
- **Kanban DSL parser**: A deep module that parses Markdown into sections with items. Section headers are `##` headings. Items are `- [ ]` list items. The `<br><br>` marker separates a title from a description within item text. The parser produces a structured representation: `{"section_name": ["item text 1", "item text 2", ...], ...}`.
- **Global index assignment**: Items across all sections are assigned sequential zero-based indices. Index 0 is the first item in the first section, index N is the Nth item in the Nth section, etc.
- **Stateful ETag tracking**: Each board has an in-memory entry mapping `board_name -> {"etag": str, "items": [...]}`. `list_items` reads from S3, stores the ETag, and returns items. Mutating tools (`edit_item`, `add_item`, `change_status`) require a prior `list_items` call for that board. On write, the server re-reads the file from S3 and compares the ETag — if stale, rejects with error + fresh item data.
- **S3 interaction**: Uses `boto3` with standard AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`). Operations: `HeadObject` to get ETag, `GetObject` to read, `PutObject` to write. The bucket name is extracted from the board path (`bucket/key.md` split on first `/`).
- **No section mutation**: Tools cannot add or remove section headings. Only item text within existing sections can be modified.
- **No delete**: Items cannot be deleted from the board. They can only be moved between sections via `change_status`.
- **Tool signatures**:
  - `list_items(board: str)` — reads S3, establishes ETag, returns `[{section, index, text}]`
  - `edit_item(board: str, index: int, new_text: str)` — replaces item text at global index, returns `[{section, index, text}]`
  - `change_status(board: str, index: int, target_section: str)` — moves item at global index to target section, returns `[{section, index, text}]`
  - `add_item(board: str, text: str, prepend: bool = False)` — appends text to end of first section by default, or prepends to start when `prepend=True`, returns `[{section, index, text}]`
- **Deep module extraction**: The Kanban DSL parser is a deep module: `KanbanBoard` class with `parse(text: str) -> Board` and `render(board: Board) -> str`. It takes raw Markdown and produces a structured mutable object, and vice versa. This module is testable in isolation with no S3 dependency.
- **Index validation**: If `edit_item` receives a global index that does not belong to the expected section (passed by agent from its cached `list_items` state), it is rejected.
- **Error contract on stale write**: Returns an error explaining the data is outdated, followed by the current item list. The agent can retry with fresh indices.
- **Dependencies**: `boto3` added to `pyproject.toml`. No other new dependencies.
- **Deployment**: No new K8s resources. The same single-instance deployment hosts the new MCP server. The in-memory ETag store is compatible with this.

## Testing Decisions

- **Unit tests only** for the deep parser module (`src/kanban_s3/parser.py`).
- **Tests verify external behavior**: Given Markdown text, `parse()` produces correct sections and global indices. Given a modified board, `render()` produces correct Markdown output. Index shifting on add/delete/move is verified.
- **Test patterns follow existing tests**: Similar structure to `tests/test_mcp_coding.py` — use `pytest`. Since parser logic is synchronous, sync tests are sufficient. Tests live in `tests/test_kanban_s3_parser.py`.
- **Test coverage scope**: Parser module only. No S3 mocking or integration tests. The server plumbing (FastMCP tool registration) is verified implicitly when the MCP server is tested as part of the full integration suite.
- **Specific test cases**:
  - Parse empty board (no items)
  - Parse board with multiple sections
  - Parse items with `<br><br>` descriptions
  - Parse items without `<br><br>` descriptions
  - Global index assignment across sections
  - Index recalculation after item addition
  - Index recalculation after item removal (move between sections)
  - Render back to valid Markdown

## Out of Scope

- Per-item unique IDs — items are identified only by dynamic global index.
- Adding or removing sections from a board.
- Deleting items from a board.
- Board discovery or listing — board names are hardcoded.
- Multiple S3 regions or buckets per board.
- Authentication on the MCP tools — the MCP server is internal.
- Horizontal scaling support — in-memory ETag store is single-instance only.
- Board file validation against a schema — any valid Kanban DSL Markdown is accepted.
- Undo/redo or history — S3 versioning is out of scope.
- Real-time collaboration indicators — the server is pull-based.

## Further Notes

- **PRD filename**: `0005-feature-kanban-s3-mcp.md` — follows the naming convention `{number}-feature-{short-name}.md`.
- **DSL format**: The Kanban Markdown DSL uses `##` for section headings and `- [ ]` for items. Line breaks within item text use `<br><br>`. This is a lightweight format — no YAML frontmatter, no metadata fields.
- **Etag lifecycle**: When a mutating tool succeeds, the in-memory ETag is updated to the new value from the S3 response. Subsequent mutations use the updated ETag.
- **boto3 versioning**: S3 ETags for objects < 100MB are MD5 hashes. For larger objects (multipart uploads), they are not MD5 hashes and have a different format. The server treats ETags as opaque strings and uses them only for comparison.
- **Module structure**: The `buc-kanban` code lives in a `src/kanban_s3/` package directory:
  - `src/kanban_s3/__init__.py` — exposes `buc_kanban` FastMCP instance
  - `src/kanban_s3/parser.py` — deep module: `KanbanBoard` class (parse/render/global indices)
  - `src/kanban_s3/server.py` — S3 operations, ETag tracking, tool implementations
  - `src/kanban_s3/config.py` — hardcoded board registry
- Minimal wiring in `src/mcp.py` (one import + `app.mount()` call) and `src/server.py` (one mount point + health registration).

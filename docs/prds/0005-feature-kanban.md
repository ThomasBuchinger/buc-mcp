# PRD: Kanban MCP Server

## Problem Statement

Kanban boards stored as Markdown files on S3 are used as the task management surface for AI agents. Agents need to interact with these boards — adding items, listing items, moving items between columns — through the MCP protocol. Currently there is no MCP server to bridge agents with S3-hosted Kanban Markdown files. The files follow the Obsidian Kanban plugin DSL or a simplified Markdown variant, and direct file manipulation risks corrupting the structured format.

## Solution

A `buc-personal` MCP server (mounted at `/buc-personal`) that exposes three tools (`kanban_add_item`, `kanban_list_items`, `kanban_move_item`) to interact with one or more Kanban boards. Each board maps to an S3 object via a hardcoded name-to-S3 mapping. On every tool call, the server fetches the file from S3, parses it into an internal representation, applies the requested operation, and writes the file back to S3 with ETag-based conflict prevention. Items are identified by their position-based sequence number across all columns. All tools return the refreshed `kanban_list_items` output so agents always see the latest state.

## User Stories

1. As an AI agent, I want to add a new task to a Kanban board by calling `kanban_add_item`, so that I can create work items programmatically.
2. As an AI agent, I want `kanban_add_item` to default to the first column if I don't specify a `column_name`, so that I can quickly add items without needing to know column names.
3. As an AI agent, I want `kanban_add_item` to prepend to a column when I set `prepend=true`, so that I can create high-priority items that appear at the top.
4. As an AI agent, I want the checkbox state of a new item to be determined by its column (checked in `**Complete**` columns, unchecked elsewhere), so that I don't need to manage checkbox state manually.
5. As an AI agent, I want to list all items on a board via `kanban_list_items`, so that I can see the current state of the board and identify items by their sequence number.
6. As an AI agent, I want `kanban_list_items` to exclude archived items by default (`archive=false` by default), so that I only see active items during normal operations.
7. As an AI agent, I want each `kanban_list_items` item to have a `number`, `column_name`, and `text`, so that I can reliably reference items across tool calls.
8. As an AI agent, I want to move an item from one column to another via `kanban_move_item`, so that I can update the status of tasks (e.g., from "Todo" to "Done").
9. As an AI agent, I want `kanban_move_item` to automatically adjust the checkbox state based on the target column, so that moving an item to "Done" marks it as complete.
10. As an AI agent, I want `kanban_move_item` to support `prepend` so I can place a moved item at the top of its target column.
11. As an AI agent, I want every tool to return the refreshed `kanban_list_items` output, so that I always see the latest board state without a separate `kanban_list_items` call.
12. As an AI agent, I want items identified by a stable sequence number within a single tool call cycle, so that I can reference them precisely.
13. As an operator, I want to configure multiple Kanban boards with a simple Python dict mapping board names to S3 bucket/key pairs, so that the server can manage multiple boards without complex configuration.
14. As an operator, I want ETag-based conflict prevention on S3 writes, so that concurrent edits are detected and rejected rather than silently overwriting each other.
15. As an operator, I want the server to return a clear error on ETag conflict instructing the caller to refetch, so that retry logic is delegated to the agent.
16. As an AI agent, I want column names matched case-insensitively, so that small typos in column names don't cause errors.
17. As an AI agent, I want item text to be trimmed of leading/trailing whitespace, so that I don't accidentally introduce formatting issues.
18. As an AI agent, I want items moved to the Archive column to be hidden from `kanban_list_items` when `archive=false`, so that archived items don't clutter the active view.
19. As an AI agent, I want `kanban_list_items` to show the Archive column (empty) when `archive=false`, so that I know the Archive column exists as a valid target for `kanban_move_item`.
20. As an AI agent, I want pre-existing column validation — `kanban_add_item` fails if the column doesn't exist, so that I can't accidentally misspell column names and create phantom columns.
21. As an agent using the simple Kanban format, I want the server to parse my board correctly, so that my board is fully compatible.
22. As an agent using the Obsidian Kanban plugin format, I want the server to preserve frontmatter, `%% kanban:settings` footer, `**Complete**` markers, and `***` separators, so that the board renders correctly in Obsidian.
23. As an agent, I want the server to handle multi-line item descriptions using `<br><br>`, so that items with details are preserved as single unit moves.
24. As an operator, I want the server to have no persistent local state, so that there are no sync issues between the server's internal state and the S3 file.
25. As an operator, I want the server to be deployed alongside existing MCP servers on the same FastAPI host, so that no additional infrastructure is needed.

## Implementation Decisions

- **MCP Server**: `buc-personal` — a new `FastMCP` instance mounted at `/buc-personal` on the existing FastAPI webserver. Follows the same pattern as `buc-coding`, `buc-kubernetes`, `buc-skills`.
- **Board Configuration**: A hardcoded Python dict in source code mapping `board_name` (str) to `{bucket: str, key: str}`. Simple to maintain for a small number of boards. No runtime config reloading.
- **S3 Access**: boto3 (`s3.Client`) for `get_object` (with ETag extraction) and `put_object` (with `ChecksumMode='ENABLED'` and `IfNoneMatch`/conditional write for conflict prevention). A minimal `DummyS3` abstraction wraps this for testing — it stores the raw string in memory with an auto-incrementing ETag. Boards map to S3 objects via a hardcoded dict (e.g., bucket `buc-personal`). No local file storage — fetch on every call, write back on every mutation.
- **Parser Module**: A deep module that takes raw Markdown text, produces an internal representation of columns and items, and can serialize the internal representation back to Markdown. Preserves all non-item content (frontmatter, settings footers, separators, blank lines) exactly as-is.
- **Item Identification**: Items are numbered by their position in the file (top-to-bottom, continuing across columns). Numbers are computed fresh on every call — no persistent sequence store. Item identity is based on its full text content (including checkbox marker).
- **Checkbox State Logic**: Column-driven. If a column has a `**Complete**` sub-header, all items in that column use `- [x]`. Otherwise, items use `- [ ]`. Set automatically on add and on move (based on target column).
- **Column Discovery**: Columns are identified by `## ` headers (case-insensitive matching). Pre-existing columns only — `kanban_add_item` fails if the target column doesn't exist.
- **Default Column**: The first `## ` column in the file (by order of appearance).
- **Placement**: `prepend=false` (default) appends the item after all existing items in the column. `prepend=true` inserts before all existing items in the column.
- **Tool Return Values**: All three tools return the refreshed `kanban_list_items` output (JSON list of `{number, column_name, text}`) so agents always see the current state.
- **Archive Handling**: The Archive column is detected by name (case-insensitive). When `archive=false`, it's shown in `kanban_list_items` but with an empty items list. When `archive=true`, it's included normally.
- **Conflict Resolution**: On ETag mismatch during `put_object`, return an error with a clear message instructing the caller to refetch items via `kanban_list_items` and retry. No auto-retry logic.
- **Format Support**: Both the simple Kanban format (just `## ` headers + items) and the Obsidian Kanban plugin format (frontmatter, `%% kanban:settings` footer, `**Complete**` markers, `***` separators) are supported. The parser preserves all structural content it doesn't explicitly modify.
- **Module Structure**:
  - `src/kanban/parser.py` — Markdown parsing, serialization, item/column metadata extraction
  - `src/kanban/tools.py` — FastMCP tool definitions (`kanban_add_item`, `kanban_list_items`, `kanban_move_item`)
  - `src/kanban/s3.py` — S3 fetch/write with ETag handling
  - `src/kanban/models.py` — Internal data models (Column, Item, BoardState)
  - `src/kanban/config.py` — Board-to-S3 mapping

## Testing Decisions

- **`parser` module**: Unit tests in `tests/test_kanban_parser.py`. Test parsing of both fixture formats (`kanban.md` and `agentKanban.md`). Verify that: columns are detected correctly, items are extracted with correct checkbox state, non-item content (frontmatter, settings footer, separators) is preserved on serialization, `**Complete**` markers are preserved, whitespace trimming works, and multi-line items with `<br><br>` are handled as single items.
- **`s3` module**: Unit tests against a `DummyS3` abstraction — a minimal implementation that stores raw strings in memory with auto-incrementing ETags. Verify `get_object` returns correct content and ETag, `put_object` uses conditional write, ETag mismatch is detected and raises an error.
- **`tools` module**: Integration tests using the `Client` fixture pattern from `tests/test_mcp_coding.py`. Test each tool end-to-end using the `DummyS3` abstraction. Verify `kanban_add_item` with and without `column_name`, with and without `prepend`. Verify `kanban_list_items` with `archive=true` and `archive=false`. Verify `kanban_move_item` correctly relocates items and adjusts checkbox state based on target column. Verify error on non-existent column.
- **`models` module**: Unit tests for data model correctness — Item text trimming, Column name comparison, BoardState serialization round-trip.
- **External behavior only**: Tests verify tool inputs/outputs and S3 interactions. No testing of FastMCP internals or HTTP transport details.

## Out of Scope

- Item editing or deletion — items can only be added, listed, or moved (including to Archive).
- Checkbox toggling without moving — checkbox state is always derived from column.
- Column creation — columns must pre-exist in the file.
- Column renaming or reordering.
- Subtasks, checklists, or nested items — only flat checkbox items.
- Rich item attributes — no tags, due dates, assignees, or metadata beyond text.
- Real-time collaboration or webhooks — S3-level conflict prevention only.
- Authentication or authorization — internal network only.
- Board creation or S3 bucket management — boards must already exist in S3.
- File format validation or linting — the parser trusts the input format.
- Logging or metrics specific to kanban operations — uses the existing metrics infrastructure.

## Further Notes

- **PRD filename**: `0005-feature-kanban.md` — follows the naming convention `{number}-feature-{short-name}.md`.
- **Existing integration**: The `buc-personal` server is already wired into `src/mcp.py` and `src/server.py` (imports `mcp_personal` from `src.kanban.tools`, mounts at `/buc-personal`).
- **Existing fixtures**: `tests/fixtures/kanban.md` (simple format) and `tests/fixtures/agentKanban.md` (Obsidian Kanban plugin format with frontmatter, `**Complete**`, `***` separators, `%% kanban:settings`) serve as test data and format references.
- **S3 dependency**: The server requires AWS credentials (standard boto3 credential chain — env vars, IAM role, shared credentials file). No additional auth abstraction needed.
- **DummyS3**: A minimal in-memory abstraction for testing — stores raw strings with auto-incrementing ETags. Used by all kanban tests instead of mocking the real S3 API.
- **No local state**: The server is intentionally stateless across calls. Each tool call is a full fetch-parse-modify-write cycle. This eliminates sync issues but means sequence numbers reset per call.
- **Conflict error message**: Should be explicit — something like "Board was modified since you last read it. Call `kanban_list_items` to refresh, then retry your operation."

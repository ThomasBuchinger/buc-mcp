# PRD: Batch Kanban Item Move

## Problem Statement

When an AI agent asks to move multiple Kanban items in a single turn, it calls `kanban_move_item` multiple times sequentially. Each call independently fetches the board from S3, parses it, applies one move, and writes back. Between consecutive calls, the board state changes — item line indices shift as items are removed and reinserted. This causes off-by-one errors: the agent's second move reference points to the wrong line, moving an unintended item or failing entirely.

## Solution

Modify the existing `kanban_move_item` tool to accept a batch of item numbers and move them all to the same column in a single atomic operation. The tool validates all item numbers exist before performing any moves, then removes all source lines, reparses for fresh indices, and inserts all moved items in one write cycle. A single S3 fetch-write roundtrip eliminates the index-shift problem.

## User Stories

1. As an AI agent, I want to pass a list of item numbers to `kanban_move_item` so that I can move multiple items to the same column in a single call.
2. As an AI agent, I want the batch move to be atomic — if any item number doesn't exist, no moves are applied — so that I never end up in a partially-moved state.
3. As an AI agent, I want the moved items to appear in their original file order in the target column, so that the relative ordering of items I'm moving as a group is preserved.
4. As an AI agent, I want `prepend=true` to work with batch moves, placing all moved items above existing items in the target column, so that I can create high-priority groups of tasks.
5. As an AI agent, I want a clear error message listing the missing item number(s) when a batch move fails, so that I can identify exactly which reference was wrong.
6. As an AI agent, I want the current board state included in the error response when a batch move fails, so that I can refresh my understanding of the board without a separate tool call.
7. As an AI agent, I want the tool description to clearly communicate that each call causes index changes and that I should not call the single-item form multiple times without refetching, so that I understand why the batch form exists.
8. As an AI agent, I can wrap a single item number in a list to move one item, so that I use a consistent pattern for all move operations.
9. As a user, I want the board file to be written at most once per move operation, so that ETag conflicts are reduced and concurrent edits are less likely to collide.
10. As an operator, I want the change to be a schema-breaking update (parameter rename `number` → `numbers`) so that agents adopt the batch-aware interface when the new MCP version is deployed.
11. As an AI agent, I know that `numbers` is always a list, even for single-item moves, so that I use a consistent pattern across all move operations.
12. As an AI agent, I want to know that all items in a batch move go to the same target column, so that I understand the scope of what the tool supports.

## Implementation Decisions

- **Parameter rename**: The existing `number` parameter is renamed to `numbers` with type `list[int]`. Always a list, even for single-item moves.
- **Breaking change**: Agents must re-read the MCP tool schema after deployment. The old `number` parameter name will not be recognized. Single-item moves must use `{"numbers": [3]}` instead of `{"number": 3}`.
- **Atomic validation**: All item numbers are validated against the *original* parsed board state before any lines are removed. If any number is not found, the entire operation fails.
- **No duplicate numbers**: If the same number appears twice in the `numbers` list, the operation fails.
- **Same column constraint**: All items in a batch move go to the same target column (`column_name`). Different columns per item are not supported.
- **Original file order**: When items are reinserted into the target column, they appear in the same relative order they had in the original file (top-to-bottom order).
- **Prepend with batch**: When `prepend=true`, all moved items are inserted above existing items in the target column. They maintain their original file order among themselves.
- **Single fetch-write**: One S3 read → parse → validate → modify → serialize → write cycle. One ETag. One write.
- **Error response format**: On failure, the tool returns an error with: (1) a clear message naming the missing item number(s), and (2) the current board state as a `kanban_list_items` output included in the error response body.
- **Tool description update**: The description is updated to explicitly state that each call modifies item indices and that multiple moves should use the batch form rather than calling the tool repeatedly.
- **Always a list**: `numbers` is always `list[int]`. Single-item moves require `{"numbers": [5]}` instead of `{"numbers": 5}`. This is a small but deliberate change in agent call patterns.

## Public Interface

### parser module (`src.kanban.parser`)

```
BoardState — dataclass representing parsed kanban file

parse(text: str) -> BoardState

move_item(state: BoardState, numbers: list[int], column_name: str, prepend: bool = False) -> BoardState
```

The `move_item` function is the core change. It accepts `numbers` as `list[int]`, validates all numbers exist in the original state, removes all matching item lines atomically, and reinserts them into the target column.

### tools module (`src.kanban.tools`)

```
kanban_move_item(board: str, numbers: list[int], column_name: str, prepend: bool = False) -> list[dict] | ErrorWithBoardState
```

MCP tool definition. Parameter `number` is replaced by `numbers` (always a `list[int]`). On error, returns a structured response containing the error message and the current board state.

### s3 module (`src.kanban.s3`)

No changes. The existing ETag-based conflict prevention applies to the single write cycle.

## Testing Decisions

- **parser module**: Unit tests for `move_item` with: single item (one-element list), multiple items (multi-element list), missing item (error), duplicate numbers (error), prepend=false order preservation, prepend=true order preservation, cross-column moves, move to same column (no-op validation).
- **tools module**: Integration tests using `DummyS3` and `Client` fixture: batch move end-to-end, error response includes board state, single-item move via one-element list, error on missing item number, error on unknown column.
- **Prior art**: Follows the pattern in `tests/test_kanban_tools.py` (integration tests via MCP client) and `tests/test_kanban_parser.py` (parser unit tests with `DummyS3` abstraction).
- **External behavior only**: Tests verify tool inputs and outputs. No testing of internal validation logic directly.

## Out of Scope

- Moving items to different columns in a single call — all items go to the same target column.
- Moving items with different prepend values — `prepend` applies to all items in the batch.
- Moving items while also adding items in a single call — batch move is separate from `kanban_add_item`.
- Item reordering within the same column — the tool only changes columns, not relative order beyond prepend/append.
- Renaming the tool — `kanban_move_item` stays as-is, just with a modified parameter signature.
- A separate `kanban_move_items` (plural) tool — the existing tool handles both single and batch via the type of `numbers`.

## Further Notes

- **PRD filename**: `010-feature-batch-kanban-move.md` — follows the naming convention, next available number after 009.
- **Dependency**: Builds on the existing `kanban_move_item` tool from PRD 005. No new tools are created.
- **Schema breaking change**: This is a deliberate breaking change. The MCP tool schema will change from `{"number": int, ...}` to `{"numbers": list[int], ...}`. Agents that re-read the schema on deployment will pick up the new interface automatically.
- **Agent call pattern change**: Single-item moves now require `{"numbers": [5]}` instead of `{"number": 5}`. The agent can handle this easily — it's just wrapping a single int in a list.
- **Agent guidance**: The tool description should be written to guide agents toward the batch form when moving multiple items. This is a documentation-level safeguard, not a technical enforcement.
- **The original problem**: An agent asking "move items 1, 3, and 5 to Done" would previously call `kanban_move_item` three times. After the first call, item 3 is now item 2 (or doesn't exist if it was below the moved item). After the second call, item 5 might be item 3 or 4. The batch form avoids this entirely by resolving all references against the pre-modification state.
- **Call pattern**: Before: `kanban_move_item(board, number=1, column="Done")` → `kanban_move_item(board, number=3, column="Done")` → `kanban_move_item(board, number=5, column="Done")`. After: `kanban_move_item(board, numbers=[1,3,5], column="Done")`.

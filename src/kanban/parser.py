"""Line-based Kanban Markdown parser.

The parser keeps the original file intact (split by lines) and only locates
columns (``## `` headers) and items (``- [ ]`` / ``- [x]`` lines). Operations
add/remove/move whole lines and reparse, so all non-item content (frontmatter,
``**Complete**`` markers, ``***`` separators, ``%% kanban:settings`` footers,
blank lines) is preserved verbatim.
"""

import re
from dataclasses import dataclass, field

# ── Board configuration ──────────────────────────────────────────────────────

BOARDS: dict[str, dict[str, str]] = {
    "General": {
        "bucket": "obsidian-sync",
        "key": "vault/buc/3_Project/AgentKanban.md",
        "description": "Default board for small misc tasks. Use this board unless specified differently. expecially if you're using the remindme skill",
    },
    # "Homelab": {
    #     "bucket": "obsidian-sync",
    #     "key": "vault/buc/3_Project//Homelab.md",
    #     "description": "Use this board, when you detect the conversation is about self hosting Applications or Kubernetes or Software Engineering/Development/Programming topics. Keywords: Homelab, lab, apps, services. If unsure, ask the user if you should use this board",
    # },
    # "Food": {
    #     "bucket": "obsidian-sync",
    #     "key": "vault/buc/3_Project//Food.md",
    #     "description": "This board is basically a Grocery list. Use this board, when the user asks you to remind them to buy food items. Keywords: essen, food",
    # },
}

TEST_BOARDS: dict[str, dict[str, str]] = {
    "todo": {
        "bucket": "buc-personal",
        "key": "kanban.md",
        "description": "Personal task board",
    },
    "obsidian": {
        "bucket": "buc-personal",
        "key": "agentKanban.md",
        "description": "Obsidian Kanban board",
    },
}


def get_board(name: str) -> dict[str, str]:
    import os
    boards = BOARDS if os.environ.get("AWS_ENDPOINT_URL") else TEST_BOARDS
    if name not in boards:
        raise ValueError(
            f"Unknown board: {name!r}. Available boards: {list(boards)}"
        )
    return boards[name]


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Column:
    name: str
    line_index: int
    is_complete: bool = False
    is_archive: bool = False
    item_line_indices: list[int] = field(default_factory=list)

    @property
    def normalized_name(self) -> str:
        return self.name.strip().lower()


@dataclass
class Item:
    number: int
    column_name: str
    text: str
    checked: bool
    line_index: int


@dataclass
class BoardState:
    lines: list[str]
    columns: list[Column] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)


# ── Parser ───────────────────────────────────────────────────────────────────

ITEM_RE = re.compile(r"^- \[([ x])\]\s+(.*)$")
COLUMN_RE = re.compile(r"^##\s+(.+?)\s*$")
COMPLETE_RE = re.compile(r"^\*\*Complete\*\*\s*$")


def parse(text: str) -> BoardState:
    lines = text.split("\n")
    state = BoardState(lines=lines)
    current: Column | None = None
    for i, line in enumerate(lines):
        m = COLUMN_RE.match(line)
        if m:
            name = m.group(1).strip()
            current = Column(
                name=name,
                line_index=i,
                is_archive=(name.strip().lower() == "archive"),
            )
            state.columns.append(current)
            continue
        if current is not None:
            if COMPLETE_RE.match(line):
                current.is_complete = True
                continue
            if ITEM_RE.match(line):
                current.item_line_indices.append(i)
    _assign_numbers(state)
    return state


def _assign_numbers(state: BoardState) -> None:
    state.items = []
    n = 0
    for col in state.columns:
        for idx in col.item_line_indices:
            n += 1
            im = ITEM_RE.match(state.lines[idx])
            checked = im.group(1) == "x"
            body = im.group(2).strip()
            state.items.append(
                Item(
                    number=n,
                    column_name=col.name,
                    text=body,
                    checked=checked,
                    line_index=idx,
                )
            )


def serialize(state: BoardState) -> str:
    return "\n".join(state.lines)


def list_items(state: BoardState, archive: bool = False) -> list[dict]:
    result: list[dict] = []
    for item in state.items:
        col = find_column_by_name(state.columns, item.column_name)
        if col is not None and col.is_archive and not archive:
            continue
        result.append(
            {
                "number": item.number,
                "column_name": item.column_name,
                "text": item.text,
            }
        )
    return result


def find_column_by_name(columns: list[Column], name: str) -> Column | None:
    target = name.strip().lower()
    for c in columns:
        if c.normalized_name == target:
            return c
    return None


def _item_line(checked: bool, text: str) -> str:
    mark = "x" if checked else " "
    return f"- [{mark}] {text}"


def _column_body_start(state: BoardState, col: Column) -> int:
    """First line after the header and any ``**Complete**`` marker."""
    idx = col.line_index + 1
    while idx < len(state.lines) and COMPLETE_RE.match(state.lines[idx]):
        idx += 1
    return idx


def _insertion_index(state: BoardState, col: Column, prepend: bool) -> int:
    if prepend and col.item_line_indices:
        return col.item_line_indices[0]
    if not col.item_line_indices:
        return _column_body_start(state, col)
    return col.item_line_indices[-1] + 1


def add_item(
    state: BoardState, column_name: str, text: str, prepend: bool = False
) -> BoardState:
    col = find_column_by_name(state.columns, column_name)
    if col is None:
        raise ValueError(f"Column {column_name!r} does not exist")
    text = text.strip()
    new_line = _item_line(col.is_complete, text)
    insert_at = _insertion_index(state, col, prepend)
    state.lines.insert(insert_at, new_line)
    return parse(serialize(state))


def _validate_no_duplicate_numbers(numbers: list[int]) -> None:
    if len(numbers) != len(set(numbers)):
        raise ValueError(
            f"Duplicate item numbers in batch: {sorted(set(n for n in numbers if numbers.count(n) > 1))}"
        )


def _validate_numbers_exist(state: BoardState, numbers: list[int]) -> None:
    existing = {it.number for it in state.items}
    missing = [n for n in numbers if n not in existing]
    if missing:
        raise ValueError(f"Cannot find item(s) with number(s): {missing}")


def move_item(
    state: BoardState, numbers: list[int], column_name: str, prepend: bool = False
) -> BoardState:
    target_col = find_column_by_name(state.columns, column_name)
    if target_col is None:
        raise ValueError(f"Column {column_name!r} does not exist")

    _validate_no_duplicate_numbers(numbers)
    _validate_numbers_exist(state, numbers)

    by_number = {it.number: it for it in state.items}
    items_in_order = list(by_number[n] for n in numbers)
    for idx in (it.line_index for it in reversed(items_in_order)):
        state.lines.pop(idx)

    state = parse(serialize(state))
    target_col = find_column_by_name(state.columns, column_name)
    assert target_col is not None

    insert_at = _insertion_index(state, target_col, prepend)
    for item in items_in_order:
        state.lines.insert(insert_at, _item_line(target_col.is_complete, item.text.strip()))
        insert_at += 1

    return parse(serialize(state))

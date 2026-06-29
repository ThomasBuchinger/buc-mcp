"""FastMCP tool definitions for the Kanban board.

Every tool performs a full fetch -> parse -> modify -> write cycle so the
server stays stateless across calls. All three tools return the refreshed
``kanban_list_items`` output so agents always see the latest board state.
"""

from fastmcp import FastMCP

from src.kanban import parser
from src.kanban.s3 import get_s3_client

mcp_personal = FastMCP("buc-personal")


def _build_tool_description() -> str:
    lines = ["List all items on a board."]
    lines.append("\n")
    lines.append("By default (``archive=False``) items in the Archive column are hidden.")
    lines.append("\n")
    lines.append("Available boards:")
    for name, cfg in sorted(parser.BOARDS.items()):
        desc = cfg.get("description", "")
        if desc:
            lines.append(f"- **{name}**: {desc}")
        else:
            lines.append(f"- **{name}**")
    return "".join(lines)

_s3_client = None


def set_s3_client(client) -> None:
    """Override the S3 client (used by tests to inject ``DummyS3``)."""
    global _s3_client
    _s3_client = client


def _client():
    global _s3_client
    if _s3_client is None:
        _s3_client = get_s3_client()
    return _s3_client


def _fetch(board_cfg: dict) -> tuple[str, str]:
    resp = _client().get_object(Bucket=board_cfg["bucket"], Key=board_cfg["key"])
    return resp["Body"], resp["ETag"]


def _write(board_cfg: dict, content: str, etag: str) -> None:
    _client().put_object(
        Bucket=board_cfg["bucket"],
        Key=board_cfg["key"],
        Body=content,
        IfMatch=etag,
    )


@mcp_personal.tool(description=_build_tool_description())
def kanban_list_items(board: str, archive: bool = False) -> list[dict]:
    cfg = parser.get_board(board)
    content, _ = _fetch(cfg)
    state = parser.parse(content)
    return parser.list_items(state, archive=archive)


@mcp_personal.tool
def kanban_add_item(
    board: str,
    text: str,
    column_name: str | None = None,
    prepend: bool = False,
) -> list[dict]:
    """Add a new item to a board.

    Defaults to the first column when ``column_name`` is omitted. When
    ``prepend`` is true the item is inserted before existing items in the
    column, otherwise it is appended. The checkbox state is derived from the
    target column (checked for ``**Complete**`` columns).
    """
    cfg = parser.get_board(board)
    content, etag = _fetch(cfg)
    state = parser.parse(content)
    if column_name is None:
        column_name = state.columns[0].name
    state = parser.add_item(state, column_name, text, prepend)
    _write(cfg, parser.serialize(state), etag)
    return parser.list_items(state, archive=False)


@mcp_personal.tool
def kanban_move_item(
    board: str,
    number: int,
    column_name: str,
    prepend: bool = False,
) -> list[dict]:
    """Move an item (identified by its sequence number) to another column.

    The checkbox state is adjusted based on the target column. ``prepend``
    places the item at the top of the target column.
    """
    cfg = parser.get_board(board)
    content, etag = _fetch(cfg)
    state = parser.parse(content)
    state = parser.move_item(state, number, column_name, prepend)
    _write(cfg, parser.serialize(state), etag)
    return parser.list_items(state, archive=False)

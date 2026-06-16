import os
import boto3
from botocore.exceptions import ClientError
from fastmcp import FastMCP
from src.kanban_s3.parser import KanbanBoard
from src.kanban_s3.config import KANBAN_BOARDS
from src.mcp import mcp_kanban



# board_name -> {"etag": str, "board": KanbanBoard}
_cache: dict[str, dict] = {}

def _s3():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )


def _bucket_key(board: str) -> tuple[str, str]:
    if board not in KANBAN_BOARDS:
        raise ValueError(f"Unknown board: {board}")
    b, k = KANBAN_BOARDS[board].split("/", 1)
    return b, k

def _validate(board: str) -> dict:
    if board not in _cache:
        raise ValueError(
            f"Must call list_items for board '{board}' before mutating tools"
        )
    return _cache[board]


def _write_to_s3(board: str, body: str, etag: str) -> None:
    bucket, key = _bucket_key(board)
    client = _s3()
    try:
        client.head_object(Bucket=bucket, Key=key, IfMatch=etag)
    except ClientError as e:
        if e.response["Error"]["Code"] == "PreconditionFailed":
            fresh_resp = client.get_object(Bucket=bucket, Key=key)
            fresh_board = KanbanBoard.parse(fresh_resp["Body"].read().decode("utf-8"))
            raise ValueError(
                f"Board '{board}' has been modified since you called list_items. "
                f"Call list_items again to get fresh data and retry. "
                f"Current items: {_cache[board]["board"].to_json()}"
            ) from e
        raise
    resp = client.put_object(Bucket=bucket, Key=key, Body=body)
    _cache[board]["etag"] = resp["ETag"]


@mcp_kanban.tool
async def list_items(board: str) -> list[dict]:
    """List all items on a Kanban board with global indices."""
    bucket, key = _bucket_key(board)
    resp = _s3().get_object(Bucket=bucket, Key=key)
    board_obj = KanbanBoard.parse(resp["Body"].read().decode("utf-8"))
    _cache[board] = {"etag": resp["ETag"], "board": board_obj}
    return _cache[board]["board"].to_json()


@mcp_kanban.tool
async def edit_item(board: str, index: int, new_text: str) -> list[dict]:
    """Change the text of an existing item by global index."""
    cache = _validate(board)
    if index >= len(cache["board"].items):
        raise ValueError(f"Index {index} out of range (max {len(cache['board'].items) - 1})")

    cache["board"].edit_item(index, new_text)
    _write_to_s3(board, cache["board"].render(), cache["etag"])
    return cache["board"].to_json()


@mcp_kanban.tool
async def add_item(board: str, text: str, prepend: bool = False) -> list[dict]:
    """Add a new item to a Kanban board (end of first section by default)."""
    cache = _validate(board)

    if not cache["board"].add_item(text, prepend=prepend):
        raise ValueError("No sections available on board")

    _write_to_s3(board, cache["board"].render(), cache["etag"])
    return cache["board"].to_json()


@mcp_kanban.tool
async def change_status(
    board: str, index: int, target_section: str
) -> list[dict]:
    """Move an item from one section to another by global index."""
    cache = _validate(board)
    if index >= len(cache["board"].items):
        raise ValueError(f"Index {index} out of range (max {len(cache['board'].items) - 1})")

    src = cache["board"].items[index].section_name
    if src == target_section:
        raise ValueError(f"Item already in section '{target_section}'")

    if not cache["board"].move_item(index, target_section):
        raise ValueError(f"Target section '{target_section}' does not exist on board")

    _write_to_s3(board, cache["board"].render(), cache["etag"])
    return cache["board"].to_json()

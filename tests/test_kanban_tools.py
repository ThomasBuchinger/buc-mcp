"""Integration tests for the Kanban MCP tools."""

import os
import anyio
import pytest
from fastmcp import Client

from src.kanban import tools
from src.kanban.s3 import DummyS3, CONFLICT_MESSAGE
from tests.test_kanban_parser import FIXTURES, SIMPLE, OBSIDIAN


def _call(name: str, args: dict):
    """Run an async MCP tool call synchronously."""
    async def _run():
        async with client:
            result = await client.call_tool(name, args)
            return result.data
    return anyio.run(_run)


@pytest.fixture
def dummy_s3():
    s3 = DummyS3()
    s3.dummyS3_set_content("buc-personal", "kanban.md", SIMPLE)
    s3.dummyS3_set_content("buc-personal", "agentKanban.md", OBSIDIAN)
    tools.set_s3_client(s3)
    return s3


@pytest.fixture(autouse=True)
def _setup_client(dummy_s3):
    os.environ.pop("AWS_ENDPOINT_URL", None)
    global client
    client = Client(tools.mcp_personal)


def test_kanbanListItems_works():
    items = _call("kanban_list_items", {"board": "todo"})
    assert len(items) != 0
    assert items[0] == {"number": 1, "column_name": "Todo", "text": "First task"}

def test_kanbanAddItem_works():
    items = _call("kanban_add_item", {"board": "todo", "column_name": "Done", "text": "Brand new"})

def test_kanbanAddItem_defaults_to_the_first_column():
    items = _call("kanban_add_item", {"board": "todo", "text": "Brand new"})
    todo_items = [it for it in items if it["column_name"] == "Todo"]
    assert todo_items[-1]["text"] == "Brand new"

def test_etag_conflict_on_concurrent_write(dummy_s3):
    original_put = dummy_s3.put_object
    def conflicting_put(*args, **kwargs):
        kwargs["IfMatch"] = '"stale"'
        return original_put(*args, **kwargs)
    dummy_s3.put_object = conflicting_put
    with pytest.raises(Exception):
        _call("kanban_add_item", {"board": "todo", "text": "second"})


def test_kanbanMoveItem_single_via_list():
    items = _call("kanban_move_item", {"board": "todo", "numbers": [1], "column_name": "Done"})
    done_items = [it for it in items if it["column_name"] == "Done" and it["text"] == "First task"]
    assert len(done_items) == 1
    todo_items = [it for it in items if it["column_name"] == "Todo"]
    assert all(it["text"] != "First task" for it in todo_items)


def test_kanbanMoveItem_batch_move():
    items = _call("kanban_move_item", {"board": "todo", "numbers": [1, 3], "column_name": "Done"})
    done_items = [it for it in items if it["column_name"] == "Done"]
    done_texts = [it["text"] for it in done_items]
    assert "First task" in done_texts
    assert any("Login bug" in text for text in done_texts)
    todo_items = [it for it in items if it["column_name"] == "Todo"]
    assert all("Login bug" not in it["text"] for it in todo_items)
    assert all(it["text"] != "First task" for it in todo_items)


def test_kanbanMoveItem_batch_missing_number_returns_error():
    with pytest.raises(Exception):
        _call("kanban_move_item", {"board": "todo", "numbers": [1, 999], "column_name": "Done"})


def test_kanbanMoveItem_batch_duplicate_number_returns_error():
    with pytest.raises(Exception):
        _call("kanban_move_item", {"board": "todo", "numbers": [1, 1], "column_name": "Done"})


def test_kanbanMoveItem_batch_unknown_column_returns_error():
    with pytest.raises(Exception):
        _call("kanban_move_item", {"board": "todo", "numbers": [1, 2], "column_name": "Nonexistent"})

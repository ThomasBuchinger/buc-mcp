"""Unit tests for the Kanban parser."""

from pathlib import Path

from src.kanban import parser

FIXTURES = Path(__file__).parent / "fixtures"
SIMPLE = (FIXTURES / "kanban.md").read_text()
OBSIDIAN = (FIXTURES / "agentKanban.md").read_text()


def test_can_read_columns_in_simple_kanbanboard():
    state = parser.parse(SIMPLE)
    names = [c.name for c in state.columns]
    assert names == ["Todo", "In Progress", "Review", "Empty", "Done"]

def test_numberic_item_number_works_across_columns():
    state = parser.parse(SIMPLE)
    for index, item in enumerate(state.items):
        assert index+1 == item.number

def test_parser_preserves_file_content():
    state = parser.parse(OBSIDIAN)
    assert parser.serialize(state) == OBSIDIAN

def test_parser_preserves_file_content_even_if_it_is_completely_invalid():
    invalid_content = """
    ---
    apiVersion: v1

    - [ ] item without header
    # this is actually a comment

    **Complete**
    """
    state = parser.parse(invalid_content)
    assert parser.serialize(state) == invalid_content

def test_an_empty_column_is_preserved():
    state = parser.parse(SIMPLE)
    assert "## Empty" in parser.serialize(state)

def test_detect_complete_marker_for_column():
    state = parser.parse(OBSIDIAN)
    done = next(c for c in state.columns if c.name == "Done")
    assert done.is_complete is True

def test_archive_column_is_detected_as_special_column():
    state = parser.parse(OBSIDIAN)
    archive = next(c for c in state.columns if c.name == "Archive")
    assert archive.is_archive is True

def test_item_checkbox_refects_column():
    state = parser.parse(OBSIDIAN)
    get_testcard = lambda: next(item for item in state.items if item.text == "TestCard")
    assert get_testcard().checked == False
    state = parser.move_item(state, get_testcard().number, "Done")
    assert get_testcard().checked == True
    state = parser.move_item(state, get_testcard().number, "Open")
    assert get_testcard().checked == False
    
def test_multiline_br_items_treated_as_single():
    state = parser.parse(SIMPLE)
    item = next(it for it in state.items if "Login bug" in it.text)
    assert "<br><br>" in item.text
    assert "User cannot log in" in item.text

def test_item_text_trimmed():
    md = "## Todo\n\n- [ ]   spaced task   \n"
    state = parser.parse(md)
    assert state.items[0].text == "spaced task"


def test_case_insensitive_column_lookup():
    state = parser.parse(SIMPLE)
    assert parser.find_column_by_name(state.columns, "todo") is not None
    assert parser.find_column_by_name(state.columns, "TODO") is not None
    assert parser.find_column_by_name(state.columns, " ToDo ") is not None


def test_add_item_append_default():
    state = parser.parse(SIMPLE)
    state = parser.add_item(state, "Todo", "New task")
    todo_items = [it for it in state.items if it.column_name == "Todo"]
    assert todo_items[-1].text == "New task"
    assert todo_items[-1].checked is False


def test_add_item_prepend():
    state = parser.parse(SIMPLE)
    state = parser.add_item(state, "Todo", "Priority", prepend=True)
    todo_items = [it for it in state.items if it.column_name == "Todo"]
    assert todo_items[0].text == "Priority"


def test_add_item_defaults_checkbox_for_complete_column():
    state = parser.parse(OBSIDIAN)
    state = parser.add_item(state, "Done", "Done task", prepend=False)
    done_items = [it for it in state.items if it.column_name == "Done"]
    assert any(it.text == "Done task" and it.checked for it in done_items)


def test_add_item_nonexistent_column_raises():
    state = parser.parse(SIMPLE)
    try:
        parser.add_item(state, "Nonexistent", "x", prepend=False)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_move_item_relocates_line():
    state = parser.parse(SIMPLE)
    state = parser.move_item(state, number=1, column_name="Done", prepend=False)
    done_items = [it for it in state.items if it.column_name == "Done"]
    assert any(it.text == "First task" for it in done_items)
    todo_items = [it for it in state.items if it.column_name == "Todo"]
    assert all(it.text != "First task" for it in todo_items)

def test_move_item_nonexistent_number_raises():
    state = parser.parse(SIMPLE)
    try:
        parser.move_item(state, number=999, column_name="Done", prepend=False)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_list_items_excludes_archive_by_default():
    state = parser.parse(OBSIDIAN)
    out = parser.list_items(state, archive=False)
    assert all(it["column_name"] != "Archive" for it in out)


def test_list_items_includes_archive_when_requested():
    state = parser.parse(OBSIDIAN)
    out = parser.list_items(state, archive=True)
    assert any(it["column_name"] == "Archive" for it in out)


def test_list_items_returns_number_column_text():
    state = parser.parse(SIMPLE)
    out = parser.list_items(state)
    assert all(set(it.keys()) == {"number", "column_name", "text"} for it in out)
    assert out[0]["number"] == 1


def test_move_item_to_archive_hides_from_default_list():
    state = parser.parse(OBSIDIAN)
    state = parser.move_item(state, number=1, column_name="Archive")
    items = parser.list_items(state)
    assert all(it["text"] != "Meeting mit david" for it in items)
    archived = parser.list_items(state, archive=True)
    assert any(it["text"] == "Meeting mit david" for it in archived)

import pytest
from pathlib import Path

from src.kanban_s3.parser import KanbanBoard, KanbanItem

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def kanban():
    return (FIXTURES / "kanban.md").read_text()

def filter_by_section(section: str, items: list[KanbanItem]) -> list[KanbanItem]:
    return [i for i in items if i.section_name == section]

def test_parse_valid_kanban_board_works(kanban):
    board = KanbanBoard.parse(kanban)
    assert len(board.to_items()) != 0

def test_parse_can_parse_section_names(kanban):
    board = KanbanBoard.parse(kanban)
    assert board.sections == ["Todo", "In Progress", "Review", "Empty", "Done"]

def test_render_produces_the_same_output(kanban):
    board = KanbanBoard.parse(kanban)
    
    assert kanban == board.render()


def test_addItem_can_add_item_to_board(kanban):
    board = KanbanBoard.parse(kanban)
    item_count = len(board.to_items())
    board.add_item("MY_UNITTEST_ITEM")
    assert len(board.to_items()) == item_count + 1

def test_addItems_renders_new_item(kanban):
    board = KanbanBoard.parse(kanban)
    board.add_item("MY_UNITTEST_ITEM")
    assert "- [ ] MY_UNITTEST_ITEM" in board.render()

def test_addItems_can_add_items_at_the_top(kanban):
    board = KanbanBoard.parse(kanban)
    board.add_item("MY_UNITTEST_ITEM", prepend=True)
    first = filter_by_section("Todo", board.to_items())[0]
    assert first.text == "MY_UNITTEST_ITEM"

def test_addItems_can_add_items_at_the_end_by_default(kanban):
    board = KanbanBoard.parse(kanban)
    board.add_item("MY_UNITTEST_ITEM")
    first = filter_by_section("Todo", board.to_items())[-1]
    assert first.text == "MY_UNITTEST_ITEM"

def test_addItem_fails_adding_item_to_non_existent_section(kanban):
    board = KanbanBoard.parse(kanban)
    success = board.move_item(0, "Non Existing Column")
    assert success == False
    
def test_editItem_can_edit_item(kanban):
    board = KanbanBoard.parse(kanban)
    assert board.items[0].text == "First task"
    board.edit_item(0, "First task - Edited")
    assert board.items[0].text == "First task - Edited"

def test_editItem_can_be_out_of_range(kanban):
    board = KanbanBoard.parse(kanban)
    success = board.edit_item(999, "First task - Edited")
    assert success == False

def test_editItem_fails_to_edit_non_exising_index(kanban):
    board = KanbanBoard.parse(kanban)
    success = board.edit_item(999, "this should fail")
    assert success == False

def test_moveItem_works(kanban):
    board = KanbanBoard.parse(kanban)
    board.move_item(0, "In Progress")
    item = filter_by_section("In Progress", board.to_items())[-1]
    assert item.text == "First task"

def test_moveItem_fails_moving_to_non_existing_section(kanban):
    board = KanbanBoard.parse(kanban)
    success = board.move_item(0, "Non Existing Column")
    assert success == False

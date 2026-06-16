from __future__ import annotations

import re


class KanbanItem:
    def __init__(self, section_name: str, text: str):
        self.section_name = section_name
        self.text = text


class KanbanBoard:
    def __init__(self):
        self.items: list[KanbanItem] = []
        self.sections: list[str] = []

    @classmethod
    def parse(cls, text: str) -> KanbanBoard:
        board = cls()
        current_section: str | None = None
        for line in text.splitlines():
            match = re.match(r"^##\s+(.+)$", line)
            if match:
                current_section = match.group(1).strip()
                board.sections.append(current_section)
                continue
            if current_section is not None and re.match(r"^- \[ \] ", line):
                board.items.append(KanbanItem(current_section, line[6:]))
        return board

    def section_exists(self, section_name: str) -> bool:
        return section_name in self.sections

    def add_section(self, name: str) -> None:
        if name not in self.sections:
            self.sections.append(name)

    def to_items(self) -> list[KanbanItem]:
        return list(self.items)
    
    def to_json(self) -> list[dict]:
        return [
            {"section": i.section_name, "index": j, "text": i.text}
            for j, i in enumerate(self.items)
        ]

    def get_section_item_range(self, section_name: str) -> tuple[int, int]:
        start = None
        end = 0
        for i, item in enumerate(self.items):
            if item.section_name == section_name:
                if start is None:
                    start = i
                end = i + 1
        if start is None:
            start = end
        return start, end

    def add_item(self, text: str, prepend: bool = False, section: str | None = None) -> bool:
        target = section or self.sections[0]
        if not self.section_exists(target):
            return False
        start, end = self.get_section_item_range(target)
        pos = start if prepend else end
        self.items.insert(pos, KanbanItem(target, text))
        return True

    def edit_item(self, global_index: int, new_text: str) -> bool:
        if global_index < 0 or global_index >= len(self.items):
            return False
        self.items[global_index].text = new_text
        return True

    def move_item(self, global_index: int, target_section: str) -> bool:
        if global_index < 0 or global_index >= len(self.items):
            return False
        if not self.section_exists(target_section):
            return False
        item = self.items.pop(global_index)
        item.section_name = target_section
        self.add_item(item.text, section=target_section)
        return True

    def render(self) -> str:
        lines: list[str] = []
        for i, section in enumerate(self.sections):
            section_items = [item for item in self.items if item.section_name == section]
            if i > 0 or section_items:
                if lines:
                    lines.append("")
                lines.append(f"## {section}")
                lines.append("")
            for item in section_items:
                lines.append(f"- [ ] {item.text}")
        if self.items:
            lines.append("")
        return "\n".join(lines)

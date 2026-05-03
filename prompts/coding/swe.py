from pathlib import Path

from fastmcp.prompts import prompt

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "coding-prompts"


@prompt
def prd_create(prompt = "") -> str:
    """
    Create documentation-first PRDs that guide development through user-facing content
    """
    content = (SKILLS_DIR / "swe-prd-create" / "SKILL.md").read_text()
    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.index("---", 3)
        content = content[end + 3:].lstrip("\n")
    return content + prompt

@prompt
def prd_start(prompt = "") -> str:
    """
    Start working on a PRD implementation
    """
    content = (SKILLS_DIR / "swe-prd-start" / "SKILL.md").read_text()
    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.index("---", 3)
        content = content[end + 3:].lstrip("\n")
    return content + prompt

@prompt
def prd_next(prompt = "") -> str:
    """
    Analyze existing PRD to identify and recommend the single highest-priority task to work on next
    """
    content = (SKILLS_DIR / "swe-prd-next" / "SKILL.md").read_text()
    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.index("---", 3)
        content = content[end + 3:].lstrip("\n")
    return content + prompt

@prompt
def prd_update_decisions(prompt = "") -> str:
    """
    Update PRD based on design decisions and strategic changes made during conversations
    """
    content = (SKILLS_DIR / "swe-prd-update-decisions" / "SKILL.md").read_text()
    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.index("---", 3)
        content = content[end + 3:].lstrip("\n")
    return content + prompt


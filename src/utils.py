import frontmatter
from pathlib import Path


def skill_description(skill_dir: Path) -> str:
    """Extract the 'description' field from a SKILL.md frontmatter."""
    post = frontmatter.load(skill_dir / "SKILL.md")
    return post.metadata.get("description", "")


def skill_content(skill_dir: Path) -> str:
    """Extract the content after frontmatter from a SKILL.md."""
    post = frontmatter.load(skill_dir / "SKILL.md")
    return post.content

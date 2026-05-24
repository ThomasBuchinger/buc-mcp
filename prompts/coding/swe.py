from pathlib import Path

from fastmcp.prompts import prompt
from fastmcp.resources import resource
from src.utils import skill_content, skill_description

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


@prompt(description=skill_description(SKILLS_DIR / "coding" / "mattpocock_grill-me"))
def grill_me(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding" / "mattpocock_grill-me")
    return content + prompt
@resource("data://mattpocock_grill-me/resources/ARD-FORMAT.md")
def grill_me_adr() -> str:
    return (SKILLS_DIR / "coding" / "mattpocock_grill-me" / "resources" / "ADR-FORMAT.md").read_text()
@resource("data://mattpocock_grill-me/resources/CONTEXT-FORMAT.md")
def grill_me_adr() -> str:
    return (SKILLS_DIR / "coding" / "mattpocock_grill-me" / "resources" / "CONTEXT-FORMAT.md").read_text()


@prompt(description=skill_description(SKILLS_DIR / "coding" / "mattpocock_tdd"))
def grill_me(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding" / "mattpocock_tdd")
    return content + prompt

@prompt(description=skill_description(SKILLS_DIR / "coding" / "mattpocock_to-prd"))
def grill_me(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding" / "mattpocock_to-prd")
    return content + prompt


@prompt(description=skill_description(SKILLS_DIR / "coding" / "anthropic_frontend-design"))
def frontenddesign(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding" / "anthropic_frontend-design")
    return content + prompt
@resource("data://frontend-design/SKILL.md")
def frontentdesign_resource() -> str:
    return (SKILLS_DIR / "coding" / "anthropic_frontend-design" / "SKILL.md").read_text()

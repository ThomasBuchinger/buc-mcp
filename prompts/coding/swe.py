from pathlib import Path

from fastmcp.prompts import prompt
from src.utils import skill_content, skill_description

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


@prompt(description=skill_description(SKILLS_DIR / "coding-prompts" / "swe-prd-create"))
def prd_create(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding-prompts" / "swe-prd-create")
    return content + prompt


@prompt(description=skill_description(SKILLS_DIR / "coding-prompts" / "swe-prd-start"))
def prd_start(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding-prompts" / "swe-prd-start")
    return content + prompt


@prompt(description=skill_description(SKILLS_DIR / "coding-prompts" / "swe-prd-next"))
def prd_next(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding-prompts" / "swe-prd-next")
    return content + prompt


@prompt(description=skill_description(SKILLS_DIR / "coding-prompts" / "swe-prd-update-decisions"))
def prd_update_decisions(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding-prompts" / "swe-prd-update-decisions")
    return content + prompt


@prompt(description=skill_description(SKILLS_DIR / "coding-passive" / "mattpocock-grill-me"))
def grill_me(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding-passive" / "mattpocock-grill-me")
    return content + prompt


@prompt(description=skill_description(SKILLS_DIR / "coding-prompts" / "mattpocock-to-prd"))
def grill_to_prd(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding-prompts" / "mattpocock-to-prd")
    return content + prompt

@prompt(description=skill_description(SKILLS_DIR / "coding-prompts" / "mattpocock-prd-to-plan"))
def prd_to_plan(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "coding-prompts" / "mattpocock-prd-to-plan")
    return content + prompt

from pathlib import Path

from fastmcp.prompts import prompt
from src.utils import skill_content, skill_description

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "kubernetes-passive"


@prompt(description=skill_description(SKILLS_DIR / "kubernetes-yaml"))
def kubernetes_yaml(prompt = "") -> str:
    content = skill_content(SKILLS_DIR / "kubernetes-yaml")
    return content + prompt

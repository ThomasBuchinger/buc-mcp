from pathlib import Path

from fastmcp.prompts import prompt

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


@prompt
def kubernetes_yaml(prompt = "") -> str:
    """
    Generate production-ready Kubernetes manifests following best practices for security,
    reliability, and observability. Use this skill any time the user asks to create, write,
    or generate Kubernetes YAML. Also trigger when the user asks to "harden" or "review" an existing manifest. Always use this skill for any Kubernetes YAML generation task, even simple ones, because
    production-quality manifests require many non-obvious defaults that this skill captures.
    """
    content = (SKILLS_DIR / "kubernetes-yaml" / "SKILL.md").read_text()
    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.index("---", 3)
        content = content[end + 3:].lstrip("\n")
    return content + prompt


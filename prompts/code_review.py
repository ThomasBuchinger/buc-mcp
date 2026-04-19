from fastmcp.prompts import prompt


@prompt
def code_review(language: str = "python") -> str:
    """Review code for quality, bugs, and improvements."""
    return (
        f"Review the following {language} code. "
        "Check for bugs, security issues, performance problems, and style. "
    )

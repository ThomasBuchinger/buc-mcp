import json5
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from src.utils import skill_description, skill_content

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = ROOT_DIR / "src" / "landing_page" / "templates"
SKILLS_DIR = ROOT_DIR / "skills"
MCP_CONFIG_PATH = ROOT_DIR / "mcpconfigs" / "mcp.json"

BASE_HTML = (TEMPLATES_DIR / "base.html").read_text()
SYNC_HTML = (TEMPLATES_DIR / "sync.html").read_text()
SERVERS_HTML = (TEMPLATES_DIR / "servers.html").read_text()
SKILLS_HTML = (TEMPLATES_DIR / "skills.html").read_text()
CONFIGS_HTML = (TEMPLATES_DIR / "configs.html").read_text()

router = APIRouter()


def _render_markdown(text: str) -> str:
    parts = []
    in_code = False
    code_buf = []
    for line in text.split("\n"):
        if line.startswith("```"):
            if in_code:
                parts.append(f"<pre><code>{''.join(code_buf)}</code></pre>")
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line + "\n")
            continue
        stripped = line.strip()
        if not stripped:
            continue
        processed = line
        if processed.startswith("## "):
            processed = f"<h3>{processed[3:]}</h3>"
        elif processed.startswith("### "):
            processed = f"<h4>{processed[4:]}</h4>"
        else:
            processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', processed)
            processed = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', processed)
            processed = f"<p>{processed}</p>"
        parts.append(processed)
    if in_code:
        parts.append(f"<pre><code>{''.join(code_buf)}</code></pre>")
    return "\n".join(parts)


def _discover_skills():
    skills_by_cat = {}
    for skill_md in sorted(SKILLS_DIR.glob("*/*/SKILL.md")):
        cat = skill_md.parent.parent.name
        name = skill_md.parent.name
        skills_by_cat.setdefault(cat, []).append(name)
    return skills_by_cat


@router.get("/", response_class=HTMLResponse)
async def landing_page():
    return BASE_HTML


@router.get("/sections/sync", response_class=HTMLResponse)
async def section_sync(request: Request):
    host = request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", "http")
    server_url = f"{scheme}://{host}"
    return SYNC_HTML.replace("{server_url}", server_url)


@router.get("/sections/servers", response_class=HTMLResponse)
async def section_servers():
    from starlette.routing import Mount
    from src.server import app

    mounted = set()
    for route in app.routes:
        if isinstance(route, Mount) and hasattr(route, "app") and hasattr(route.app, "routes"):
            for sub in route.app.routes:
                if sub.path.rstrip("/") == "/mcp":
                    mounted.add(route.path)
                    break

    known = ["buc-coding", "buc-kubernetes", "buc-skills", "buc-personal", "buc-context7"]
    rows = ""
    for name in known:
        path = f"/{name}"
        mcp_path = f"{path}/mcp"
        display = name.removeprefix("buc-")
        ok = path in mounted
        cls = "mounted" if ok else "unmounted"
        label = "Mounted" if ok else "Not Configured"
        rows += (
            f'<tr><td class="server-name">{display}</td>'
            f'<td class="server-path">{mcp_path}</td>'
            f'<td><span class="status-badge {cls}">'
            f'<span class="status-dot {cls}"></span>{label}'
            f"</span></td></tr>"
        )
    return SERVERS_HTML.replace("{rows}", rows)


@router.get("/sections/skills", response_class=HTMLResponse)
async def section_skills():
    skills_by_cat = _discover_skills()
    categories_html = ""
    for cat_idx, (cat, skill_names) in enumerate(sorted(skills_by_cat.items())):
        safe_id = f"cat-items-{cat_idx}"
        categories_html += (
            f'<div class="skill-category">'
            f'<button class="category-header" '
            f'hx-get="/sections/skills/{cat}" '
            f'hx-trigger="click" '
            f'hx-target="#{safe_id}" '
            f'hx-swap="innerHTML">'
            f'<span class="arrow">▸</span> {cat}'
            f'<span class="cat-count">{len(skill_names)} skills</span>'
            f"</button>"
            f'<div id="{safe_id}" class="category-items"></div>'
            f"</div>"
        )
    return SKILLS_HTML.replace("{categories}", categories_html)


@router.get("/sections/skills/{category}", response_class=HTMLResponse)
async def section_skills_category(category: str):
    cat_dir = SKILLS_DIR / category
    if not cat_dir.is_dir():
        return HTMLResponse("", status_code=404)
    items = ""
    for skill_md in sorted(cat_dir.rglob("*/SKILL.md")):
        name = skill_md.parent.name
        desc = skill_description(skill_md.parent)
        desc_html = f'<span class="skill-desc">{desc}</span>' if desc else ""
        items += (
            f'<a class="skill-link" href="#skill-viewer" '
            f'hx-get="/sections/skill/{name}" '
            f'hx-trigger="click" '
            f'hx-target="#skill-viewer" '
            f'hx-swap="innerHTML">'
            f"{name}{desc_html}</a>"
        )
    if not items:
        return HTMLResponse("", status_code=404)
    return HTMLResponse(items)


@router.get("/sections/skill/{skill_name}", response_class=HTMLResponse)
async def section_skill(skill_name: str):
    matches = list(SKILLS_DIR.rglob(f"*/{skill_name}/SKILL.md"))
    if not matches:
        return HTMLResponse("<p>Skill not found</p>", status_code=404)
    raw = skill_content(matches[0].parent)
    html = _render_markdown(raw)
    styled = (
        '<div class="skill-content">'
        f'<div class="skill-content-header">{skill_name}</div>'
        f'<div class="skill-content-body">{html}</div>'
        f"</div>"
        '<style>'
        ".skill-content{font-size:0.82rem;line-height:1.7}"
        ".skill-content-header{font-size:0.9rem;font-weight:600;color:var(--accent);margin-bottom:0.75rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border)}"
        ".skill-content-body h3{font-size:0.95rem;font-weight:600;margin:1rem 0 0.5rem;color:var(--text-primary)}"
        ".skill-content-body h4{font-size:0.85rem;font-weight:600;margin:0.75rem 0 0.4rem;color:var(--text-primary)}"
        ".skill-content-body p{margin:0 0 0.5rem;color:var(--text-secondary)}"
        ".skill-content-body a{color:var(--blue);text-decoration:underline}"
        ".skill-content-body a:hover{color:var(--accent)}"
        ".skill-content-body pre{background:var(--bg-surface);border:1px solid var(--border);border-radius:4px;padding:0.75rem;margin:0.5rem 0;overflow-x:auto}"
        ".skill-content-body code{font-family:var(--font-mono);font-size:0.76rem;line-height:1.5}"
        ".skill-content-body pre code{background:none;padding:0}"
        ".skill-content-body strong{color:var(--text-primary)}"
        "</style>"
    )
    return HTMLResponse(styled)


@router.get("/sections/configs", response_class=HTMLResponse)
async def section_configs():
    data = json5.loads(MCP_CONFIG_PATH.read_text())
    servers = data.get("mcp", data.get("mcpServers", {}))
    rows = ""
    for name, cfg in sorted(servers.items()):
        server_type = cfg.get("type", "unknown")
        url_or_cmd = cfg.get("url", cfg.get("command", ""))
        if url_or_cmd:
            val = f'<span class="config-url">{url_or_cmd}</span>' if server_type == "remote" else f'<span class="config-cmd">{url_or_cmd}</span>'
        else:
            val = '<span class="config-cmd">—</span>'
        rows += (
            f'<tr><td class="config-name">{name}</td>'
            f'<td><span class="config-type">{server_type}</span></td>'
            f"<td>{val}</td></tr>"
        )
    return CONFIGS_HTML.replace("{rows}", rows)

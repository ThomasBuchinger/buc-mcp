# PRD: Landing Page — Server Inventory at the Root

## Problem Statement

The BUC-MCP webserver has no landing page. Browsing to the root returns a 404. Users who know the curl command for `sync.sh` must memorize it or dig through documentation. Engineers onboarding to the project have no single place to see what MCP servers are running, what skills are available, or what remote MCP configs exist.

## Solution

A single-page landing page served at `GET /` that lists everything the server exposes. The page is server-rendered and uses HTMX to lazy-load each section. No new dependencies beyond what's already installed.

## User Stories

1. As a user, I want to browse to the server root and see the sync tool curl command prominently, so that I can copy and run it immediately.
2. As a user, I want the curl command to include the correct host (injected by the server), so that it works without editing.
3. As a user, I want a copy-to-clipboard button next to the curl command, so that I can grab it in one click.
4. As a user, I want to see all running MCP servers and their mount paths, so that I know which endpoints to point my client at.
5. As a user, I want to see which MCP servers are conditionally mounted (e.g. `buc-context7` requires an API key), so that I understand why some endpoints may be absent.
6. As a user, I want to browse the skills directory in a filesystem-tree view, so that I can discover what skills exist and read their SKILL.md descriptions.
7. As a user, I want to click a skill to view its full content with basic markdown formatting, so that I can inspect a skill without leaving the browser.
8. As a user, I want to see all MCP client configs from `mcp.json` with their name, type, and URL, so that I can pick which remote servers to configure my agent with.
9. As a developer, I want each section to load independently via HTMX, so that a slow section doesn't block the rest of the page.
10. As a developer, I want the landing page code isolated in `src/landing_page/`, so that it doesn't tangle with MCP server or webserver concerns.

## Implementation Decisions

### Module structure

```
src/landing_page/
  __init__.py
  routes.py       # APIRouter with GET / and GET /sections/{name}
  templates/
    base.html     # Full HTML page (head, body skeleton, HTMX script)
    sync.html     # Sync tool curl command fragment
    servers.html  # MCP servers table fragment
    skills.html   # Skills directory tree fragment
    configs.html  # MCP configs table fragment
```

### Rendering

No template engine. HTML templates are plain `.html` files read at import time and served via `HTMLResponse`. Template variables use `{placeholder}` syntax substituted with Python `str.format()` or `str.replace()`.

### HTMX

Loaded from CDN (`https://unpkg.com/htmx.org@2`). Each section div on the base page uses `hx-get="/sections/{name}" hx-trigger="load"` to fetch its content fragment. Fallback: if HTMX fails to load, the page still renders a skeleton with a loading indicator.

### Sync tool section

Shows a code block with `curl -s {server_url}/sync.sh | bash`. The server constructs `server_url` from the incoming request's `Host` and `X-Forwarded-Proto` headers (same logic as the existing `/sync.sh` endpoint). A "Copy" button uses `navigator.clipboard.writeText()`.

### MCP Servers section

Introspects `app.routes` for mounted sub-applications whose path ends in `/mcp`. Each mount gets a row: derived server name, path, and status (mounted/unmounted). The `buc-context7` mount is conditional on `CONTEXT7_API_KEY`, so the page shows either the path or a "not configured" notice.

### Skills section

Uses `Path.rglob("skills/*/*/SKILL.md")` to discover all skills. Groups them by their parent directory (e.g. `coding/`, `coding-passive/`). Each skill shows:
- Directory name
- Description from SKILL.md frontmatter (using the existing `frontmatter` library already in dependencies)
- Link to view the full content

Skills are rendered in a collapsible tree view. Clicking a skill name loads its SKILL.md content via HTMX from `/sections/skills/{name}`, rendered with basic server-side markdown highlighting (linkified URLs, monospace for code blocks).

### MCP Configs section

Reads `mcpconfigs/mcp.json` (already parsed by the existing `/mcp.json` endpoint). Lists each config entry: server name, type (stdio/remote), and URL or command.

### Markdown rendering

For skill content viewing, no full markdown parser is added. The server does simple transformations:
- Wrap ` ``` ` blocks in `<pre><code>` (no syntax coloring)
- Replace `**text**` with `<strong>text</strong>`
- Replace `[text](url)` with `<a href="url">text</a>`
- Convert headings (`##`, `###`) to `<h3>`, `<h4>`
- Everything else as plain text in `<p>` tags

This avoids adding a markdown library dependency while still being readable.

## Testing Decisions

- **No deep module to test.** The data fetching is inline in route handlers and trivially correct (`Path.rglob`, `json.loads`, `app.routes` iteration).
- **Integration test** (`tests/test_landing_page.py`): Start the FastAPI app via `TestClient`, hit `GET /`, verify the response is HTML with an HTMX script tag and all four skeleton sections present.
- **Section tests**: Hit each `GET /sections/{name}` endpoint and verify it returns 200 with expected content (e.g. `/sections/sync` contains `curl` and `sync.sh`, `/sections/servers` contains `/buc-coding/mcp`, `/sections/skills` contains at least one skill name, `/sections/configs` contains at least one server name).
- **Prior art**: `tests/test_sync_sh_endpoint.py` and `tests/test_mcp_json_endpoint.py` demonstrate the TestClient pattern against the parent FastAPI app.

## Out of Scope

- Authentication or authorization on the landing page (same as the rest of the server — internal network only).
- Full Markdown rendering with syntax highlighting.
- Real-time updates or WebSocket connections.
- Paging or search (the inventory is small enough for one page).
- Mobile-responsive design (internal tool, desktop-first).
- Hot-reloading of template files during development.

## Further Notes

- No new Python dependencies. `frontmatter` and `json5` are already installed.
- The existing `src/utils.py` has `skill_description()` and `skill_content()` — the skills section reuses these.
- HTML template files live in `src/landing_page/templates/` as plain `.html` files, read at module level with `Path.read_text()`.
- The landing page router is registered in `src/server.py` by including it on the `app` object. No sub-mount needed — root-level routes.

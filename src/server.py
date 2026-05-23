import json
import logging
import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from fastmcp.utilities.lifespan import combine_lifespans

from src.metrics import (
    ProxyMetricsMiddleware,
    configure_logging,
    register_health_routes,
    register_metrics_route,
)
from src.mcp import (
    coding,
    coding_app,
    context7,
    context7_app,
    get_context7_api_key,
    kubernetes,
    kubernetes_app,
    syncSkill,
    syncSkill_app,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def _strip_jsonc_comments(text: str) -> str:
    """Strip // comments from JSONC (JSON with Comments) text."""
    lines = text.split("\n")
    result = []
    for line in lines:
        in_string = False
        escape = False
        new_line = []
        for i, ch in enumerate(line):
            if escape:
                new_line.append(ch)
                escape = False
                continue
            if ch == "\\" and in_string:
                new_line.append(ch)
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                new_line.append(ch)
                continue
            if not in_string and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            new_line.append(ch)
        result.append("".join(new_line))
    return "\n".join(result)


def _parse_mcps_template():
    """Parse the mcps/mcps.json template file into a dict."""
    template_path = ROOT_DIR / "mcps" / "mcps.json"
    raw = template_path.read_text()
    cleaned = _strip_jsonc_comments(raw)
    return json.loads(cleaned)


def _substitute_url(url: str, host: str, scheme: str) -> str:
    """Replace the host portion of a URL with the given host, using the given scheme."""
    match = re.match(r"(https?://)([^/]+)(/.*)?", url)
    if match:
        return f"{scheme}://{host}{match.group(3) or ''}"
    return url.replace("http://", f"{scheme}://{host}/").replace("https://", f"{scheme}://{host}/")


def _format_config(template_data: dict, agent: str, host: str, scheme: str) -> dict:
    """Format the template data into the requested agent's config format."""
    servers = template_data.get("mcp", template_data.get("mcpServers", {}))
    result = {}

    for name, config in servers.items():
        cleaned = {}
        server_type = config.get("type", "remote")

        if agent == "claude":
            if server_type == "remote":
                cleaned["type"] = "http"
            else:
                cleaned["type"] = server_type
        else:
            cleaned["type"] = server_type

        if "url" in config:
            url = config["url"]
            if scheme == "https":
                url = _substitute_url(url, host, "https")
            elif "x-forwarded-proto" in template_data.get("_meta", {}):
                url = _substitute_url(url, host, "https")
            else:
                url = _substitute_url(url, host, scheme)
            cleaned["url"] = url

        if "headers" in config:
            cleaned["headers"] = config["headers"]

        if "env" in config:
            cleaned["env"] = config["env"]

        if "args" in config:
            cleaned["args"] = config["args"]

        if "command" in config:
            cleaned["command"] = config["command"]

        result[name] = cleaned

    if agent == "claude":
        return {"mcpServers": result}
    else:
        return {"mcp": result}


_template_cache = None


def _get_template():
    global _template_cache
    if _template_cache is None:
        _template_cache = _parse_mcps_template()
    return _template_cache

configure_logging()
logger = logging.getLogger(__name__)

# FastAPI
app = FastAPI(
    lifespan=combine_lifespans(
        coding_app.lifespan,
        kubernetes_app.lifespan,
        syncSkill_app.lifespan,
        context7_app.lifespan,
    )
)
app.add_middleware(ProxyMetricsMiddleware, server_name="context7")
app.mount("/buc-coding", coding_app)
app.mount("/buc-kubernetes", kubernetes_app)
app.mount("/buc-skills", syncSkill_app)

if get_context7_api_key():
    app.mount("/buc-context7", context7_app)

# Health + metrics on parent app
register_health_routes(app, coding, kubernetes, syncSkill, context7)
register_metrics_route(app)


@app.get("/sync.sh", response_class=PlainTextResponse)
async def sync_sh(request: Request):
    sync_sh = Path(__file__).resolve().parent.parent / "scripts" / "sync.sh"

    content = sync_sh.read_text()
    host = request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", "http")
    return  f"SERVER_URL='{scheme}://{host}'\n" + content


@app.get("/mcps.json")
async def mcps_json(request: Request):
    query_params = request.query_params
    agent = query_params.get("agent", "opencode")
    host = request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", "http")

    template = _get_template()
    config = _format_config(template, agent, host, scheme)
    return JSONResponse(content=config)


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

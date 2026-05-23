import json
import json5
import logging
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
MCP_CONFIG_PATH = ROOT_DIR / "mcpconfigs" / "mcp.json"

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
    sync_sh = ROOT_DIR / "scripts" / "sync.sh"
    host = request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"SERVER_URL='{scheme}://{host}'\n" + sync_sh.read_text()


@app.get("/mcp.json")
async def mcp_json(request: Request):
    agent = request.query_params.get("agent", "opencode")
    data = json5.loads(MCP_CONFIG_PATH.read_text())
    servers = data.get("mcp", data.get("mcpServers", {}))
    if agent == "claude":
        # Claude uses "mcpServers" key and "http" type for remote servers
        for name, config in servers.items():
            if config.get("type") == "remote":
                config["type"] = "http"
        return JSONResponse(content={"mcpServers": servers})
    return JSONResponse(content={"mcp": servers})


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

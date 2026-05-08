import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
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


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

import logging
import os
import sys

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger.json import JsonFormatter
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_context7_api_key() -> str | None:
    return os.environ.get("CONTEXT7_API_KEY") or None


REQUEST_COUNT = Counter(
    "buc_mcp_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "buc_mcp_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

PROMPT_READS = Counter(
    "buc_mcp_prompt_reads_total",
    "Prompt read count",
    ["prompt_name"],
)

SKILL_READS = Counter(
    "buc_mcp_skill_reads_total",
    "Skill read count",
    ["skill_name"],
)

ERRORS = Counter(
    "buc_mcp_errors_total",
    "Error count",
    ["error_type"],
)


def register_health_routes(app, coding, kubernetes, context7=None):
    @app.get("/health/live")
    async def liveness() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/health/ready")
    async def readiness() -> JSONResponse:
        try:
            await coding.list_prompts()
            await kubernetes.list_prompts()
            if get_context7_api_key():
                await context7.list_tools()
            return JSONResponse({"status": "ready"})
        except Exception as e:
            return JSONResponse(
                {"status": "not ready", "error": str(e)},
                status_code=503,
            )


def register_metrics_route(app):
    @app.get("/metrics")
    async def metrics(request: Request) -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

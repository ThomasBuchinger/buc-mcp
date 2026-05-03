import logging
import os
import sys
import time

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger.json import JsonFormatter
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message


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

PROXY_REQUEST_COUNT = Counter(
    "buc_mcp_proxy_requests_total",
    "Total proxy requests forwarded to upstream",
    ["server", "status"],
)

PROXY_REQUEST_DURATION = Histogram(
    "buc_mcp_proxy_request_duration_seconds",
    "Proxy request latency in seconds",
    ["server"],
)

PROXY_ERRORS = Counter(
    "buc_mcp_proxy_errors_total",
    "Proxy error count",
    ["server", "error_type"],
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
            return JSONResponse({"status": "ready"})
        except Exception as e:
            return JSONResponse(
                {"status": "not ready", "error": str(e)},
                status_code=503,
            )

    @app.get("/health/context7/ready")
    async def context7_readiness() -> JSONResponse:
        if not get_context7_api_key():
            return JSONResponse({"status": "not configured"})
        if context7 is None:
            return JSONResponse({"status": "not configured"})
        try:
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


class ProxyMetricsMiddleware:
    def __init__(self, app: ASGIApp, server_name: str = "context7"):
        self.app = app
        self.server_name = server_name

    async def __call__(self, scope: dict, receive: callable, send: callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()
        status_code = None
        recorded = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, recorded
            await send(message)
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            elif message["type"] == "http.response.body" and not recorded:
                recorded = True
                duration = time.time() - start
                PROXY_REQUEST_COUNT.labels(
                    server=self.server_name, status=str(status_code or 0)
                ).inc()
                PROXY_REQUEST_DURATION.labels(server=self.server_name).observe(duration)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = time.time() - start
            PROXY_REQUEST_COUNT.labels(server=self.server_name, status="500").inc()
            PROXY_REQUEST_DURATION.labels(server=self.server_name).observe(duration)
            PROXY_ERRORS.labels(
                server=self.server_name, error_type=type(e).__name__
            ).inc()
            raise

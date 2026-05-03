import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.server import create_proxy
from fastmcp.server.providers import FileSystemProvider
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from fastmcp.utilities.lifespan import combine_lifespans

from src.metrics import (
    ProxyMetricsMiddleware,
    configure_logging,
    get_context7_api_key,
    register_health_routes,
    register_metrics_route,
)

configure_logging()
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent

# MCP Coding
coding = FastMCP("buc-coding")
coding.add_provider(FileSystemProvider(root=ROOT_DIR / "prompts" / "coding"))
coding.add_provider(
    SkillsDirectoryProvider(
        roots=ROOT_DIR / "skills" / "coding-passive",
        supporting_files="resources",
        reload=False,
    )
)
coding_app = coding.http_app(stateless_http=False)


# MCP kubernetes
kubernetes = FastMCP("buc-kubernetes")
kubernetes.add_provider(FileSystemProvider(root=ROOT_DIR / "prompts" / "kubernetes"))
kubernetes.add_provider(
    SkillsDirectoryProvider(
        roots=ROOT_DIR / "skills" / "kubernetes-passive",
        supporting_files="resources",
        reload=False,
    )
)
kubernetes_app = kubernetes.http_app(stateless_http=False)


# MCP SkillSync
syncSkill = FastMCP("buc-skills")
syncSkill.add_provider(
    SkillsDirectoryProvider(
        roots=ROOT_DIR / "skills" / "coding-passive",
        supporting_files="resources",
        reload=False,
    )
)
syncSkill.add_provider(
    SkillsDirectoryProvider(
        roots=ROOT_DIR / "skills" / "kubernetes-passive",
        supporting_files="resources",
        reload=False,
    )
)
syncSkill_app = syncSkill.http_app(stateless_http=False)


# MCP Context7 proxy
context7 = FastMCP("buc-context7")
if get_context7_api_key():
    try:
        upstream_url = os.environ.get(
            "CONTEXT7_MCP_URL", "https://mcp.context7.com/mcp"
        )
        proxy_server = create_proxy(
            Client(upstream_url, auth=BearerAuth(token=get_context7_api_key()))
        )
        context7.mount(proxy_server)
    except Exception as e:
        logger.error("Failed to create context7 proxy: %s", e)
        raise
context7_app = context7.http_app(stateless_http=False)


# FastAPI
app = FastAPI(lifespan=combine_lifespans(coding_app.lifespan, kubernetes_app.lifespan, syncSkill_app.lifespan, context7_app.lifespan))
app.add_middleware(ProxyMetricsMiddleware, server_name="context7")
app.mount("/buc-coding", coding_app)
app.mount("/buc-kubernetes", kubernetes_app)
app.mount("/buc-skills", syncSkill_app)

if get_context7_api_key():
    app.mount("/buc-context7", context7_app)

# Health + metrics on parent app
register_health_routes(app, coding, kubernetes, context7)
register_metrics_route(app)


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

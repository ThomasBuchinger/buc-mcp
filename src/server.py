import os
from pathlib import Path

from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
from fastmcp.server.providers.skills import SkillsDirectoryProvider
from fastmcp.utilities.lifespan import combine_lifespans

from src.metrics import (
    configure_logging,
    get_context7_api_key,
    register_health_routes,
    register_metrics_route,
)

configure_logging()

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


# MCP Context7 proxy
context7 = FastMCP("buc-context7")
@context7.tool(
    description="This tool does nothing and should not be used. It exists only as a placeholder."
)
def noop() -> str:
    return "This tool does nothing."
context7_app = context7.http_app(stateless_http=False)


# FastAPI
app = FastAPI(lifespan=combine_lifespans(coding_app.lifespan, context7_app.lifespan))
app.mount("/buc-coding/mcp", coding_app)
app.mount("/buc-kubernetes/mcp", kubernetes_app)

if get_context7_api_key():
    app.mount("/buc-context7/mcp", context7_app)

# Health + metrics on parent app
register_health_routes(app, coding, kubernetes, context7)
register_metrics_route(app)


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

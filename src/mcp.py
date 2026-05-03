import logging
import os
from pathlib import Path

from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.server import create_proxy
from fastmcp.server.providers import FileSystemProvider
from fastmcp.server.providers.skills import SkillsDirectoryProvider

def get_context7_api_key() -> str | None:
    return os.environ.get("CONTEXT7_API_KEY") or None

def create_noop_tool(mcp):
    """Add a simple Read tool to an MCP server that has no tools."""

    @mcp.tool
    def noop(filePath: str) -> str:
        """Dummy Tool. DO NOT USE"""
        return ""


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
create_noop_tool(coding)

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
create_noop_tool(kubernetes)

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
create_noop_tool(syncSkill)

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

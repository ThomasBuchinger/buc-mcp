from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
from fastmcp.server.providers.skills import SkillsDirectoryProvider

from src.metrics import configure_logging, register_health_routes, register_metrics_route

configure_logging()

ROOT_DIR = Path(__file__).resolve().parent.parent

mcp = FastMCP("buc-mcp")

mcp.add_provider(FileSystemProvider(root=ROOT_DIR / "prompts"))
mcp.add_provider(SkillsDirectoryProvider(
    roots=ROOT_DIR / "skills",
    supporting_files="resources",
    reload=False,
))

register_health_routes(mcp)
register_metrics_route(mcp)


@mcp.tool(description="This tool does nothing and should not be used. It exists only as a placeholder.")
def noop() -> str:
    return "This tool does nothing."

app = mcp.http_app(stateless_http=False)


def main():
    mcp.run(transport="http")


if __name__ == "__main__":
    main()

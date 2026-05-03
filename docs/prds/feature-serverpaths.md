# PRD: Server Path Refactor — Multi-Server URL Endpoints

## Summary

This PRD describes a refactoring of the BUC-MCP server architecture: replacing the single FastMCP instance serving one endpoint with a parent FastAPI app hosting multiple FastMCP instances on distinct URL paths. The existing `buc-mcp` server (prompts + skills) moves to `/buc-coding/mcp`. A new `buc-context7` server is created with a placeholder noop tool, mounted at `/buc-context7/mcp`. This refactor enables clients to choose which set of tools they need, and sets the foundation for mounting real upstream MCP proxies.

---

## Problem Statement

The current single-endpoint architecture forces all clients to connect to one URL and receive everything — prompts, skills, and any future proxied servers — in one namespace. This creates:
- No way for clients to request only Context7 tools without also getting local prompts/skills
- No isolation between feature domains
- Difficult to add new upstream servers without namespace collision concerns

A parent FastAPI app with multiple mounted MCP endpoints solves this by giving each server its own URL path and namespace identity.

---

## Goals

| Goal | Description |
|---|---|
| **Multiple URL endpoints** | Expose `/buc-coding/mcp` and `/buc-context7/mcp` under one host |
| **Isolation per server** | Each FastMCP instance has its own tools — no cross-contamination |
| **Preserve existing functionality** | All prompts, skills, health checks, and metrics continue working |
| **Minimal client impact** | Existing clients migrate by updating the URL path |

---

## Non-Goals

- Actual Context7 proxy implementation (covered in `feature-mcp-proxy.md`)
- Adding new tools beyond the placeholder noop in `buc-context7`
- Per-server authentication or rate limiting
- Multi-worker deployment changes
- CI/CD pipeline modifications

---

## Implementation Status

| Phase | Status | Notes |
|---|---|---|
| Phase 1 — `src/server.py` refactor | ✅ Done | 2026-05-03 |
| Phase 2 — `src/metrics.py` refactor | ⬜ Pending | Health/routes moved to FastAPI |
| Phase 3 — CLI entry point update | ✅ Done | Subsumed into Phase 1 (`uvicorn.run`) |

---

## Technical Approach

### Architecture

```
                    ┌─────────────────────────┐
                    │  FastAPI Parent App     │
                    │                         │
  Client ──────────►│  /buc-coding/mcp ───────┼──► FastMCP "buc-coding"
  picks endpoint    │     (prompts + skills)  │
  (coding or ctx)   │                         │
                    │  /buc-context7/mcp ─────┼──► FastMCP "buc-context7"
                    │     (noop placeholder)  │
                    │                         │
                    │  /health/live           │
                    │  /health/ready          │
                    │  /metrics               │
                    └─────────────────────────┘
```

### Core Code Structure

```python
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.utilities.lifespan import combine_lifespans

# Coding server: prompts + skills
coding = FastMCP("buc-coding")
coding.add_provider(FileSystemProvider(root=ROOT_DIR / "prompts"))
coding.add_provider(SkillsDirectoryProvider(roots=ROOT_DIR / "skills", ...))
coding_app = coding.http_app(path="/")

# Context7 server: placeholder
context7 = FastMCP("buc-context7")
@context7.tool(...)
def noop() -> str:
    return "This tool does nothing."
context7_app = context7.http_app(path="/")

# Parent app
app = FastAPI(lifespan=combine_lifespans(coding_app.lifespan, context7_app.lifespan))
app.mount("/buc-coding/mcp", coding_app)
app.mount("/buc-context7/mcp", context7_app)

# Health + metrics on parent app
register_health_routes(app)
register_metrics_route(app)
```

### Health Checks

Parent app's `/health/ready` returns overall pass/fail — checks both `coding.list_prompts()`, `coding.list_resources()`, and `context7.list_tools()`. Returns 503 if any check fails.

### Metrics

Same global counters — `endpoint` label naturally includes the mount path.

---

## Implementation Plan

### Phase 1 — Refactor `src/server.py`
- Split single `mcp` into `coding` + `context7` instances
- Create parent FastAPI app with `combine_lifespans`
- Mount both MCP apps under distinct paths

### Phase 2 — Refactor `src/metrics.py`
- Move `register_health_routes` to accept FastAPI app (not just FastMCP)
- Health/ready checks both instances
- Keep all metric names/labels unchanged

### Phase 3 — Update CLI Entry Point
- Replace `mcp.run(transport="http")` with `uvicorn.run(app, ...)`
- Dockerfile CMD stays the same: `uvicorn src.server:app`

### Phase 4 — Update Client Config
- Update `.agents/opencode.json` to use new URL paths

---

## Milestones

| # | Milestone | Description | Status |
|---|---|---|---|
| 1 | `src/server.py` refactored | Two FastMCP instances mounted under FastAPI parent on `/buc-coding/mcp` and `/buc-context7/mcp` | ✅ Done |
| 2 | `src/metrics.py` refactored | Health/metrics on parent app; readiness checks both servers | |
| 3 | CLI entry point updated | `main()` starts via uvicorn; Dockerfile CMD unchanged | ✅ Done |
| 4 | Health checks passing | `/health/live` and `/health/ready` return correct status | |
| 5 | Integration tests passing | Both endpoints serve MCP protocol, tools correctly namespaced | |
| 6 | Client configs updated | `.agents/opencode.json` uses new URL paths | |
| 7 | Documentation complete | `product-spec.md` updated with new architecture | |

---

## Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | Parent FastAPI with `app.mount()` | Standard FastAPI pattern; FastMCP docs show this approach |
| 2 | Lifespan via `combine_lifespans` | Required for proper startup/shutdown of mounted servers |
| 3 | `buc-coding` path for existing server | Semantic naming; distinguishes from context7 |
| 4 | `buc-context7` with noop placeholder | Establishes endpoint; noop removed/replaced with proxy later |
| 5 | Health/metrics on parent app only | Single scrape target; simpler |
| 6 | No path versioning | Internal service; version via server version |
| 7 | Health/ready: overall pass/fail | Simpler than per-server status; one boolean is sufficient |
| 8 | Proxy passes through upstream errors | No error transformation layer; context7 endpoint reflects upstream state |
| 9 | Phase 3 subsumed into Phase 1 | `main()` already updated to `uvicorn.run(app)` in server.py refactor |

---

## Dependencies

| Dependency | Status | Notes |
|---|---|---|
| FastMCP 3.x `http_app()` + `combine_lifespans` | Available | No new dependencies |
| FastAPI | ✅ Installed | Explicit dependency added |
| Existing infrastructure | Existing | Docker, K8s, CI unchanged |

---

## References

- [FastMCP FastAPI Integration docs](https://gofastmcp.com/integrations/fastapi)
- [FastMCP Custom Path docs](https://gofastmcp.com/deployment/http)
- [FastMCP Lifespan docs](https://gofastmcp.com/servers/lifespan)
- [FastMCP GitHub repo](https://github.com/PrefectHQ/fastmcp)

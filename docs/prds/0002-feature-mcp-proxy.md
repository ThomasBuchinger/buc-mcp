# PRD: MCP Proxy — Centralized Upstream MCP Server Proxy

## Summary

This PRD describes replacing the placeholder `buc-context7` server (mounted at `/buc-context7/mcp`) with a real upstream MCP proxy using FastMCP's `create_proxy()` primitive. The proxy centralizes API key management — upstream server credentials are stored server-side and clients access proxied tools/resources without needing individual API keys. Deployed as part of the existing multi-server buc-mcp service (parent FastAPI app hosting `buc-coding`, `buc-kubernetes`, and `buc-context7` on distinct URL paths).

---

## Problem Statement

MCP clients (OpenCode, Claude Code, etc.) that need access to upstream MCP servers like Context7 require individual API keys configured client-side. This creates operational friction:
- API keys must be distributed and rotated across every client
- Clients need separate configurations for each upstream server
- No centralized visibility into upstream server usage
- Key leakage risk when credentials live in client configurations

An in-process proxy solves these problems by hosting upstream servers server-side on their own FastMCP instance and URL path, centralizing credential management.

---

## Goals

| Goal | Description |
|---|---|
| **Centralize API keys** | Store upstream API keys as environment variables on the server; clients access proxied servers without credentials |
| **Dedicated endpoint for proxied tools** | Clients connect to `/buc-context7/mcp` to access proxied upstream tools; other endpoints remain separate |
| **Transparent proxying** | Proxied tools, resources, and prompts appear as native features of the `buc-context7` FastMCP instance |
| **Observability** | Track request metrics per upstream server and error rates |

---

## Non-Goals

- Per-server authentication (clients connecting to buc-mcp are on internal network)
- Rate limiting upstream server requests (handled upstream)
- Caching upstream tool responses
- Supporting non-HTTP upstream MCP transports (stdio, SSE)
- Per-client API key management for buc-mcp access
- Dynamic server addition (hot-plug new upstreams without restart)
- Multi-upstream proxy support (v1 targets single upstream: Context7)

---

## Technical Approach

### FastMCP Proxy Mechanism

FastMCP 3.x provides `create_proxy()` for connecting to upstream MCP servers. In the current multi-server architecture, the `buc-context7` FastMCP instance uses an authenticated `Client` with `BearerAuth` to forward requests to the upstream server:

```python
from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.server import create_proxy

# Context7 server: proxy to upstream
context7 = FastMCP("buc-context7")
upstream_url = os.environ.get("CONTEXT7_MCP_URL", "https://mcp.context7.com/mcp")
auth = BearerAuth(token=get_context7_api_key())
proxy_client = Client(upstream_url, auth=auth)
proxy_server = create_proxy(proxy_client)
context7.mount(proxy_server)

context7_app = context7.http_app(stateless_http=False)
```

The proxy is mounted on the parent FastAPI app at `/buc-context7/mcp` (conditional on `CONTEXT7_API_KEY` being set). Namespacing is handled by the URL path — no additional namespace parameter needed.

### Current Server Architecture

The proxy runs within the existing multi-server architecture:

```python
from fastapi import FastAPI
from fastmcp.utilities.lifespan import combine_lifespans

# Existing servers
coding = FastMCP("buc-coding")
# ... prompts + skills providers
coding_app = coding.http_app(stateless_http=False)

kubernetes = FastMCP("buc-kubernetes")
# ... prompts + skills providers
kubernetes_app = kubernetes.http_app(stateless_http=False)

# Context7 proxy server (to be implemented)
context7 = FastMCP("buc-context7")
context7_app = context7.http_app(stateless_http=False)

# Parent app
app = FastAPI(lifespan=combine_lifespans(coding_app.lifespan, kubernetes_app.lifespan, context7_app.lifespan))
app.mount("/buc-coding/mcp", coding_app)
app.mount("/buc-kubernetes/mcp", kubernetes_app)

if get_context7_api_key():
    app.mount("/buc-context7/mcp", context7_app)
```

### Configuration

Upstream server configured via environment variables:

| Variable | Purpose | Required |
|---|---|---|
| `CONTEXT7_API_KEY` | Bearer token for Context7 upstream | Yes |
| `CONTEXT7_MCP_URL` | Upstream MCP endpoint URL | No (default: `https://mcp.context7.com/mcp`) |

### Auth Pattern

Only Bearer token auth is supported in v1. The proxy adds `Authorization: Bearer <CONTEXT7_API_KEY>` header to all requests to the upstream server.

### Architecture

```
                    ┌─────────────────────────┐
                    │  FastAPI Parent App     │
                    │                         │
  Client ──────────►│  /buc-coding/mcp ───────┼──► FastMCP "buc-coding"
  picks endpoint    │     (prompts + skills)  │
  (coding/k8s/ctx)  │                         │
                    │  /buc-kubernetes/mcp ───┼──► FastMCP "buc-kubernetes"
                    │     (prompts + skills)  │
                    │                         │
                    │  /buc-context7/mcp ─────┼──► FastMCP "buc-context7"
                    │     │                    │
                    │     └──► ProxyClient ────┼──► mcp.context7.com
                    │                         │
                    │  /health/live           │
                    │  /health/ready          │
                    │  /metrics               │
                    └─────────────────────────┘
```

---

## Implementation Plan

### Phase 1 — Replace Noop with Proxy

Replace the placeholder noop tool in `buc-context7` with a real `create_proxy()` upstream connection in `src/server.py`:
- Remove noop tool from `buc-context7` FastMCP instance
- Create authenticated `Client` with `BearerAuth` using `CONTEXT7_API_KEY`
- Pass `Client` to `create_proxy()` (not raw URL)
- Mount proxy without namespace parameter — URL path handles namespacing
- Keep conditional mounting: only mount `/buc-context7/mcp` when API key is present
- Validate key is present at startup; fail fast if missing but endpoint configured

### Phase 2 — Health & Metrics for Proxies

Add observability for the proxied server:
- Parent app readiness (`/health/ready`) does NOT check proxy — proxy errors must not take down all endpoints
- Log proxy connection errors for observability
- Add dedicated `/health/context7/ready` endpoint that checks upstream connectivity by listing tools from upstream
- Prometheus metrics per upstream server (request counts, latency, errors)

### Phase 3 — Configuration & Deployment

Wire proxy configuration into deployment:
- Document proxy configuration in `docs/product-spec.md`
- Document expected `CONTEXT7_API_KEY` env var for users to patch via kustomize

### Phase 4 — Testing

Add test coverage for proxy functionality:
- Tests for `/health/context7/ready` endpoint returning correct status when proxy is configured vs absent
- Tests for proxy configuration parsing (env var handling)
- No integration tests for upstream proxying (requires API key; assumes FastMCP proxy works)

---

## Milestones

| # | Milestone | Description | Status |
|---|---|---|---|
| 1 | Proxy core implemented | `create_proxy` with authenticated `Client` replacing noop in `buc-context7` server.py; proxied tools accessible via `/buc-context7/mcp` | ✅ Done |
| 2 | Proxy health checks | Parent `/health/ready` unchanged; new `/health/context7/ready` checks upstream; proxy errors logged | ✅ Done |
| 3 | Proxy metrics | Prometheus metrics for Context7 proxy (request counts, latency, error rates) | ✅ Done |
| 4 | Tests passing | Tests for `/health/context7/ready` endpoint and env var configuration parsing | ✅ Done |
| 5 | Documentation complete | `docs/product-spec.md` updated with proxy architecture; `CONTEXT7_API_KEY` documented for kustomize patching | |

---

## Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | Separate `buc-context7` server for proxy | Consistent with multi-server architecture; clients can choose coding vs k8s vs context7 endpoints |
| 2 | Bearer token auth only | Context7 uses Bearer tokens; sufficient for v1 |
| 3 | Explicit error on upstream failure | Clients need to know the proxy is broken vs. silently having fewer tools |
| 4 | Single upstream URL (Context7 only) | Simplest v1; multi-upstream proxy added later if needed |
| 5 | No dynamic server addition | Not needed for initial rollout; adds unnecessary complexity |
| 6 | Pass through upstream errors | No transformation layer; upstream errors reach clients as-is |
| 7 | Conditional mounting (`if get_context7_api_key()`) | Graceful degradation — server starts even without API key; endpoint absent until key configured |
| 8 | Authenticated `Client` with `BearerAuth` for upstream | FastMCP `create_proxy` requires `Client` with auth, not raw URL |
| 9 | No namespace parameter on mount | URL path (`/buc-context7/mcp`) handles namespacing; no additional namespace needed |
| 10 | Parent `/health/ready` does NOT check proxy | Proxy errors must not take down all endpoints; separate `/health/context7/ready` endpoint |
| 11 | No integration tests for upstream proxying | Requires API key; assumes FastMCP proxy implementation works |
| 12 | No K8s deployment manifest changes | Users patch `CONTEXT7_API_KEY` via kustomize for greater flexibility |
| 13 | No `.agents/opencode.json` update | Manual redeployment needed before updating client configs |
| 14 | Proxy metrics via ASGI middleware (HTTP-level only) | Tool-level granularity requires JSON-RPC parsing; HTTP-level metrics simpler and sufficient for observability |

---

## Open Questions

| # | Question | Impact |
|---|---|---|
| 1 | Should the proxy forward roots, sampling, and elicitation from upstream? | FastMCP `ProxyClient` supports these; enables more advanced upstream features |

---

## Dependencies

| Dependency | Status | Notes |
|---|---|---|
| FastMCP 3.x `create_proxy` + `mount` | Available | Core primitive; `Client` with `BearerAuth` required |
| Parent FastAPI app with multi-server mounts | ✅ Implemented | `feature-serverpaths.md` — `combine_lifespans`, conditional mounting |
| `buc-context7` noop placeholder | ✅ Implemented | Replaced with proxy |
| Context7 MCP endpoint (`mcp.context7.com`) | External | Requires `CONTEXT7_API_KEY` env var |
| Existing buc-mcp server infrastructure | Existing | Reuses same Docker container, K8s deployment, observability |
| `/health/context7/ready` endpoint | ✅ Implemented | Checks upstream connectivity; does not affect parent readiness |
| Proxy metrics ASGI middleware | ✅ Implemented | HTTP-level request counts, latency, error rates at mount path |

---

## References

- [FastMCP Proxy Provider docs](https://gofastmcp.com/servers/providers/proxy)
- [FastMCP Composition / Mount docs](https://gofastmcp.com/servers/composition)
- [FastMCP ProxyClient docs](https://gofastmcp.com/python-sdk/fastmcp-server-providers-proxy)
- [FastMCP GitHub repo](https://github.com/PrefectHQ/fastmcp)

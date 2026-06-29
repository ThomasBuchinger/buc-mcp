# Implementation Plan: BUC-MCP FastMCP Server

## Summary

This plan describes how to build the BUC-MCP server: a centralized MCP server that exposes shared prompts and skills to Claude Code clients. Built with FastMCP 3.x, deployed as a Docker container on Kubernetes, served over Streamable HTTP.

---

## User Stories

1. As an MCP client, I want to connect to the buc-mcp server over Streamable HTTP at `/mcp`, so that I can interact with prompts and skills using the standard MCP protocol.
2. As an MCP client, I want to list available prompts via the MCP protocol, so that I can discover what prompts the server exposes.
3. As an MCP client, I want to read a specific prompt by name, so that I can retrieve its rendered content.
4. As an MCP client, I want to list available skills as resources, so that I can discover skill directories the server exposes.
5. As an MCP client, I want to read a skill's `SKILL.md` (e.g. `skill://traintimes/SKILL.md`), so that I can load the skill's instructions.
6. As a Kubernetes liveness probe, I want `GET /health/live` to return 200 when the process is alive, so that the probe can restart unhealthy pods.
7. As a Kubernetes readiness probe, I want `GET /health/ready` to return 200 only when providers are functional (prompts and resources can be listed), so that traffic is not routed to a server that isn't ready.
8. As an operator, I want a `GET /metrics` endpoint exposing Prometheus metrics, so that I can monitor request counts, latency, and errors.
9. As a developer, I want the `skills/` directory to be auto-discovered via `SkillsDirectoryProvider`, so that adding a new skill (a directory with `SKILL.md`) requires no code changes.
10. As a developer, I want the `prompts/` directory to be auto-discovered via `FileSystemProvider`, so that adding a new prompt file registers it automatically.
11. As a developer, I want a `main()` CLI entry point that runs the server with `transport="http"`, so that I can run the server locally for development.

---

## Phase 1 — Project Scaffolding

### 1.1 Python project setup

Create a standard Python project with `pyproject.toml` using modern packaging (e.g. Hatch or uv).

**Target Python version:** 3.14.

**Dependencies:** `fastmcp>=3.0.0`, `uvicorn[standard]`, `prometheus-client`, `python-json-logger`.

**Dev dependencies:** `pytest`, `anyio[trio]`, `httpx`.

### 1.2 Directory structure

Source code lives directly in `src/` — no nested package directory.

```
buc-mcp/
├── pyproject.toml
├── Dockerfile
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
├── src/
│   ├── __init__.py
│   ├── server.py              # FastMCP server entry point & ASGI app
│   ├── health.py              # Health check routes
│   └── metrics.py             # Prometheus metrics
├── prompts/                   # Prompt files (@prompt decorated Python files)
├── skills/                    # Skill directories (each with SKILL.md)
│   └── traintimes/
│       └── SKILL.md
├── tests/
│   ├── conftest.py
│   ├── test_server.py
│   └── test_health.py
└── docs/
    ├── product-spec.md
    └── feature-server.md
```

---

## Phase 2 — FastMCP Server Core

### 2.1 Server entry point (`src/server.py`)

Create the FastMCP server instance, wire up providers, and configure the HTTP transport.

**Key decisions:**

| Decision | Choice | Rationale |
|---|---|---|
| Transport | Streamable HTTP (ASGI app via `mcp.http_app()`) | Required by spec; supports K8s load balancing |
| Stateless mode | `stateless_http=True` | Enables horizontal scaling without session affinity |
| ASGI server | Uvicorn | Standard, production-grade, supports multiple workers |
| MCP endpoint path | `/mcp` (default) | Convention; no reason to customize |

**Implementation responsibilities:**

- Instantiate `FastMCP("buc-mcp")`
- Add a `SkillsDirectoryProvider` pointing at the repo's `skills/` directory with `supporting_files="resources"` and `reload=False`
- Add a `FileSystemProvider` pointing at the repo's `prompts/` directory
- Register health check and metrics custom routes (from `health.py` and `metrics.py`)
- Export an `app` object via `mcp.http_app(stateless_http=True)` for Uvicorn
- Provide a `main()` CLI entry point for local development using `mcp.run(transport="http")`

### 2.2 Prompts directory (`prompts/`)

Prompts are Python files using FastMCP's standalone `@prompt` decorator. The `FileSystemProvider` scans this directory and registers all decorated functions.

**Convention:** One prompt per file, filename matches the prompt name (snake_case).

### 2.3 Skills directory (`skills/`)

Skills use the existing directory convention. Each skill is a subdirectory containing a `SKILL.md` and optional supporting files. The `SkillsDirectoryProvider` automatically discovers them.

**Adding new skills:** Create a new directory under `skills/` with a `SKILL.md` file. No code changes required.

---

## Phase 3 — Docker & Kubernetes Deployment

### 3.1 Dockerfile

Multi-stage build using `python:3.14-slim` for a small production image.

**Key points:**
- Multi-stage build: builder stage installs dependencies, final stage copies only what's needed
- `prompts/` and `skills/` are baked into the image (content is versioned with the release)
- Uvicorn with 2 workers as the CMD; adjust via K8s resource limits
- Expose port 8000
- No secrets in the image (internal network trust model)
- Uvicorn runs the ASGI app as `src.server:app`

### 3.2 Kubernetes manifests

**`k8s/deployment.yaml`:**

- 2 replicas for availability
- Prometheus scrape annotations (`prometheus.io/scrape`, `/port`, `/path`) pointing at port 8000 and `/metrics`
- Liveness probe: `GET /health/live` on port 8000, initial delay 3s, period 10s
- Readiness probe: `GET /health/ready` on port 8000, initial delay 5s, period 10s
- Resource requests: 100m CPU / 128Mi memory; limits: 500m CPU / 256Mi memory

**`k8s/service.yaml`:**

- ClusterIP service, port 80 -> targetPort 8000
- `stateless_http=True` eliminates the need for sticky sessions

---

## Phase 4 — Observability

### 4.1 Health checks (`src/health.py`)

Two endpoints registered as custom routes on the FastMCP server via `@mcp.custom_route`:

| Endpoint | Purpose | K8s probe |
|---|---|---|
| `GET /health/live` | Process is alive | Liveness |
| `GET /health/ready` | Providers loaded, transport accepting connections | Readiness |

The readiness endpoint should call `mcp.list_prompts()` and `mcp.list_resources()` to verify providers are functional, returning 503 on failure.

### 4.2 Prometheus metrics (`src/metrics.py`)

Expose a `/metrics` endpoint using `prometheus_client`.

**Metrics to track:**

| Metric | Type | Labels | Description |
|---|---|---|---|
| `buc_mcp_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests |
| `buc_mcp_request_duration_seconds` | Histogram | `method`, `endpoint` | Request latency |
| `buc_mcp_prompt_reads_total` | Counter | `prompt_name` | Prompt read count |
| `buc_mcp_skill_reads_total` | Counter | `skill_name` | Skill read count |
| `buc_mcp_errors_total` | Counter | `error_type` | Error count |

### 4.3 Structured logging

Configure Python's `logging` module to emit JSON to stdout using `python-json-logger`. Call the logging configuration at server startup.

---

## Phase 5 — Testing

### 5.1 Test strategy

| Layer | What to test | Tool |
|---|---|---|
| Unit | Prompt functions return expected strings | pytest |
| Integration | FastMCP client can list/read prompts and skills | FastMCP `Client` (in-memory) |
| Health | `/health/live` and `/health/ready` return correct status | httpx / starlette TestClient |
| Container | Image builds and starts successfully | Docker + curl in CI |

Integration tests should use FastMCP's `Client` class against the `mcp` server instance directly (in-memory, no HTTP needed). Tests verify that prompts are listed, skills are discovered, and skill resources (e.g. `skill://traintimes/SKILL.md`) are readable.

---

## Phase 6 — CI/CD Pipeline

### 6.1 GitHub Actions workflow

Two jobs:
- **test**: Set up Python 3.14, install dev dependencies, run pytest
- **build** (depends on test): Build Docker image, push to registry on main branch merges

### 6.2 Release process

1. Merge PR to `main`
2. CI builds and pushes tagged container image (`$SHA` + `latest`)
3. Deploy to K8s (rolling update via image tag change)

No per-prompt versioning — the entire server is versioned as a unit per the spec.

---

## Implementation Order

| Step | Phase | Deliverable | Depends on |
|---|---|---|---|
| 1 | 1.1 | `pyproject.toml`, package skeleton in `src/` | — |
| 2 | 2.1 | `server.py` with FastMCP + providers wired up | Step 1 |
| 3 | 2.2 | At least one prompt in `prompts/` | Step 2 |
| 4 | 2.3 | Verify `skills/traintimes` is discovered | Step 2 |
| 5 | 4.1 | Health check endpoints | Step 2 |
| 6 | 4.2 | Prometheus `/metrics` endpoint | Step 2 |
| 7 | 4.3 | Structured JSON logging | Step 2 |
| 8 | 5 | Tests (unit + integration) | Steps 2-7 |
| 9 | 3.1 | Dockerfile | Steps 2-7 |
| 10 | 3.2 | K8s manifests | Step 9 |
| 11 | 6 | CI/CD pipeline | Steps 8-10 |

---

## Open Questions

| # | Question | Impact |
|---|---|---|
| 1 | Which container registry to push images to? | Dockerfile tags, CI config |
| 2 | Are there existing Prometheus/Grafana dashboards to integrate with? | Metric naming conventions |
| 3 | Should prompts be plain Markdown files or Python files with `@prompt` decorators? Plain Markdown is simpler but less flexible (no parameters). | Prompts directory convention |
| 4 | Is CORS middleware needed, or are all clients on the internal network? | Server middleware config |
| 5 | Desired replica count and resource limits for production? | K8s deployment spec |

---

## References

- [FastMCP Skills Provider docs](https://gofastmcp.com/servers/providers/skills)
- [FastMCP FileSystem Provider docs](https://gofastmcp.com/servers/providers/filesystem)
- [FastMCP HTTP Deployment docs](https://gofastmcp.com/deployment/http)
- [FastMCP GitHub repo](https://github.com/PrefectHQ/fastmcp)
- [FastMCP 3.0 announcement](https://jlowin.dev/blog/fastmcp-3)

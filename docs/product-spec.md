# BUC-MCP: Central Prompt & Skills Server

## Overview

BUC-MCP is a multi-server MCP endpoint platform built on FastAPI. It exposes shared Prompts and Skills for Coding and Kubernetes agents, plus proxied upstream MCP servers, through three URL paths: `/buc-coding/mcp` (prompts + skills), `/buc-kubernetes/mcp` (prompts + skills), and `/buc-context7/mcp` (Context7 tools). A parent FastAPI app hosts all three FastMCP instances on distinct URL paths, enabling clients to select which set of tools they need.

Built with FastMCP and deployed to Kubernetes, the server exposes prompts and skills through the MCP protocol's native Prompts primitive and the Skills feature (introduced in FastMCP 3.0.0). The Context7 proxy centralizes API key management — upstream server credentials are stored server-side and clients access proxied tools without individual API keys.

## Goals

- **Centralize prompt management** — One repo, one server, one place to find and share prompts.
- **Prompts as code** — Prompts and skills are files in the git repo, versioned and reviewed via PRs.
- **Selective tool enablement** — Clients point at a specific endpoint and receive only the relevant tools.
- **Extensible multi-server platform** — New MCP servers can be mounted on distinct paths under the same FastAPI host without namespace collision.
- **Centralized proxy credentials** — Upstream API keys stored server-side; clients access proxied tools without credentials.

## Non-Goals

- Per-prompt versioning or rollback (the MCP server is versioned as a whole via releases).
- Authentication or authorization at the MCP layer (internal network only).
- Serving non-Claude-Code MCP clients (may be supported later, not a design driver).
- Prompt analytics, usage tracking, or A/B testing.

## Architecture

```
                    ┌─────────────────────────────┐
                    │  FastAPI Parent App         │
                    │                             │
  Client ──────────►│  /buc-coding/mcp ───────────┼──► FastMCP "buc-coding"
  picks endpoint    │     (prompts + skills)      │
  (coding/k8s/ctx)  │                             │
                    │  /buc-kubernetes/mcp ───────┼──► FastMCP "buc-kubernetes"
                    │     (prompts + skills)      │
                    │                             │
                    │  /buc-context7/mcp ──────────┼──► FastMCP "buc-context7"
                    │     │                        │
                    │     └──► ProxyClient ────────┼──► mcp.context7.com
                    │                             │
                    │  /health/live               │
                    │  /health/ready              │
                    │  /health/context7/ready     │
                    │  /metrics                   │
                    └─────────────────────────────┘
```

### Components

| Component | Description |
|---|---|
| **FastAPI Parent App** | Hosts multiple FastMCP instances on distinct URL paths. |
| **FastMCP "buc-coding"** | Serves prompts (FilesystemProvider) and skills (SkillsDirectoryProvider) for coding agents. |
| **FastMCP "buc-kubernetes"** | Serves prompts (FilesystemProvider) and skills (SkillsDirectoryProvider) for kubernetes agents. |
| **FastMCP "buc-context7"** | Proxies Context7 upstream via `create_proxy()` with `BearerAuth` (mounted when `CONTEXT7_API_KEY` is set). |
| **Filesystem Provider** | FastMCP's built-in filesystem provider that loads prompts from local directories. |
| **Skills Directory Provider** | FastMCP's skills provider that loads skill bundles from local directories. |
| **ProxyClient** | Authenticated FastMCP client that forwards requests to upstream MCP server. |

## Content Model

- `prompts/NAME.md` — Markdown file containing the prompt
- `skills/NAME/SKILLS.md` — Standard Skills directory, containing the `SKILL.md` and additional resources (e.g. scripts)

## Deployment

| Aspect | Detail |
|---|---|
| **Runtime** | Python (latest stable) |
| **Framework** | FastAPI + FastMCP (latest) |
| **Container** | Docker image built from the repo |
| **Orchestration** | Kubernetes |
| **Auth** | None (internal network trust) |
| **Entry point** | `uvicorn src.server:app` |

## Release Strategy

The entire MCP server is versioned as a unit. Releases correspond to container image tags built from the main branch. There is no per-prompt versioning — the repo state at build time defines the content.

## Operational Requirements

### Health Checks

The server exposes health check endpoints for Kubernetes liveness and readiness probes:

| Endpoint | Description |
|---|---|
| `/health/live` | Always returns `{"status": "ok"}` (200) |
| `/health/ready` | Checks prompt/skill filesystem for coding and kubernetes servers; returns 503 if any check fails. Does NOT check proxy — proxy errors must not take down all endpoints. |
| `/health/context7/ready` | Dedicated proxy health check. Returns 200 with `{"status": "not configured"}` when `CONTEXT7_API_KEY` is absent. Returns 200 with `{"status": "ready"}` when upstream is reachable. Returns 503 with `{"status": "not ready"}` when upstream connection fails. |
| `/metrics` | Prometheus-compatible metrics endpoint |

The parent readiness probe (`/health/ready`) verifies that the coding and kubernetes servers' prompt/skill filesystems are loaded. Proxy errors are handled separately via `/health/context7/ready` to prevent them from affecting other endpoints.

### Monitoring

Monitoring is a core requirement. The server must expose:

- **Structured logging** — JSON logs to stdout for cluster log aggregation.
- **Metrics** — Prometheus-compatible metrics endpoint covering request counts, latency, error rates, and connected client count.
- **Proxy metrics** — Per-upstream-server metrics (request counts, latency, errors) tracked via ASGI middleware on the `/buc-context7/mcp` mount path.
- **Alerting hooks** — Metrics should be scrapable by existing cluster monitoring infrastructure.

### Client Configuration

Distribution of the MCP server endpoint to engineers is out of scope for this project. Clients connect to a specific endpoint path:

- `/buc-coding/mcp` — Prompts and skills (coding)
- `/buc-kubernetes/mcp` — Prompts and skills (kubernetes)
- `/buc-context7/mcp` — Context7 tools (requires `CONTEXT7_API_KEY` to be configured on the server)

## Context7 Proxy Configuration

The Context7 proxy server is conditionally mounted only when the `CONTEXT7_API_KEY` environment variable is present. The endpoint is absent from the server until the key is configured.

### Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `CONTEXT7_API_KEY` | Bearer token for Context7 upstream authentication | Yes (to mount proxy endpoint) |
| `CONTEXT7_MCP_URL` | Upstream MCP endpoint URL | No (default: `https://mcp.context7.com/mcp`) |

### Authentication Pattern

The proxy uses an authenticated `Client` with `BearerAuth` to forward requests to the upstream Context7 server. The `create_proxy()` primitive receives this client and handles MCP protocol forwarding transparently.

### Kubernetes Deployment

`CONTEXT7_API_KEY` should be injected via kustomize patch. Example:

```yaml
# kustomization.yaml
patches:
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: buc-mcp
      spec:
        template:
          spec:
            containers:
              - name: buc-mcp
                env:
                  - name: CONTEXT7_API_KEY
                    valueFrom:
                      secretKeyRef:
                        name: context7-api-key
                        key: api-key
```

Create the secret separately:

```bash
kubectl create secret generic context7-api-key --from-literal=api-key=<YOUR_KEY>
```

This approach provides flexibility — users can manage the secret lifecycle independently of the deployment manifests.

# BUC-MCP: Central Prompt & Skills Server

## Overview

BUC-MCP is a multi-server MCP endpoint platform built on FastAPI. It exposes shared Prompts and Skills for Coding-Agents through one of two URL paths: `/buc-coding/mcp` (prompts + skills) and `/buc-context7/mcp` (Context7 tools). A parent FastAPI app hosts both FastMCP instances on distinct URL paths, enabling clients to select which set of tools they need.

Built with FastMCP and deployed to Kubernetes, the server exposes prompts and skills through the MCP protocol's native Prompts primitive and the Skills feature (introduced in FastMCP 3.0.0).

## Goals

- **Centralize prompt management** — One repo, one server, one place to find and share prompts.
- **Prompts as code** — Prompts and skills are files in the git repo, versioned and reviewed via PRs.
- **Selective tool enablement** — Clients point at a specific endpoint and receive only the relevant tools — coding endpoints get prompts and skills; context7 endpoints get Context7 tools.
- **Extensible multi-server platform** — New MCP servers can be mounted on distinct paths under the same FastAPI host without namespace collision.

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
  (coding or ctx)   │                             │
                    │  /buc-context7/mcp ──────────┼──► FastMCP "buc-context7"
                    │     (Context7 tools)        │
                    │                             │
                    │  /health/live               │
                    │  /health/ready              │
                    │  /metrics                   │
                    └─────────────────────────────┘
```

### Components

| Component | Description |
|---|---|
| **FastAPI Parent App** | Hosts multiple FastMCP instances on distinct URL paths. |
| **FastMCP "buc-coding"** | Serves prompts (FilesystemProvider) and skills (SkillsDirectoryProvider). |
| **FastMCP "buc-context7"** | Serves Context7 tools (mounted when `CONTEXT7_API_KEY` is set). |
| **Filesystem Provider** | FastMCP's built-in filesystem provider that loads prompts from local directories. |
| **Skills Directory Provider** | FastMCP's skills provider that loads skill bundles from local directories. |

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
| `/health/ready` | Checks prompt/skill filesystem and Context7 tools (when mounted); returns 503 if any check fails |
| `/metrics` | Prometheus-compatible metrics endpoint |

The readiness probe verifies that the prompt/skill filesystem is loaded and the MCP transport is accepting connections. When `CONTEXT7_API_KEY` is set, it also verifies the context7 server is operational.

### Monitoring

Monitoring is a core requirement. The server must expose:

- **Structured logging** — JSON logs to stdout for cluster log aggregation.
- **Metrics** — Prometheus-compatible metrics endpoint covering request counts, latency, error rates, and connected client count.
- **Alerting hooks** — Metrics should be scrapable by existing cluster monitoring infrastructure.

### Client Configuration

Distribution of the MCP server endpoint to engineers is out of scope for this project. Clients connect to a specific endpoint path:

- `/buc-coding/mcp` — Prompts and skills
- `/buc-context7/mcp` — Context7 tools (requires `CONTEXT7_API_KEY` to be configured on the server)

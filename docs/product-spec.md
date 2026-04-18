# BUC-MCP: Central Prompt & Skills Server

## Overview

This MCP server hosts shared Prompts and Skills for Coding-Agents. It's a centrally maintained repository with useful resources 

Built with FastMCP and deployed to Kubernetes, the server exposes prompts and skills through the MCP protocol's native Prompts primitive and the Skills feature (introduced in FastMCP 3.0.0).

## Goals

- **Centralize prompt management** — One repo, one server, one place to find and share prompts.
- **Prompts as code** — Prompts and skills are files in the git repo, versioned and reviewed via PRs.
- **Zero client-side config burden** — Claude Code users point at one MCP server and get everything.
- **Selective tool enablement** — The server exposes all available tools; each client decides which tools to enable in their agent config.

## Non-Goals

- Per-prompt versioning or rollback (the MCP server is versioned as a whole via releases).
- Authentication or authorization at the MCP layer (internal network only).
- Serving non-Claude-Code MCP clients (may be supported later, not a design driver).
- Prompt analytics, usage tracking, or A/B testing.

## Architecture

```
+-------------------+       MCP (SSE/Streamable HTTP)       +-------------------+
|   Claude Code     | ------------------------------------> |    BUC-MCP        |
|   (MCP Client)    |                                       |    (FastMCP)      |
+-------------------+                                       +--------+----------+
                                                                     |
                                                              Filesystem Provider
                                                                     |
                                                            +--------+----------+
                                                            |  prompts/         |
                                                            |  skills/          |
                                                            |  (files in repo)  |
                                                            +-------------------+
```

### Components

| Component | Description |
|---|---|
| **FastMCP Server** | Python process exposing MCP Prompts and Skills via Streamable HTTP transport. |
| **Filesystem Provider** | FastMCP's built-in filesystem provider that loads prompts and skills from local directories. |
| **Prompts directory** | Directory of prompt files following FastMCP's prompt file conventions. |
| **Skills directory** | Directory of skill bundles (prompt + resources/scripts) following the experimental Skills spec. |


## Content Model

- `prompts/NAME.md` Markdown file containing the propmt
- `skills/NAME/SKILLS.md` Standaard Skills directory, containing the `SKILL.md` and additional resources (e.g. scripts) 



## Deployment

| Aspect | Detail |
|---|---|
| **Runtime** | Python (latest stable) |
| **Framework** | FastMCP (latest) |
| **Container** | Docker image built from the repo |
| **Orchestration** | Kubernetes |
| **Auth** | None (internal network trust) |


## Release Strategy

The entire MCP server is versioned as a unit. Releases correspond to container image tags built from the main branch. There is no per-prompt versioning — the repo state at build time defines the content.

## Operational Requirements

### Health Checks

The server exposes health check endpoints for Kubernetes liveness and readiness probes. The readiness probe should verify that the prompt/skill filesystem is loaded and the MCP transport is accepting connections.

### Monitoring

Monitoring is a core requirement. The server must expose:
- **Structured logging** — JSON logs to stdout for cluster log aggregation.
- **Metrics** — Prometheus-compatible metrics endpoint covering request counts, latency, error rates, and connected client count.
- **Alerting hooks** — Metrics should be scrapable by existing cluster monitoring infrastructure.

### Client Configuration

Distribution of the MCP server endpoint to engineers is out of scope for this project.


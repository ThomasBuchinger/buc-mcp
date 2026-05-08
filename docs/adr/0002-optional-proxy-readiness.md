# Optional Proxy Excluded from Readiness

Proxy MCP servers (e.g. `buc-context7`) are excluded from the parent `/health/ready` check. Local MCP servers (`buc-coding`, `buc-kubernetes`) are included. Only `/health/live` checks process liveness; `/health/ready` returns pass/fail for all local servers. Proxy health is checked separately via `/health/context7/ready`.

K8s readiness probe is `/health/ready`. With the proxy excluded, an upstream failure does not cause the pod to become unready — K8s keeps routing traffic but the endpoint returns an error. This is the correct behavior for optional endpoints: a broken upstream must not cascade and take down all MCP servers. The alternative — including proxy in readiness — would mean upstream failure brings down the entire pod, blocking clients that only need local servers.

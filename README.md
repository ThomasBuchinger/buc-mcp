# BUC-MCP

This is my collection of prompts/skills/tools related to AI agents.

AI Agents rely a lot on local client configuration. While most features are supported by most Agent-Harnesses they all assume stuff to be in different directories. This project aims be a Toolbox for AI Agent configuration:

- **Centralize Prompts/Skills**: Collect Prompts and Skills in a central place and provide them over the MCP protocol
- **Categorize**: Keep the Agent context focused, by providing use-case specific collection of Tools
- **Glue Code**: Skills over MCP are not well supported by clients yet. Therefore "invokeable Skills" are exposed as prompts
- **Configuration Mangement**: 

| MCP Endpoint          | Description |
|-----------------------|-------------|
| `/buc-coding/mcp`     | Prompts and Skills for writing feature-specs |
| `/buc-kubernetes/mcp` | Skills for troubleshooting and handling Kubernetes Manifests (DevOps focused) |
| `/buc-context7/mcp`   | proxy to `https://mcp.context7.com/mcp`, because envoy has problems with their HTTPS-Cert |
| `/buc-skills/mcp`     | Skills over MCP isn't well supported by clients yet. This MCP exposes skills to be downloaded into the clients skills/ directory|

Configuration Management Scripts

| Script       | Description |
| -------------|-------------|
| `/skills.sh` | (Not Implemented yet) Sync Skills into the skills directory |
| `/models.sh` | (Not Implemented yet) Configure available models |


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
                    │  /buc-context7/mcp ─────────┼──► FastMCP "buc-context7"
                    │     │                       │
                    │     └──► ProxyClient ───────┼──► mcp.context7.com
                    │                             │
                    │  /health/live               │
                    │  /health/ready              │
                    │  /health/context7/ready     │
                    │  /metrics                   │
                    └─────────────────────────────┘
```

### Kubernetes Deployment

Deploy the MCP server via Kustomize. You will need to set the Container image to the correct release

```yaml
resources:
- https://github.com/thomasbuchinger/buc-mcp/k8s?timeout=120&ref=main
- buc-mcp.yaml

images:
- name:  ghcr.io/thomasbuchinger/buc-mcp
  newTag: v0.5.0
```

To use the Context7 Proxy, you need to inject the `CONTEXT7_API_KEY` Environment variable in you kustomize Deployment.

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
                        name: buc-mcp-secrets
                        key: context7
```

```bash
# Secret template
kubectl create secret generic buc-mcp-secrets --from-literal=context7=YOUR_KEY --dry-run client -o yaml
```
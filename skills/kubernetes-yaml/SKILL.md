---
name: kubernetes-yaml
description: >-
  Generate production-ready Kubernetes manifests following best practices for security,
  reliability, and observability. Use this skill any time the user asks to create, write,
  or generate Kubernetes YAML. Also trigger when the user asks to "harden" or "review" an existing manifest. Always use this skill for any Kubernetes YAML generation task, even simple ones, because
  production-quality manifests require many non-obvious defaults that this skill captures.

---

# Kubernetes Manifest Skill

Generates production-ready Kubernetes manifests with security hardening, resource management,
health checks, and operational best practices baked in by default.

## Workflow

1. **Check existing Configuration**: Check if the repo already has kubernetes resources. Check which 3rd Party projects are already used and re-use them if it makes sense. Also check if the existing resources use any customer-specific labels (e.g. which team owns resources, internal accounting)
2. **Identify resources needed**: infer from the context which resources are needed. Pay attention which additional resources are needed.
3. **Ask clarifying questions only when necessary**: infer sensible defaults for language/runtime, replicas, resource sizes, and ports; ask only for things you cannot infer (e.g. external DB hostnames, TLS cert names, domain names for Ingress)
4. **Check reference files** Check @kubernetes-yaml/resources/KIND-ref.yaml file as your starting point. Comments are a hints, do not copy the comments
5. **Use Kustomize**: Always generate a `kustomization.yaml` so the user can selective include/exclude resources (e.g. NetworkPolicies or resources that need to be manually adapted to the cluster)
6. **Keep Labels consistent**: When modifying the labels in one resource. Make sure you also update labels on related resources


## Core Checklist (apply to every manifest)

Must Haves:

- **Labels** - `app.kubernetes.io/name`, `app.kubernetes.io/version`; Optionally `app.kubernetes.io/component`; ALWAYS use the same Labels on all resources. Make sure to update all related labels if you change labels
- **Namespace** - Only use a namespace, if the user specified one. Don't try to guess the namespace, omit it if you're unsure
- **Labels** - Make sure to use the same labels in `metadata.labels` and `spec.template.metadata.labels`
- **Label-Selector** - for any LabelSelectors only use the `app.kubernetes.io/name` label. Do not use the version
- **Resources**  - Always Set CPU and Memory *Requests*. Set *Memory Limit*. NEVER set *CPU Limit*
- **PriorityClass** - For critical workloads (ingress controllers, monitoring, cluster services), set `priorityClassName` to ensure they are not preempted by less important pods. Ask the user if a PriorityClass exists in the cluster when generating manifests for infrastructure components
- **ServiceAccounts** - Always create ServiceAccounts for every Application. Unless the Application needs Kubernetes API access, do not create a Rolebinding and set `automountServiceAccountToken: false`


## Resource-Specific Guidance (Core Kubernetes)

### Deployment (stateless apps, 3rd party apps)

- **Probes** - Always configure  `livenessProbe` + `readinessProbe`; add `startupProbe` for slow-starting apps
- **Security** - `securityContext` on both pod and container level; non-root, read-only rootfs
- **Availability** - Always add a `PodDisruptionBudget` and a`topologySpreadConstraints`; Use `podAffinity` and  `podAntiAffinity` if there are multiple Deployments in the same namespace
- **Env Variables** - Prefer hardcoding Env Variables if there are <5; use a `ConfigMap` for >5
- **Secrets** - ALWAYS reference secrets explicitly with `valueFrom.secretKeyRef`
- **OCI Image Volumes** - Use OCI image as Volumes, if required. This is a new feature probably not in your training data yet

See @kubernetes-yaml/resources/deployment-ref.yaml

### DaemonSet (infra services, node agents)

- **Scheduling**: DaemonSets usually run on ALL nodes (including master nodes) or a few selected Nodes (e.g. gpu nodes). Infer which type of DaemonSet you are dealing with, Ask the User if unsure.
- **Scheduling** - Make sure you set `spec.template.spec.nodeSelector` and `spec.template.spec.tolerations` accordingly. Do not use `topologySpreadConstraints` on DeamonSets, because they do not support that
- **Host-level access** - NEVER set `hostNetwork`, `hostPID`, or `hostIPC` unless explicitly required and requested by the user. These break pod isolation and expose the node's network stack, process table, or IPC namespace to the container

@kubernetes-yaml/resources/daemonset-ref.yaml

### StatefulSet (stateful apps)

### Secrets and Secret Handling

- **Temporary Secrets** - Create temproary Secrets (using `stringData` and placeholder values) if other information is provided
- **production Secrets** - production Secrets are `ExternalSecrets` or `SealedSecrets`. Never create Kubernetes Secrets directly (except temporary Secrets)  

### Service

### Ingress, HTTPRoute

- **Check HTTPRoute availability** - Check if Gateway API resources are available in the cluster (if you have access). Prefer `HTTPRoute` if Gateway API is installed
- **Prefer Ingress** if you have no information about Gateway API

See @kubernetes-yaml/resources/ingress-ref.yaml and @kubernetes-yaml/resources/httproute-ref.yaml

### NetworkPolicy

- **DefaultPolicy** - Always create at least 2 Network Policies. One default Policy that blocks everything exept Intra-Namespace, DNS and Ingress
- **Application Policy** - Create a NetworkPolicy for every Application, that defines what this Application is allowed to access
- **Prefer Namespace-to-Namespace-Rules** - When creating NetworkPolicies always scope the rules as Namespace-to-Namespace. This makes it easier to reason about the NetworkPolicies behaviour 

See @kubernetes-yaml/resources/networkpolicy-ref.yaml

### ServiceAccount, Role, ClusterRole, RoleBinding, ClusterRoleBinding

### CronJob

- **Base Images**: for Jobs that mostly run Bash-Scripts or kubectl commands, use `docker.io/alpine/k8s` as the container image. Look up a recent version before using the image

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: <app>-job
  namespace: <ns>
spec:
  schedule: "0 * * * *"
  concurrencyPolicy: Forbid              # prevent overlapping runs
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 3
      template:
        spec:
          restartPolicy: OnFailure
          serviceAccountName: <app>
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
          containers:
            - name: job
              image: <registry>/<app>:<tag>
              resources:
                requests:
                  cpu: "100m"
                  memory: "128Mi"
                limits:
                  memory: "256Mi"
              securityContext:
                allowPrivilegeEscalation: false
                readOnlyRootFilesystem: true
                capabilities:
                  drop: ["ALL"]
              volumeMounts:
              - name: tmp
                mountPath: /tmp
          volumes:
          - name: tmp
            emptyDir: {}
```

## Additional Components

### ExternalSecret


```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: <app>-secrets
  namespace: <ns>
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: cluster-secret-store
    kind: ClusterSecretStore
  target:
    name: <app>-secrets
  data:
    - secretKey: db-password
      remoteRef:
        key: /prod/<app>/db-password
```

### Certificate

### Helm

### Kustomize

### Gitops: ArgoCD / FluxCD

### Cilium NetworkPolicies

### ServiceMonitor

### CloudNativePG: Cluster

### Dex

### Istio

### Kube-vip

### MetalLB

### OAuth2Proxy

## Advanced techniques - only use if needed

This section contains advanced techniques that can be very useful if you need them, but you should not use them unless there is a good reason.

### Replace init-script

With this technique you can configure an application before it starts.

- Create a ConfigMap containing a script that copies a configuration-file template from the ConfigMap 

Example: 
```yaml
kind: ConfigMap
metadata:
  name: <app>-scripts
data:
  config.yaml.template: |-
    apiKey: INSERT_API_KEY
    log-level: info
  custom-entrypoint.sh: |-
    cp /scripts/config.yaml.template /etc/app/config.yaml
    sed -i 's/INSERT_API_KEY/$API_KEY/'

    exec /app/entrypoint.sh

# Deployment
spec:
  template:
    spec:
      containers:
        - name: ""
          command:
            - "/scripts/custom-entrypoint.sh"
```

### StartupProbe for initial configuration

With this technique you can configure an application via it's own API after the container starts. 

- Create a ConfigMap with a script that checks at the application has started
- Configure the application via the Script (prefer curl commands the the application API, use cli-commands if there is no other option)
- Run the Script in `startupProbe.exec.command` 

Example: 
```yaml
kind: ConfigMap
metadata:
  name: <app>-scripts
data:
  configure.sh: |-
    set -e 
    curl --fail http://127.0.0.1:8080/healthz
    curl -X POST http://127.0.0.1:8080/api/ --data DATA

# Deployment
spec:
  template:
    spec:
      containers:
        - name: ""
          startupProbe:
            exec:
              command:
                - "/scripts/configure.sh"
            initialDelaySeconds: 0
            periodSeconds: 15
            timeoutSeconds: 10
```
### CronJob for initial configuration

### Init-Container file copy

---

## Output Format

- Group related resource into a file. Do not create a new file for every resource.
- Output multiple resources into a single file per group, as a single multi-document YAML file separated by `---`
- No not output the comments from the reference files. They are hints for you, not output
- Mark placeholder values with a `# TODO: ...` comment. Print a summary which files contain placeholders at the end


| Group | Resources |
| --- | --- |
| app | Deployment, StatefulSet, DaemonSet, Service, PersistentVolume, PersistentVolumeClaim, ConfigMap, Secret, ... |
| network | Ingress, HTTPRoute, NetworkPolicy |
| rbac | Role, ClusterRole, Rolebinding, ClusterRolebinding, ServiceAccount |


## Image Tagging Policy

- **Development**: use semver tag (`v1.2.3`)
- **Production**: prefer digest pinning (`image@sha256:<hash>`) for immutability
- **Never** use `:latest`: it makes rollbacks and audits impossible


# calcaggregationprocessor

Helm chart for **calcaggregationprocessor** (java-ajsc) on AKS.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Uninstallation](#uninstallation)
- [Parameters](#parameters)
  - [Global](#global-parameters)
  - [Image](#image-parameters)
  - [Service Account](#service-account-parameters)
  - [Pod Security](#pod-security-parameters)
  - [Service](#service-parameters)
  - [Ingress](#ingress-parameters)
  - [Resources](#resource-parameters)
  - [Health Probes](#health-probe-parameters)
  - [Autoscaling](#autoscaling-parameters)
  - [Pod Disruption Budget](#pod-disruption-budget-parameters)
  - [Deployment Strategy](#deployment-strategy-parameters)
  - [Scheduling](#scheduling-parameters)
  - [Environment Variables](#environment-variable-parameters)
  - [Volumes](#volume-parameters)
  - [Network Policy](#network-policy-parameters)
  - [Monitoring](#monitoring-parameters)
  - [Java AJSC](#java-ajsc-parameters)
- [Environment Overrides](#environment-overrides)
- [Dependency Charts](#dependency-charts)
- [Examples](#examples)

---

## Prerequisites

- Helm 3.x
- Kubernetes 1.25+
- AKS cluster with appropriate node pools
- `kubectl` configured for target cluster
- Image pull secret `regcred` created in target namespace

---

## Installation

```bash
# Dev environment
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  -f ./calcaggregationprocessor/values-dev.yaml \
  -n com-att-attcc-dev-merge --create-namespace

# Prod environment
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  -f ./calcaggregationprocessor/values-prod.yaml \
  -n com-att-attcc-dev-merge

# With image tag override
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  -f ./calcaggregationprocessor/values-prod.yaml \
  --set image.tag=3.5.1 \
  -n com-att-attcc-dev-merge

# Dry run (validate without deploying)
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  -f ./calcaggregationprocessor/values-dev.yaml \
  -n com-att-attcc-dev-merge --dry-run --debug
```

## Uninstallation

```bash
helm uninstall calcaggregationprocessor -n com-att-attcc-dev-merge
```

---

## Parameters

### Global Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `replicaCount` | int | `1` | Number of pod replicas. Ignored when `autoscaling.enabled` is `true`. |
| `nameOverride` | string | `""` | Override the chart name in resource names. |
| `fullnameOverride` | string | `""` | Override the full resource name (skips release prefix). |
| `minReadySeconds` | int | `120` | Seconds a pod must be ready before considered available. |
| `revisionHistoryLimit` | int | `3` | Number of old ReplicaSets to retain for rollback. |

### Image Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image.repository` | string | `acr.azurecr.io/com-att-attcc-dev-merge/calcaggregationprocessor` | Docker image repository. |
| `image.tag` | string | `1.0.0` | Docker image tag. Falls back to `Chart.appVersion`. |
| `image.pullPolicy` | string | `IfNotPresent` | Pull policy: `Always`, `IfNotPresent`, `Never`. |
| `imagePullSecrets` | list | `[{name: regcred}]` | Secrets for private registry authentication. |

### Service Account Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serviceAccount.create` | bool | `true` | Create a ServiceAccount resource. |
| `serviceAccount.annotations` | map | `{}` | ServiceAccount annotations (e.g., Azure Workload Identity `azure.workload.identity/client-id`). |
| `serviceAccount.name` | string | `""` | Custom name. Defaults to chart fullname. |

### Pod Security Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `podAnnotations` | map | `{prometheus.io/scrape: "true", ...}` | Annotations on pods. |
| `podSecurityContext.runAsNonRoot` | bool | `true` | Enforce non-root execution. |
| `podSecurityContext.seccompProfile.type` | string | `RuntimeDefault` | Seccomp profile. |
| `securityContext.allowPrivilegeEscalation` | bool | `false` | Block privilege escalation. |
| `securityContext.readOnlyRootFilesystem` | bool | `false` | Read-only root filesystem. |
| `securityContext.runAsNonRoot` | bool | `true` | Non-root at container level. |
| `securityContext.capabilities.drop` | list | `["ALL"]` | Dropped Linux capabilities. |

### Service Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service.type` | string | `ClusterIP` | Service type: `ClusterIP`, `NodePort`, `LoadBalancer`. |
| `service.port` | int | `80` | Service port exposed to cluster. |
| `service.targetPort` | int | `8080` | Container port to forward to. |

### Ingress Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ingress.enabled` | bool | `false` | Enable Ingress resource. |
| `ingress.className` | string | `nginx` | Ingress class name. |
| `ingress.annotations` | map | `{kubernetes.io/ingress.class: nginx, ...}` | Controller annotations. |
| `ingress.hosts[].host` | string | `calcaggregationprocessor.example.com` | Hostname for routing. |
| `ingress.hosts[].paths[].path` | string | `/` | URL path. |
| `ingress.hosts[].paths[].pathType` | string | `Prefix` | Path matching type. |
| `ingress.tls` | list | `[]` | TLS config with `secretName` and `hosts`. |

### Resource Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `resources.requests.memory` | string | *(from Ansible)* | Memory request. |
| `resources.requests.cpu` | string | *(from Ansible)* | CPU request. |
| `resources.limits.memory` | string | *(from Ansible)* | Memory limit. |
| `resources.limits.cpu` | string | *(from Ansible)* | CPU limit. |

### Health Probe Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `livenessProbe.httpGet.path` | string | `/actuator/health` | Liveness endpoint. |
| `livenessProbe.httpGet.port` | int | `8080` | Liveness port. |
| `livenessProbe.httpGet.scheme` | string | `HTTP` | `HTTP` or `HTTPS`. |
| `livenessProbe.httpGet.httpHeaders` | list | `[{name: X-Custom-Header, value: Alive}]` | Custom headers. |
| `livenessProbe.initialDelaySeconds` | int | `120` | Delay before first check. |
| `livenessProbe.periodSeconds` | int | `30` | Interval between checks. |
| `livenessProbe.timeoutSeconds` | int | `30` | Timeout per check. |
| `readinessProbe.httpGet.path` | string | `/actuator/health` | Readiness endpoint. |
| `readinessProbe.httpGet.port` | int | `8080` | Readiness port. |
| `readinessProbe.httpGet.scheme` | string | `HTTP` | `HTTP` or `HTTPS`. |
| `readinessProbe.httpGet.httpHeaders` | list | `[{name: X-Custom-Header, value: Ready}]` | Custom headers. |
| `readinessProbe.initialDelaySeconds` | int | `110` | Delay before first check. |
| `readinessProbe.periodSeconds` | int | `30` | Interval between checks. |
| `readinessProbe.timeoutSeconds` | int | `30` | Timeout per check. |

### Autoscaling Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `autoscaling.enabled` | bool | `false` | Enable HPA. Overrides `replicaCount`. |
| `autoscaling.minReplicas` | int | `1` | Minimum replicas. |
| `autoscaling.maxReplicas` | int | `3` | Maximum replicas. |
| `autoscaling.targetCPUUtilizationPercentage` | int | `75` | CPU target for scaling. |
| `autoscaling.targetMemoryUtilizationPercentage` | int | `80` | Memory target for scaling. |

### Pod Disruption Budget Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pdb.enabled` | bool | `true` | Enable PodDisruptionBudget. |
| `pdb.minAvailable` | int | `1` | Min available pods during disruptions. |
| `pdb.maxUnavailable` | int | *(unset)* | Max unavailable (mutually exclusive with minAvailable). |

### Deployment Strategy Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deploymentStrategy.type` | string | `RollingUpdate` | `RollingUpdate` or `Recreate`. |
| `deploymentStrategy.rollingUpdate.maxUnavailable` | string | `50%` | Max unavailable during update. |
| `deploymentStrategy.rollingUpdate.maxSurge` | string | `50%` | Max surge during update. |

### Scheduling Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `nodeSelector` | map | `{}` | Node selector labels. |
| `tolerations` | list | `[]` | Pod tolerations. |
| `affinity` | map | *(nodeAffinity if configured)* | Affinity/anti-affinity rules. |

### Environment Variable Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `env` | list | *(from Ansible deployment.yaml)* | Plain-value env vars (`name`/`value` pairs). |
| `envOverrides` | list | *(per-environment)* | Env vars merged from `values-{env}.yaml`. |
| `envFromSecrets` | list | *(from Ansible deployment.yaml)* | Secret-sourced env vars grouped by `secretName`. |
| `envFromSecrets[].secretName` | string | | Kubernetes Secret name. |
| `envFromSecrets[].keys[].name` | string | | Env var name. |
| `envFromSecrets[].keys[].key` | string | | Key within the Secret. |

### Volume Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `volumes` | list | *(from Ansible deployment.yaml)* | Volume definitions (configMap or secret). |
| `volumes[].name` | string | | Volume name. |
| `volumes[].configMap.name` | string | | ConfigMap source name. |
| `volumes[].secret.secretName` | string | | Secret source name. |
| `volumes[].secret.optional` | bool | | Whether the Secret must exist. |
| `volumeMounts` | list | *(from Ansible deployment.yaml)* | Container mount points. |
| `volumeMounts[].name` | string | | Matching volume name. |
| `volumeMounts[].mountPath` | string | | Mount path in container. |
| `volumeMounts[].readOnly` | bool | `false` | Read-only mount. |
| `configFiles` | map | `{}` | Config file contents rendered into ConfigMap. |

### Network Policy Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `networkPolicy.enabled` | bool | `false` | Enable NetworkPolicy. |
| `networkPolicy.ingress` | list | *(namespace-scoped rule)* | Allowed ingress traffic rules. |

### Monitoring Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serviceMonitor.enabled` | bool | `false` | Enable Prometheus ServiceMonitor. |
| `serviceMonitor.interval` | string | `30s` | Scrape interval. |
| `serviceMonitor.path` | string | `/actuator/prometheus` | Metrics endpoint. |
| `serviceMonitor.port` | string | `http` | Port name to scrape. |

### Java AJSC Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `javaOpts` | string | *(from Ansible ajsc_args_map)* | Full JVM options string. |
| `springProfilesActive` | string | `default` | Spring Boot active profiles. |
| `managementPort` | int | `8080` | Actuator/management port. |
| `tomcat.maxThreads` | int | `200` | Tomcat connector max threads. |
| `tomcat.minSpareThreads` | int | `25` | Tomcat connector min spare threads. |

---

## Environment Overrides

Environment-specific values files override the base `values.yaml`. Generated environments: dev, perf, stage, uat, prod, dr.

Files: `values-dev.yaml`, `values-perf.yaml`, `values-stage.yaml`, `values-uat.yaml`, `values-prod.yaml`, `values-dr.yaml`.

Layer them using Helm's `-f` flag (later files take precedence):

```bash
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  -f ./calcaggregationprocessor/values-{environment}.yaml \
  -n com-att-attcc-dev-merge
```

### What Changes Per Environment

| Parameter | Dev | Prod |
|-----------|-----|------|
| `replicaCount` | 1 | 2 |
| `resources` | Dev sizing | Prod sizing |
| `autoscaling.enabled` | false | true |
| `ingress.enabled` | false | true |
| `envOverrides` | Dev routing/context vars | - |
| `affinity` | Dev nodepool | - |

---

## Dependency Charts

Enable with `--enable-dependency-chart` flag during conversion.

```bash
# Update dependencies
helm dependency update ./calcaggregationprocessor

# Install with dependency enabled
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  --set common-library.enabled=true \
  -n com-att-attcc-dev-merge
```

---

## Examples

### Override replicas and image tag

```bash
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  --set replicaCount=3 \
  --set image.tag=2.0.0 \
  -n com-att-attcc-dev-merge
```

### Enable ingress with TLS

```bash
helm upgrade --install calcaggregationprocessor ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=calcaggregationprocessor.prod.example.com \
  --set ingress.tls[0].secretName=prod-tls \
  --set ingress.tls[0].hosts[0]=calcaggregationprocessor.prod.example.com \
  -n com-att-attcc-dev-merge
```

### Template rendering (no deploy)

```bash
helm template my-release ./calcaggregationprocessor \
  -f ./calcaggregationprocessor/values.yaml \
  -f ./calcaggregationprocessor/values-dev.yaml
```

### Lint validation

```bash
helm lint ./calcaggregationprocessor/
```

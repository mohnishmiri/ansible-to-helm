# Ansible to Helm Chart Converter - Usage Guide

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Parameters Reference](#cli-parameters-reference)
- [Service Types](#service-types)
- [Input Directory Structure](#input-directory-structure)
- [Generated Helm Chart Structure](#generated-helm-chart-structure)
- [Values.yaml Parameter Reference](#valuesyaml-parameter-reference)
- [Environment-Specific Values](#environment-specific-values)
- [Dependency Chart Support](#dependency-chart-support)
- [Ansible Parsing Details](#ansible-parsing-details)
- [Helm Templates Reference](#helm-templates-reference)
- [AKS Deployment Standards](#aks-deployment-standards)
- [CI/CD Integration](#cicd-integration)
- [Extensibility Guide](#extensibility-guide)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

---

## Overview

The **Ansible to Helm Chart Converter** is a production-grade Python framework that reads existing Ansible playbooks, roles, and inventory configurations and generates standardized, production-ready Helm charts optimized for Azure Kubernetes Service (AKS).

### What It Does

1. **Parses** Ansible playbooks (`deploy.yml`), role defaults (`defaults/main.yml`), tasks (`tasks/main.yaml`), inventory group_vars, and existing Kubernetes templates from roles
2. **Extracts** deployment configurations: resources, probes, env vars, secrets, volumes, JVM args, node affinity, replica counts, and strategy settings
3. **Transforms** Ansible-specific patterns into Kubernetes-native Helm chart values
4. **Generates** a complete Helm chart directory with 11 template files, per-environment values overrides, Chart.yaml, and documentation

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                          │
│                        (convert.py)                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ConversionEngine                            │
│                     (core/engine.py)                            │
│                                                                 │
│  Step 1: Parse ──► Step 2: Transform ──► Step 3: Generate       │
└───────┬──────────────────────┬──────────────────────┬───────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐  ┌───────────────────┐  ┌───────────────────────┐
│   Parsers     │  │  Values Builder   │  │   Helm Generator      │
│               │  │                   │  │                       │
│ - Playbook    │  │ - values.yaml     │  │ - Chart.yaml          │
│ - Role        │  │ - values-dev.yaml │  │ - templates/          │
│ - Inventory   │  │ - values-prod.yaml│  │ - README.md           │
│ - K8s Template│  │ - ...             │  │                       │
└───────────────┘  └───────────────────┘  └───────────────────────┘
```

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.9+ | Runtime |
| pip | Latest | Package management |
| Helm | 3.x | Chart validation (`helm lint`) |
| kubectl | 1.25+ | Cluster deployment (optional) |
| Git | Any | Version control (optional) |

### Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyYAML | >= 6.0.1 | YAML parsing and generation |
| Jinja2 | >= 3.1.2 | Template variable resolution |
| click | >= 8.1.7 | CLI argument parsing |
| jsonschema | >= 4.17.3 | Schema validation |
| rich | >= 13.7.0 | Terminal output formatting |

---

## Installation

### Option 1: Direct Usage (Recommended)

```bash
cd ansible-to-helm
pip install -r requirements.txt
python convert.py --help
```

### Option 2: Install as Package

```bash
cd ansible-to-helm
pip install -e .
ansible-to-helm --help
```

### Option 3: Install with Dev Dependencies

```bash
cd ansible-to-helm
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Quick Start

### Minimal Example

```bash
python convert.py \
  --playbook-location ./playbook \
  --config-role-location ./configrole \
  --output-location ./helm-output \
  --service-name my-service \
  --service-type java-ajsc \
  --namespace my-namespace
```

### Full Example with All Options

```bash
python convert.py \
  --playbook-location ./ansible/playbooks \
  --config-role-location ./ansible/roles/my-config-role \
  --output-location ./helm-output \
  --service-name customer-ms \
  --service-type java-ajsc \
  --namespace customer \
  --enable-dependency-chart \
  --environment dev \
  --environment perf \
  --environment uat \
  --environment prod \
  --chart-version 2.1.0 \
  --app-version 3.5.0 \
  --dry-run
```

### Dry Run (Preview Without Writing)

```bash
python convert.py \
  --playbook-location ./playbook \
  --config-role-location ./configrole \
  --output-location ./helm-output \
  --service-name customer-ms \
  --service-type java-ajsc \
  --namespace customer \
  --dry-run
```

---

## CLI Parameters Reference

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `--playbook-location` | PATH (must exist) | Absolute or relative path to the directory containing Ansible playbooks (`deploy.yml`, `requirements.yml`, `inventory/`, `secrets/`). The converter reads the playbook to identify roles, and scans the `inventory/` subdirectory for environment-specific `group_vars`. |
| `--config-role-location` | PATH (must exist) | Absolute or relative path to the Ansible role directory. Must contain the standard role structure: `defaults/main.yml`, `tasks/main.yaml`, `templates/configs/`, and optionally `templates/k8s/`. |
| `--output-location` | PATH (created if absent) | Directory where the generated Helm chart will be written. A subdirectory named after `--service-name` is created inside this path. If the directory already exists, files are overwritten. |
| `--service-name` | STRING | Name of the microservice. Used as the Helm chart name, Kubernetes resource name prefix, and directory name. Must be a valid DNS label (lowercase, hyphens allowed, no underscores). Examples: `customer-ms`, `order-service`, `web-portal`. |
| `--service-type` | CHOICE | Type of microservice workload. Determines default health check paths, resource sizes, and JVM-specific settings. See [Service Types](#service-types) for details. Allowed values: `java-ajsc`, `nodejs`, `react`, `generic`. |
| `--namespace` | STRING | Kubernetes namespace for deployment. Used in generated values, ingress host patterns, image repository paths, network policy selectors, and Helm labels. Examples: `customer`, `order`, `platform`. |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--enable-dependency-chart` | FLAG | `false` | When set, adds a `dependencies` section to `Chart.yaml` with a reference to `common-library` chart. The dependency uses `condition: common-library.enabled` so it can be toggled per environment. Requires `helm dependency update` before install. |
| `--environment` | STRING (repeatable) | `dev`, `qa`, `prod` | Environments to generate `values-{env}.yaml` override files for. Can be specified multiple times. Each environment maps to Ansible inventory directories under `playbook-location/inventory/`. If a matching inventory directory exists, environment-specific variables (ROUTEOFFER, ENVCONTEXT, etc.) are extracted. |
| `--chart-version` | STRING | `1.0.0` | Semantic version for the Helm chart itself (written to `Chart.yaml` `version` field). Follow SemVer: increment major for breaking changes, minor for features, patch for fixes. |
| `--app-version` | STRING | `1.0.0` | Application version (written to `Chart.yaml` `appVersion` field and used as the default image tag in `values.yaml`). Typically matches your Docker image tag or release version. |
| `--dry-run` | FLAG | `false` | Preview mode. Runs the full parsing and transformation pipeline but does not write any files to disk. Useful for validating that the Ansible sources are parseable before generating output. |

### Parameter Details

#### `--playbook-location`

The converter expects this directory structure:

```
playbook-location/
├── deploy.yml              # Main playbook (parsed for role references)
├── requirements.yml        # Optional Ansible Galaxy requirements
├── inventory/
│   ├── dev/
│   │   ├── hosts           # Inventory hosts (not parsed for Helm)
│   │   └── group_vars/
│   │       └── all         # YAML file with env-specific variables
│   ├── perf/
│   │   └── group_vars/
│   │       └── all
│   ├── uat/
│   │   └── group_vars/
│   │       └── all
│   └── stage/
│       └── group_vars/
│           └── all
└── secrets/                # Secret files (referenced but not embedded)
    ├── keyfile
    └── truststore.jks
```

**What is parsed from each file:**

| File | Extracted Data |
|------|---------------|
| `deploy.yml` | Play name, hosts pattern, role references |
| `inventory/*/group_vars/all` | ROUTEOFFER, ENVCONTEXT, AFTENVIRONMENT, AFTLATITUDE, AFTLONGITUDE, CSI_CLUSTER, WMQ_ENVCONTEXT, GL_ENV, DEBUG_LEVEL, nodeAffinitykey, nodeAffinityvalue, probe timings, resource overrides |
| `secrets/` | Referenced in volume mounts; files are NOT embedded in Helm chart for security |

#### `--config-role-location`

The converter expects this directory structure:

```
config-role-location/
├── defaults/
│   └── main.yml            # Default variables (resources, probes, JVM args, replicas)
├── tasks/
│   └── main.yaml           # Task definitions (parsed for ConfigMap/Secret patterns)
├── meta/
│   └── main.yml            # Role metadata (optional)
└── templates/
    ├── configs/            # Application config files
    │   ├── application.properties
    │   ├── logback.xml
    │   ├── aft.properties
    │   ├── cadi.properties
    │   └── ...
    └── k8s/                # Existing K8s templates
        ├── deployment.yaml # Container ports, env vars, volumes, probes, affinity
        └── service.yaml    # Service ports, type
```

**What is parsed from each file:**

| File | Extracted Data |
|------|---------------|
| `defaults/main.yml` | `resource_map` (per-env CPU/memory), `ajsc_args_map` (per-env JVM args), `att_ms_replicas`, `k8s_imagepullpolicy`, `k8s_deployment_strategy`, `pod_maxUnavailable`, `pod_maxSurge`, `pod_minReadySeconds`, `pod_revisionHistoryLimit`, `k8s_readiness_*`, `k8s_liveness_*`, `server_health_port`, `server_tomcat_*` |
| `tasks/main.yaml` | ConfigMap creation patterns, Secret creation patterns, kubectl apply patterns |
| `templates/k8s/deployment.yaml` | `containerPort`, all `env` entries (plain values, secretKeyRef, fieldRef), `volumes`, `volumeMounts`, node affinity expressions, probe paths |
| `templates/k8s/service.yaml` | Service `port`, `targetPort`, `type` (NodePort/ClusterIP) |
| `templates/configs/*` | Config file names (available as `configFiles` map keys in values.yaml) |

#### `--service-type`

| Value | Health Path | Default Port | Extra Settings | Use Case |
|-------|-------------|-------------|----------------|----------|
| `java-ajsc` | `/actuator/health` | `8080` | `javaOpts`, `springProfilesActive`, `managementPort`, `tomcat.maxThreads`, `tomcat.minSpareThreads`, `JAVA_OPTS` / `JAVA_OPTS_OVERRIDE` env vars | Spring Boot AJSC microservices |
| `nodejs` | `/health` | `3000` | `nodeOptions` (e.g., `--max-old-space-size=2048`) | Express/Fastify Node.js services |
| `react` | `/` | `80` | Lightweight resources (128Mi/256Mi), no JVM settings | Nginx-served React/Vue/Angular SPAs |
| `generic` | `/health` | `8080` | No type-specific settings added | Custom workloads, Go, Python, etc. |

#### `--environment`

Repeatable flag. Each value creates a `values-{name}.yaml` file.

```bash
# Generate all 6 environment files (default)
--environment dev --environment perf --environment stage --environment uat --environment prod --environment dr

# Only dev and prod
--environment dev --environment prod

# Default if omitted
# Generates: values-dev.yaml, values-perf.yaml, values-stage.yaml, values-uat.yaml, values-prod.yaml, values-dr.yaml
```

**Environment-to-AKS Namespace mapping:**

The converter maps `--environment` values to Ansible inventory directories and AKS namespace keys:

| Environment | Inventory Dir | AKS Namespace | Default Replicas |
|-------------|---------------|---------------|-----------------|
| `dev` | `inventory/dev/` | `com-att-attcc-dev-merge` | 1 |
| `perf` | `inventory/perf/` | `com-att-attcc-new-perf` | 2 |
| `stage` | `inventory/stage/` | `com-att-attcc-preprod` | 2 |
| `uat` | `inventory/uat/` | `com-att-attcc-uat-merge` | 1 |
| `prod` | `inventory/prod/` | `com-att-attcc-prod` | 2 |
| `dr` | `inventory/dr/` | `com-att-attcc-dr` | 2 |

If no matching inventory directory exists, the environment file is still generated with default values.

---

## Service Types

### java-ajsc

Generates a Helm chart tuned for Java AJSC (Spring Boot) microservices:

- **JVM configuration**: `javaOpts` value extracted from `ajsc_args_map` per environment, injected via `JAVA_OPTS_OVERRIDE` / `JAVA_OPTS` env vars
- **Health probes**: `/actuator/health` on port 8080 with custom headers
- **Tomcat tuning**: `tomcat.maxThreads` and `tomcat.minSpareThreads` from `server_tomcat_*` variables
- **Management port**: `managementPort` from `server_health_port` (default 8080)
- **Spring profiles**: `springProfilesActive` placeholder for profile switching
- **Prometheus**: Annotations configured for `/actuator/prometheus` scraping

**Example values.yaml additions for java-ajsc:**

```yaml
javaOpts: "-Xms512m -Xmx2048m -XX:MetaspaceSize=256m ..."
springProfilesActive: "default"
managementPort: 8080
tomcat:
  maxThreads: 200
  minSpareThreads: 25
env:
  - name: JAVA_OPTS_OVERRIDE
    value: "-Xms512m -Xmx2048m ..."
  - name: JAVA_OPTS
    value: "$(JAVA_OPTS_OVERRIDE)"
```

### nodejs

Generates a Helm chart tuned for Node.js microservices:

- **Health probes**: `/health` instead of `/actuator/health`
- **Default port**: 3000
- **Node options**: `nodeOptions` value (e.g., `--max-old-space-size=2048`)

### react

Generates a Helm chart tuned for static frontend apps served by Nginx:

- **Health probes**: `/` (root path)
- **Default port**: 80
- **Lightweight resources**: 128Mi request / 256Mi limit memory, 100m request / 250m limit CPU

### generic

Generates a baseline Helm chart with no service-type-specific settings. Use this for Go, Python, Rust, or other workloads and customize the generated values.yaml manually.

---

## Input Directory Structure

### Complete Expected Input Layout

```
project-root/
├── playbook/                               # --playbook-location
│   ├── deploy.yml                          # Ansible playbook
│   ├── requirements.yml                    # Galaxy requirements (optional)
│   ├── inventory/
│   │   ├── dev/
│   │   │   ├── hosts                       # Inventory hosts
│   │   │   ├── group_vars/
│   │   │   │   └── all                     # Dev environment variables
│   │   │   └── host_vars/
│   │   │       └── hostname.example.com    # Host-specific vars (optional)
│   │   ├── perf/
│   │   │   └── group_vars/all
│   │   ├── uat/
│   │   │   └── group_vars/all
│   │   └── stage/
│   │       └── group_vars/all
│   └── secrets/
│       ├── keyfile
│       ├── truststore.jks
│       └── README.txt
│
└── configrole/                             # --config-role-location
    ├── defaults/
    │   └── main.yml                        # Default variables
    ├── tasks/
    │   └── main.yaml                       # Task definitions
    ├── meta/
    │   └── main.yml                        # Role metadata
    └── templates/
        ├── configs/
        │   ├── application.properties      # App config
        │   ├── logback.xml                 # Logging config
        │   ├── aft.properties              # AFT config
        │   ├── cadi.properties             # CADI config
        │   ├── spm2.properties             # SPM2 config
        │   ├── wmqLog.properties           # WMQ config
        │   └── errorMessages.properties    # Error messages
        └── k8s/
            ├── deployment.yaml             # K8s Deployment template
            └── service.yaml                # K8s Service template
```

---

## Generated Helm Chart Structure

```
output-location/
└── service-name/
    ├── Chart.yaml                  # Chart metadata, version, dependencies
    ├── values.yaml                 # Base values (all parameters)
    ├── values-dev.yaml             # Dev environment overrides
    ├── values-perf.yaml            # Perf environment overrides
    ├── values-uat.yaml             # UAT environment overrides
    ├── values-prod.yaml            # Production overrides (HPA, ingress enabled)
    ├── README.md                   # Auto-generated installation docs
    ├── charts/                     # Dependency charts directory (empty by default)
    └── templates/
        ├── _helpers.tpl            # Reusable template functions
        ├── deployment.yaml         # Deployment with rolling update, probes, volumes
        ├── service.yaml            # ClusterIP/NodePort service
        ├── configmap.yaml          # ConfigMap from configFiles map
        ├── secret.yaml             # Secret from secrets map
        ├── hpa.yaml                # HorizontalPodAutoscaler (conditional)
        ├── pdb.yaml                # PodDisruptionBudget (conditional)
        ├── ingress.yaml            # Ingress resource (conditional)
        ├── networkpolicy.yaml      # NetworkPolicy (conditional)
        ├── serviceaccount.yaml     # ServiceAccount (conditional)
        └── NOTES.txt               # Post-install instructions
```

---

## Values.yaml Parameter Reference

### Global Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `replicaCount` | int | `1` | Number of pod replicas. Ignored when `autoscaling.enabled` is `true`. |
| `nameOverride` | string | `""` | Override for the chart name used in resource names. |
| `fullnameOverride` | string | `""` | Override for the full resource name (skips release name prefix). |
| `minReadySeconds` | int | `120` | Seconds a pod must be ready before considered available. |
| `revisionHistoryLimit` | int | `3` | Number of old ReplicaSets to retain for rollback. |

### Image Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image.repository` | string | `acr.azurecr.io/{namespace}/{service-name}` | Docker image registry and repository path. |
| `image.tag` | string | `1.0.0` (from `--app-version`) | Docker image tag. Falls back to `Chart.appVersion`. |
| `image.pullPolicy` | string | `IfNotPresent` | Image pull policy. Values: `Always`, `IfNotPresent`, `Never`. |
| `imagePullSecrets` | list | `[{name: regcred}]` | List of Kubernetes secrets for private registry authentication. |

### Service Account

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serviceAccount.create` | bool | `true` | Whether to create a ServiceAccount resource. |
| `serviceAccount.annotations` | map | `{}` | Annotations for the ServiceAccount (e.g., Azure Workload Identity). |
| `serviceAccount.name` | string | `""` | Name override. Defaults to chart fullname if empty. |

### Pod Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `podAnnotations` | map | See below | Annotations applied to pods. |
| `podSecurityContext.runAsNonRoot` | bool | `true` | Enforce non-root container execution. |
| `podSecurityContext.seccompProfile.type` | string | `RuntimeDefault` | Seccomp profile type. |
| `securityContext.allowPrivilegeEscalation` | bool | `false` | Prevent privilege escalation in container. |
| `securityContext.readOnlyRootFilesystem` | bool | `false` | Mount root filesystem as read-only. |
| `securityContext.runAsNonRoot` | bool | `true` | Enforce non-root in container security context. |
| `securityContext.capabilities.drop` | list | `["ALL"]` | Linux capabilities to drop. |

**Default podAnnotations:**

```yaml
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/actuator/prometheus"
```

### Service

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service.type` | string | `ClusterIP` | Kubernetes service type. Values: `ClusterIP`, `NodePort`, `LoadBalancer`. |
| `service.port` | int | `80` | Service port exposed to the cluster. |
| `service.targetPort` | int | `8080` | Container port the service forwards traffic to. |

### Ingress

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ingress.enabled` | bool | `false` | Enable or disable the Ingress resource. |
| `ingress.className` | string | `nginx` | Ingress class name (for Kubernetes 1.18+). |
| `ingress.annotations` | map | See below | Ingress annotations for the controller. |
| `ingress.hosts` | list | See below | List of host rules. |
| `ingress.hosts[].host` | string | `{service-name}.example.com` | Hostname for the ingress rule. |
| `ingress.hosts[].paths` | list | `[{path: "/", pathType: "Prefix"}]` | Path rules for the host. |
| `ingress.tls` | list | `[]` | TLS configuration for HTTPS termination. |

**Default ingress annotations:**

```yaml
ingress:
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
```

**Example TLS configuration:**

```yaml
ingress:
  tls:
    - secretName: my-tls-secret
      hosts:
        - customer-ms.example.com
```

### Resources

| Parameter | Type | Default (dev) | Description |
|-----------|------|--------------|-------------|
| `resources.requests.memory` | string | `1Gi` | Memory request. Extracted from Ansible `resource_map`. |
| `resources.requests.cpu` | string | `512m` | CPU request. Extracted from Ansible `resource_map`. |
| `resources.limits.memory` | string | `2Gi` | Memory limit. Extracted from Ansible `resource_map`. |
| `resources.limits.cpu` | string | `1024m` | CPU limit. Extracted from Ansible `resource_map`. |

**How resources are mapped from Ansible:**

The converter reads `resource_map` from `defaults/main.yml`:

```yaml
# Ansible defaults/main.yml
resource_map:
  com-att-attcc-dev-merge:
    limits_memory:   "2Gi"
    requests_memory: "1Gi"
    limits_cpu:      "1024m"
    requests_cpu:    "512m"
  com-att-attcc-prod:
    limits_memory:   "4Gi"
    requests_memory: "2Gi"
    limits_cpu:      "1024m"
    requests_cpu:    "512m"
```

These are mapped to `values.yaml` (dev defaults) and `values-prod.yaml` (prod overrides).

### Health Probes

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `livenessProbe.httpGet.path` | string | `/actuator/health` | HTTP path for liveness check. |
| `livenessProbe.httpGet.port` | int | `8080` | Port for liveness check. |
| `livenessProbe.httpGet.scheme` | string | `HTTP` | Scheme (`HTTP` or `HTTPS`). |
| `livenessProbe.httpGet.httpHeaders` | list | `[{name: X-Custom-Header, value: Alive}]` | Custom HTTP headers. |
| `livenessProbe.initialDelaySeconds` | int | `120` | Seconds before first liveness check. |
| `livenessProbe.periodSeconds` | int | `30` | Seconds between liveness checks. |
| `livenessProbe.timeoutSeconds` | int | `30` | Seconds before liveness check times out. |
| `readinessProbe.httpGet.path` | string | `/actuator/health` | HTTP path for readiness check. |
| `readinessProbe.httpGet.port` | int | `8080` | Port for readiness check. |
| `readinessProbe.httpGet.scheme` | string | `HTTP` | Scheme (`HTTP` or `HTTPS`). |
| `readinessProbe.httpGet.httpHeaders` | list | `[{name: X-Custom-Header, value: Ready}]` | Custom HTTP headers. |
| `readinessProbe.initialDelaySeconds` | int | `110` | Seconds before first readiness check. |
| `readinessProbe.periodSeconds` | int | `30` | Seconds between readiness checks. |
| `readinessProbe.timeoutSeconds` | int | `30` | Seconds before readiness check times out. |

### Autoscaling (HPA)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `autoscaling.enabled` | bool | `false` | Enable HorizontalPodAutoscaler. When `true`, `replicaCount` is ignored. |
| `autoscaling.minReplicas` | int | `1` | Minimum number of replicas. |
| `autoscaling.maxReplicas` | int | `3` | Maximum number of replicas. |
| `autoscaling.targetCPUUtilizationPercentage` | int | `75` | Target CPU utilization for scaling. |
| `autoscaling.targetMemoryUtilizationPercentage` | int | `80` | Target memory utilization for scaling. |

### Pod Disruption Budget

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pdb.enabled` | bool | `true` | Enable PodDisruptionBudget. |
| `pdb.minAvailable` | int | `1` | Minimum pods that must be available during disruptions. |
| `pdb.maxUnavailable` | int | (unset) | Maximum pods that can be unavailable. Mutually exclusive with `minAvailable`. |

### Deployment Strategy

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deploymentStrategy.type` | string | `RollingUpdate` | Deployment strategy. Values: `RollingUpdate`, `Recreate`. |
| `deploymentStrategy.rollingUpdate.maxUnavailable` | string | `50%` | Max unavailable pods during rolling update. |
| `deploymentStrategy.rollingUpdate.maxSurge` | string | `50%` | Max surge pods during rolling update. |

### Scheduling

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `nodeSelector` | map | `{}` | Node selector labels for pod scheduling. |
| `tolerations` | list | `[]` | Pod tolerations for tainted nodes. |
| `affinity` | map | See below | Pod affinity/anti-affinity rules. |

**Default affinity (from Ansible nodeAffinitykey/nodeAffinityvalue):**

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: nodepool
              operator: In
              values:
                - default
```

### Environment Variables

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `env` | list | (extracted from deployment.yaml) | List of plain-value environment variables. |
| `envOverrides` | list | (per-environment) | Environment-specific variable overrides, merged at deploy time. |
| `envFromSecrets` | list | (extracted from deployment.yaml) | List of secret-sourced environment variables, grouped by secret name. |

**env format:**

```yaml
env:
  - name: ROUTEOFFER
    value: "D2A"
  - name: ENVCONTEXT
    value: "TEST"
  - name: DEBUG_LEVEL
    value: "INFO"
```

**envFromSecrets format:**

```yaml
envFromSecrets:
  - secretName: aaf-cred
    keys:
      - name: AAF_ID
        key: aaf_id
      - name: AAF_PASSWORD
        key: aaf_password
  - secretName: connectionmanagement
    keys:
      - name: attcc_db_url
        key: attcc_db_url
      - name: attcc_db_username
        key: attcc_db_username
      - name: attcc_db_password
        key: attcc_db_password
```

**envOverrides format (in values-dev.yaml):**

```yaml
envOverrides:
  - name: ROUTEOFFER
    value: "D2A"
  - name: ENVCONTEXT
    value: "TEST"
  - name: AFTENVIRONMENT
    value: "AFTUAT"
```

### Volumes and Volume Mounts

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `volumes` | list | (extracted) | Volume definitions. Supports ConfigMap and Secret sources. |
| `volumeMounts` | list | (extracted) | Container volume mount paths. |

**volumes format:**

```yaml
volumes:
  - name: config-volume
    configMap:
      name: '{{ include "fullname" . }}-config'
  - name: secret-volume
    secret:
      secretName: '{{ include "fullname" . }}-secret'
  - name: aaf-volume
    secret:
      secretName: aaf-cred
      optional: true
```

**volumeMounts format:**

```yaml
volumeMounts:
  - name: config-volume
    mountPath: /opt/att/ajsc/etc
  - name: secret-volume
    mountPath: /opt/att/ajsc/secret
  - name: aaf-volume
    mountPath: /opt/att/ajsc/aaf
```

### Config Files

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `configFiles` | map | `{}` | Key-value map of config file names to contents. Rendered into the ConfigMap. |

**Example:**

```yaml
configFiles:
  application.properties: |
    server.port=8080
    spring.profiles.active=dev
  logback.xml: |
    <configuration>...</configuration>
```

### Network Policy

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `networkPolicy.enabled` | bool | `false` | Enable NetworkPolicy resource. |
| `networkPolicy.ingress` | list | (namespace-scoped) | Ingress rules for allowed traffic. |

### Service Monitor (Prometheus)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serviceMonitor.enabled` | bool | `false` | Enable Prometheus ServiceMonitor. |
| `serviceMonitor.interval` | string | `30s` | Scrape interval. |
| `serviceMonitor.path` | string | `/actuator/prometheus` | Metrics endpoint path. |
| `serviceMonitor.port` | string | `http` | Port name to scrape. |

### Java AJSC-Specific Parameters

These are only present when `--service-type java-ajsc`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `javaOpts` | string | (extracted from ajsc_args_map) | Full JVM options string. Used as the value for `JAVA_OPTS_OVERRIDE`. |
| `springProfilesActive` | string | `default` | Spring Boot active profiles. |
| `managementPort` | int | `8080` | Spring Boot management/actuator port. |
| `tomcat.maxThreads` | int | `200` | Tomcat connector max threads. |
| `tomcat.minSpareThreads` | int | `25` | Tomcat connector min spare threads. |

---

## Environment-Specific Values

Each `--environment` generates a `values-{env}.yaml` file containing overrides for that environment. These files are designed to be layered on top of the base `values.yaml` using Helm's `-f` flag.

### What Gets Overridden Per Environment

| Parameter | Dev | Perf | UAT | Prod |
|-----------|-----|------|-----|------|
| `replicaCount` | 1 | 2 | 1 | 2 |
| `resources.requests.memory` | From resource_map | From resource_map | From resource_map | From resource_map |
| `resources.limits.memory` | From resource_map | From resource_map | From resource_map | From resource_map |
| `javaOpts` | Dev JVM args | Perf JVM args | UAT JVM args | Prod JVM args |
| `autoscaling.enabled` | - | - | - | `true` |
| `autoscaling.minReplicas` | - | - | - | `2` |
| `autoscaling.maxReplicas` | - | - | - | `6` |
| `pdb.enabled` | - | - | - | `true` |
| `ingress.enabled` | - | - | - | `true` |
| `envOverrides` | Dev vars | Perf vars | UAT vars | - |
| `affinity` | Dev nodepool | Perf nodepool | UAT nodepool | - |

### Deployment Command Per Environment

```bash
# Development
helm upgrade --install customer-ms ./customer-ms \
  -f ./customer-ms/values.yaml \
  -f ./customer-ms/values-dev.yaml \
  -n customer --create-namespace

# Performance
helm upgrade --install customer-ms ./customer-ms \
  -f ./customer-ms/values.yaml \
  -f ./customer-ms/values-perf.yaml \
  -n customer

# UAT
helm upgrade --install customer-ms ./customer-ms \
  -f ./customer-ms/values.yaml \
  -f ./customer-ms/values-uat.yaml \
  -n customer

# Production
helm upgrade --install customer-ms ./customer-ms \
  -f ./customer-ms/values.yaml \
  -f ./customer-ms/values-prod.yaml \
  -n customer
```

### Adding Custom Values at Deploy Time

```bash
# Override specific values via --set
helm upgrade --install customer-ms ./customer-ms \
  -f ./customer-ms/values.yaml \
  -f ./customer-ms/values-prod.yaml \
  --set replicaCount=4 \
  --set image.tag=3.5.1 \
  -n customer
```

---

## Dependency Chart Support

### Enabling Dependencies

```bash
python convert.py \
  --playbook-location ./playbook \
  --config-role-location ./configrole \
  --output-location ./helm-output \
  --service-name customer-ms \
  --service-type java-ajsc \
  --namespace customer \
  --enable-dependency-chart
```

### Generated Chart.yaml with Dependencies

```yaml
apiVersion: v2
name: customer-ms
dependencies:
  - name: common-library
    version: 1.0.0
    repository: "file://../common-library"
    condition: common-library.enabled
```

### Using Dependencies

```bash
# Update dependencies before install
helm dependency update ./customer-ms

# Install with dependency enabled
helm upgrade --install customer-ms ./customer-ms \
  --set common-library.enabled=true \
  -n customer
```

### Adding External Dependencies

Edit the generated `Chart.yaml` to add more dependencies:

```yaml
dependencies:
  - name: common-library
    version: 1.0.0
    repository: "file://../common-library"
    condition: common-library.enabled
  - name: redis
    version: 18.x.x
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
  - name: postgresql
    version: 13.x.x
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
```

---

## Ansible Parsing Details

### What the Converter Parses

| Ansible Source | Parsed Elements | Helm Target |
|---------------|----------------|-------------|
| `defaults/main.yml` `resource_map` | Per-environment CPU/memory limits and requests | `resources` in `values.yaml` and `values-{env}.yaml` |
| `defaults/main.yml` `ajsc_args_map` | Per-environment JVM args with heap/metaspace sizes | `javaOpts` in `values.yaml` and `values-{env}.yaml` |
| `defaults/main.yml` `att_ms_replicas` | Default replica count | `replicaCount` |
| `defaults/main.yml` `k8s_imagepullpolicy` | Image pull policy | `image.pullPolicy` |
| `defaults/main.yml` `k8s_deployment_strategy` | Deployment strategy type | `deploymentStrategy.type` |
| `defaults/main.yml` `pod_maxUnavailable` | Rolling update max unavailable | `deploymentStrategy.rollingUpdate.maxUnavailable` |
| `defaults/main.yml` `pod_maxSurge` | Rolling update max surge | `deploymentStrategy.rollingUpdate.maxSurge` |
| `defaults/main.yml` `pod_minReadySeconds` | Min ready seconds | `minReadySeconds` |
| `defaults/main.yml` `pod_revisionHistoryLimit` | Revision history limit | `revisionHistoryLimit` |
| `defaults/main.yml` `k8s_readiness_*` | Readiness probe timing | `readinessProbe.initialDelaySeconds`, etc. |
| `defaults/main.yml` `k8s_liveness_*` | Liveness probe timing | `livenessProbe.initialDelaySeconds`, etc. |
| `defaults/main.yml` `server_health_port` | Management port | `managementPort`, probe port |
| `defaults/main.yml` `server_tomcat_*` | Tomcat thread config | `tomcat.maxThreads`, `tomcat.minSpareThreads` |
| `templates/k8s/deployment.yaml` `env` | Plain env vars (`value:`) | `env` list in `values.yaml` |
| `templates/k8s/deployment.yaml` `env` | Secret-ref env vars (`valueFrom.secretKeyRef`) | `envFromSecrets` list in `values.yaml` |
| `templates/k8s/deployment.yaml` `env` | Field-ref env vars (`valueFrom.fieldRef`) | Hardcoded in `templates/deployment.yaml` |
| `templates/k8s/deployment.yaml` `volumes` | ConfigMap and Secret volumes | `volumes` list in `values.yaml` |
| `templates/k8s/deployment.yaml` `volumeMounts` | Container mount paths | `volumeMounts` list in `values.yaml` |
| `templates/k8s/deployment.yaml` `containerPort` | Container port | `service.targetPort` |
| `templates/k8s/deployment.yaml` affinity | Node affinity key/value | `affinity` in `values.yaml` |
| `templates/k8s/service.yaml` | Service port, targetPort, type | `service.port`, `service.targetPort`, `service.type` |
| `inventory/*/group_vars/all` | ROUTEOFFER, ENVCONTEXT, AFTENVIRONMENT, etc. | `envOverrides` in `values-{env}.yaml` |
| `inventory/*/group_vars/all` | nodeAffinitykey, nodeAffinityvalue | `affinity` in `values-{env}.yaml` |
| `templates/configs/*` | Config file names | Available as `configFiles` keys |

### Jinja2 Variable Resolution

Ansible templates use `{{ variable }}` syntax. The converter handles these as follows:

| Pattern | Resolution |
|---------|-----------|
| `{{dev_min_heap_size}}`, `{{prod_max_heap_size}}`, etc. | Resolved to actual values from `defaults/main.yml` |
| `{{non_proxy_hosts}}` | Resolved to `*.windows.net` from defaults |
| `{{ANS_msname}}`, `{{ANS_VERSION}}`, etc. | Mapped to Helm template variables or values.yaml entries |
| `{{ROUTEOFFER}}`, `{{ENVCONTEXT}}`, etc. | Moved to `envOverrides` in per-environment values |
| Unresolvable variables | Stripped (replaced with empty string) |

---

## Helm Templates Reference

### _helpers.tpl

Defines reusable template functions:

| Function | Output | Usage |
|----------|--------|-------|
| `name` | Chart name (truncated to 63 chars) | Resource name component |
| `fullname` | `{release}-{chart}` (truncated to 63 chars) | Primary resource name |
| `chart` | `{name}-{version}` | `helm.sh/chart` label |
| `labels` | Common labels block | All resources |
| `selectorLabels` | Selector labels block | Deployment selector, Service selector |
| `serviceAccountName` | ServiceAccount name | Deployment spec |

### deployment.yaml

Features:
- Conditional replicas (disabled when HPA is active)
- Rolling update strategy with configurable maxSurge/maxUnavailable
- Config checksum annotation for automatic pod restart on config changes
- Security context with non-root, capability drop
- Image pull secrets
- Node affinity, node selector, tolerations
- Dynamic env vars from values, envOverrides, and envFromSecrets
- Hardcoded fieldRef env vars (MS_NODE_NAME, MS_POD_NAME, MS_POD_NAMESPACE, MS_POD_IP, MS_POD_SERVICE_ACCOUNT)
- Volume mounts
- Liveness and readiness probes
- Resource limits and requests

### service.yaml

Standard ClusterIP service with configurable type, port, and targetPort.

### configmap.yaml

Iterates over `configFiles` map to create multi-file ConfigMap entries.

### secret.yaml

Iterates over `secrets` map with base64 encoding.

### hpa.yaml

Conditional HPA with CPU and memory utilization targets. Uses `autoscaling/v2` API.

### pdb.yaml

Conditional PDB with `minAvailable` or `maxUnavailable` (mutually exclusive).

### ingress.yaml

Conditional Ingress with className, annotations, hosts, paths, and TLS support.

### networkpolicy.yaml

Conditional NetworkPolicy with namespace-scoped ingress rules.

### serviceaccount.yaml

Conditional ServiceAccount with custom annotations (for Azure Workload Identity, etc.).

### NOTES.txt

Post-install instructions showing how to access the service based on service type (ClusterIP port-forward, NodePort, or Ingress URL).

---

## AKS Deployment Standards

The generated Helm charts follow these AKS best practices:

### Security

- `runAsNonRoot: true` enforced at pod and container level
- `seccompProfile: RuntimeDefault` enabled
- `allowPrivilegeEscalation: false` set
- All Linux capabilities dropped (`drop: ["ALL"]`)
- Secrets referenced via `secretKeyRef`, not embedded in ConfigMaps
- Image pull secrets configured for private ACR registries

### Reliability

- Liveness and readiness probes with configurable timing
- PodDisruptionBudget enabled by default (`minAvailable: 1`)
- Rolling update strategy with configurable surge/unavailable
- `minReadySeconds: 120` to prevent premature traffic routing
- Revision history limit for rollback capability

### Scalability

- HPA with CPU and memory targets (enabled in prod by default)
- Node affinity for nodepool-based scheduling
- Resource requests and limits for QoS guarantees

### Observability

- Prometheus scrape annotations on pods
- `/actuator/prometheus` metrics endpoint (java-ajsc)
- ServiceMonitor support for Prometheus Operator

### AKS-Specific

- Azure Ingress compatibility (nginx ingress class)
- Azure Key Vault integration placeholders via ServiceAccount annotations
- Azure Workload Identity compatibility via `serviceAccount.annotations`
- Network Policy support for namespace isolation
- ACR image repository path convention (`acr.azurecr.io/{namespace}/{service}`)

### Example: Azure Workload Identity

```yaml
serviceAccount:
  create: true
  annotations:
    azure.workload.identity/client-id: "00000000-0000-0000-0000-000000000000"
```

### Example: Azure Key Vault CSI Driver

```yaml
volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: "azure-keyvault"
volumeMounts:
  - name: secrets-store
    mountPath: /mnt/secrets
    readOnly: true
```

---

## CI/CD Integration

### GitHub Actions

The included `.github/workflows/ci.yml` runs:

1. **Unit tests** across Python 3.10, 3.11, 3.12
2. **Linting** with ruff and black
3. **Helm lint** on generated chart output

```bash
# Local validation matching CI
cd ansible-to-helm
python -m pytest tests/ -v --cov=src/converter
ruff check src/ tests/
black --check src/ tests/
```

### Azure DevOps

The included `azure-pipelines.yml` runs:

1. **Unit tests** with JUnit XML output
2. **Generate and lint** Helm chart

### Integrating into Your Pipeline

```yaml
# Example: generate and deploy in a pipeline step
steps:
  - name: Generate Helm Chart
    run: |
      python convert.py \
        --playbook-location ./playbook \
        --config-role-location ./configrole \
        --output-location ./helm-output \
        --service-name ${{ env.SERVICE_NAME }} \
        --service-type java-ajsc \
        --namespace ${{ env.NAMESPACE }} \
        --app-version ${{ env.BUILD_VERSION }} \
        --environment ${{ env.TARGET_ENV }}

  - name: Helm Lint
    run: helm lint ./helm-output/${{ env.SERVICE_NAME }}/

  - name: Helm Deploy
    run: |
      helm upgrade --install ${{ env.SERVICE_NAME }} \
        ./helm-output/${{ env.SERVICE_NAME }} \
        -f ./helm-output/${{ env.SERVICE_NAME }}/values.yaml \
        -f ./helm-output/${{ env.SERVICE_NAME }}/values-${{ env.TARGET_ENV }}.yaml \
        --set image.tag=${{ env.BUILD_VERSION }} \
        -n ${{ env.NAMESPACE }}
```

---

## Extensibility Guide

### Adding a New Service Type Plugin

1. Create a new file in `src/converter/plugins/`:

```python
# src/converter/plugins/golang.py
from converter.plugins.base_plugin import ServiceTypePlugin
from converter.core.models import ParsedAnsibleData

class GolangPlugin(ServiceTypePlugin):
    @property
    def service_type(self) -> str:
        return "golang"

    def customize_values(self, values: dict, parsed: ParsedAnsibleData) -> dict:
        values["livenessProbe"]["httpGet"]["path"] = "/healthz"
        values["readinessProbe"]["httpGet"]["path"] = "/readyz"
        values["resources"] = {
            "requests": {"memory": "64Mi", "cpu": "50m"},
            "limits": {"memory": "128Mi", "cpu": "200m"},
        }
        return values

    def default_health_path(self) -> str:
        return "/healthz"

    def default_port(self) -> int:
        return 8080
```

2. Add `"golang"` to the `click.Choice` in `cli.py`

3. Register the plugin in the engine (or use the `ParserRegistry`)

### Adding a New Parser

1. Extend `BaseParser`:

```python
from converter.parsers.base import BaseParser

class DockerComposeParser(BaseParser):
    def parse(self):
        data = self._load_yaml(self.path / "docker-compose.yml")
        # Extract ports, env, volumes...
        return extracted_data
```

2. Call it in `ConversionEngine._parse_ansible()`

### Adding a New Helm Template

1. Add a render method in `TemplateRenderer`
2. Add the file to `HelmChartGenerator._write_templates()`
3. Add corresponding values to `ValuesBuilder.build()`

---

## Security Considerations

### Secrets Handling

- The converter **never embeds secret values** in generated files
- Ansible secrets directory is referenced but not copied
- Secret env vars use `secretKeyRef` pointing to pre-existing Kubernetes secrets
- The `secrets` map in `values.yaml` is empty by default; populate at deploy time or via external secret managers

### Recommendations

- Use Azure Key Vault with CSI Secret Store Driver instead of Kubernetes Secrets
- Use Azure Workload Identity instead of static credentials
- Never commit `values-*.yaml` files containing actual secret values
- Use Helm `--set` or sealed-secrets for sensitive values in CI/CD
- Enable NetworkPolicy to restrict pod-to-pod traffic

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'click'` | Dependencies not installed | Run `pip install -r requirements.txt` |
| `Path does not exist` | Wrong `--playbook-location` or `--config-role-location` | Verify paths exist and contain expected files |
| Empty `env` list in values.yaml | No `env:` block in `templates/k8s/deployment.yaml` | Ensure the Ansible role has a K8s deployment template |
| Missing environment values file | No matching `inventory/{env}/group_vars/all` | File is still generated with defaults; add group_vars for overrides |
| `helm lint` errors | Template syntax issues | Check generated templates for valid Go template syntax |

### Validation Commands

```bash
# Validate the converter runs successfully
python convert.py --dry-run \
  --playbook-location ./playbook \
  --config-role-location ./configrole \
  --output-location ./helm-output \
  --service-name test-ms \
  --service-type java-ajsc \
  --namespace test

# Lint generated chart
helm lint ./helm-output/test-ms/

# Template rendering test (without deploying)
helm template test-release ./helm-output/test-ms/ \
  -f ./helm-output/test-ms/values.yaml \
  -f ./helm-output/test-ms/values-dev.yaml

# Run unit tests
python -m pytest tests/ -v
```

---

## Examples

### Example 1: Java AJSC Microservice

```bash
python convert.py \
  --playbook-location ./playbook \
  --config-role-location ./configrole \
  --output-location ./helm-output \
  --service-name customer-ms \
  --service-type java-ajsc \
  --namespace customer \
  --enable-dependency-chart \
  --environment dev \
  --environment perf \
  --environment uat \
  --environment prod \
  --chart-version 2.0.0 \
  --app-version 3.5.0
```

### Example 2: Node.js Microservice

```bash
python convert.py \
  --playbook-location ./ansible/playbooks \
  --config-role-location ./ansible/roles/order-service \
  --output-location ./helm-charts \
  --service-name order-service \
  --service-type nodejs \
  --namespace orders \
  --environment dev \
  --environment prod
```

### Example 3: React Frontend

```bash
python convert.py \
  --playbook-location ./ansible/playbooks \
  --config-role-location ./ansible/roles/web-portal \
  --output-location ./helm-charts \
  --service-name web-portal \
  --service-type react \
  --namespace frontend \
  --environment dev \
  --environment staging \
  --environment prod
```

### Example 4: Generic Service (Dry Run)

```bash
python convert.py \
  --playbook-location ./ansible/playbooks \
  --config-role-location ./ansible/roles/my-service \
  --output-location ./helm-charts \
  --service-name my-service \
  --service-type generic \
  --namespace platform \
  --dry-run
```

### Example 5: Batch Conversion (Multiple Services)

```bash
#!/bin/bash
SERVICES=("customer-ms" "order-ms" "billing-ms" "notification-ms")
TYPES=("java-ajsc" "java-ajsc" "nodejs" "nodejs")

for i in "${!SERVICES[@]}"; do
  python convert.py \
    --playbook-location "./ansible/playbooks" \
    --config-role-location "./ansible/roles/${SERVICES[$i]}-config" \
    --output-location "./helm-charts" \
    --service-name "${SERVICES[$i]}" \
    --service-type "${TYPES[$i]}" \
    --namespace "${SERVICES[$i]%%-*}" \
    --environment dev \
    --environment prod \
    --enable-dependency-chart
done
```

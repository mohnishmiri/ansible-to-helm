"""Renders Helm template files using best-practice patterns."""

from converter.core.config import ConverterConfig
from converter.core.models import ParsedAnsibleData


class TemplateRenderer:

    def render_helpers(self, config: ConverterConfig) -> str:
        return '''{{/*
Expand the name of the chart.
*/}}
{{- define "name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name.
*/}}
{{- define "fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label.
*/}}
{{- define "chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "labels" -}}
app: {{ .Values.appLabel | default (include "name" .) }}
version: {{ .Values.image.tag | default .Chart.AppVersion | quote }}
{{- if .Values.routeoffer }}
routeoffer: {{ .Values.routeoffer }}
{{- end }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "selectorLabels" -}}
app: {{ .Values.appLabel | default (include "name" .) }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
'''

    def render_deployment(self, config: ConverterConfig, parsed: ParsedAnsibleData) -> str:
        field_ref_envs = ""
        for ev in parsed.secret_env_vars:
            if ev.field_ref:
                field_ref_envs += (
                    '            - name: ' + ev.name + '\n'
                    '              valueFrom:\n'
                    '                fieldRef:\n'
                    '                  fieldPath: ' + ev.field_ref + '\n'
                )

        return '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "fullname" . }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  strategy:
    type: {{ .Values.deploymentStrategy.type }}
    {{- if eq .Values.deploymentStrategy.type "RollingUpdate" }}
    rollingUpdate:
      maxUnavailable: {{ .Values.deploymentStrategy.rollingUpdate.maxUnavailable }}
      maxSurge: {{ .Values.deploymentStrategy.rollingUpdate.maxSurge }}
    {{- end }}
  minReadySeconds: {{ .Values.minReadySeconds }}
  revisionHistoryLimit: {{ .Values.revisionHistoryLimit }}
  selector:
    matchLabels:
      {{- include "selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "serviceAccountName" . }}
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.podSecurityContext }}
      securityContext:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- if .Values.affinity }}
      affinity:
        {{- toYaml .Values.affinity | nindent 8 }}
      {{- end }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- if .Values.volumes }}
      volumes:
        {{- range .Values.volumes }}
        - name: {{ .name }}
          {{- if eq .type "configmap" }}
          configMap:
            {{- if .external }}
            name: {{ .sourceName }}
            {{- else }}
            name: {{ include "fullname" $ }}-{{ .sourceName }}
            {{- end }}
          {{- else if eq .type "secret" }}
          secret:
            {{- if .external }}
            secretName: {{ .sourceName }}
            {{- else }}
            secretName: {{ include "fullname" $ }}-{{ .sourceName }}
            {{- end }}
            {{- if .optional }}
            optional: {{ .optional }}
            {{- end }}
          {{- end }}
        {{- end }}
      {{- end }}
      containers:
        - name: {{ .Chart.Name }}
          {{- with .Values.securityContext }}
          securityContext:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
              protocol: TCP
          env:
            {{- range .Values.env }}
            - name: {{ .name }}
              value: {{ .value | quote }}
            {{- end }}
            {{- if .Values.envOverrides }}
            {{- range .Values.envOverrides }}
            - name: {{ .name }}
              value: {{ .value | quote }}
            {{- end }}
            {{- end }}
            {{- range .Values.envFromSecrets }}
            {{- $secretName := .secretName }}
            {{- range .keys }}
            - name: {{ .name }}
              valueFrom:
                secretKeyRef:
                  name: {{ $secretName }}
                  key: {{ .key }}
            {{- end }}
            {{- end }}
''' + field_ref_envs + '''          volumeMounts:
            {{- range .Values.volumeMounts }}
            - name: {{ .name }}
              mountPath: {{ .mountPath }}
              {{- if .readOnly }}
              readOnly: {{ .readOnly }}
              {{- end }}
            {{- end }}
          {{- with .Values.livenessProbe }}
          livenessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.readinessProbe }}
          readinessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
      restartPolicy: Always
'''

    def render_service(self, config: ConverterConfig, parsed: ParsedAnsibleData) -> str:
        return '''apiVersion: v1
kind: Service
metadata:
  name: {{ include "fullname" . }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
      protocol: TCP
      name: http
  selector:
    {{- include "selectorLabels" . | nindent 4 }}
'''

    def render_configmap(self, config: ConverterConfig, parsed: ParsedAnsibleData) -> str:
        return '''apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "fullname" . }}-config
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
data:
  {{- range $key, $value := .Values.configFiles }}
  {{ $key }}: |
    {{ $value | nindent 4 }}
  {{- end }}
'''

    def render_secret(self, config: ConverterConfig) -> str:
        return '''apiVersion: v1
kind: Secret
metadata:
  name: {{ include "fullname" . }}-secret
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
type: Opaque
data:
  {{- range $key, $value := .Values.secrets }}
  {{ $key }}: {{ $value | b64enc | quote }}
  {{- end }}
'''

    def render_hpa(self, config: ConverterConfig) -> str:
        return '''{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "fullname" . }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    {{- if .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    {{- end }}
    {{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
    {{- end }}
{{- end }}
'''

    def render_serviceaccount(self, config: ConverterConfig) -> str:
        return '''{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "serviceAccountName" . }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
'''

    def render_pdb(self, config: ConverterConfig) -> str:
        return '''{{- if .Values.pdb.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "fullname" . }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
spec:
  {{- if .Values.pdb.minAvailable }}
  minAvailable: {{ .Values.pdb.minAvailable }}
  {{- end }}
  {{- if .Values.pdb.maxUnavailable }}
  maxUnavailable: {{ .Values.pdb.maxUnavailable }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "selectorLabels" . | nindent 6 }}
{{- end }}
'''

    def render_ingress(self, config: ConverterConfig) -> str:
        return '''{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "fullname" . }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
'''

    def render_networkpolicy(self, config: ConverterConfig) -> str:
        return '''{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "fullname" . }}
  namespace: {{ .Values.namespace | default .Release.Namespace }}
  labels:
    {{- include "labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
  ingress:
    {{- toYaml .Values.networkPolicy.ingress | nindent 4 }}
{{- end }}
'''

    def render_notes(self, config: ConverterConfig) -> str:
        return '''1. Get the application URL by running these commands:
{{- if .Values.ingress.enabled }}
{{- range $host := .Values.ingress.hosts }}
  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ $host.host }}
{{- end }}
{{- else if contains "NodePort" .Values.service.type }}
  export NODE_PORT=$(kubectl get --namespace {{ .Values.namespace | default .Release.Namespace }} -o jsonpath="{.spec.ports[0].nodePort}" services {{ include "fullname" . }})
  export NODE_IP=$(kubectl get nodes --namespace {{ .Values.namespace | default .Release.Namespace }} -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "ClusterIP" .Values.service.type }}
  kubectl --namespace {{ .Values.namespace | default .Release.Namespace }} port-forward svc/{{ include "fullname" . }} {{ .Values.service.port }}:{{ .Values.service.targetPort }}
{{- end }}

2. Service: ''' + config.service_name + '''
   Type: ''' + config.service_type + '''
   Namespace: {{ .Values.namespace | default .Release.Namespace }}
'''

    def render_readme(self, config: ConverterConfig) -> str:
        envs = ', '.join(config.environments)
        env_files = ', '.join([f'`values-{e}.yaml`' for e in config.environments])
        dep_section = ("Dependency charts are enabled. Run `helm dependency update` before installing." if config.enable_dependencies else "Enable with `--enable-dependency-chart` flag during conversion.")
        svc = config.service_name
        ns = config.namespace
        stype = config.service_type
        appv = config.app_version

        return '''# ''' + svc + '''

Helm chart for **''' + svc + '''** (''' + stype + ''') on AKS.

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
  - [Monitoring](#monitoring-parameters)''' + ('''
  - [Java AJSC](#java-ajsc-parameters)''' if stype == 'java-ajsc' else '') + '''
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
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  -f ./''' + svc + '''/values-dev.yaml \\
  -n ''' + ns + ''' --create-namespace

# Prod environment
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  -f ./''' + svc + '''/values-prod.yaml \\
  -n ''' + ns + '''

# With image tag override
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  -f ./''' + svc + '''/values-prod.yaml \\
  --set image.tag=3.5.1 \\
  -n ''' + ns + '''

# Dry run (validate without deploying)
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  -f ./''' + svc + '''/values-dev.yaml \\
  -n ''' + ns + ''' --dry-run --debug
```

## Uninstallation

```bash
helm uninstall ''' + svc + ''' -n ''' + ns + '''
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
| `image.repository` | string | `acr.azurecr.io/''' + ns + '/' + svc + '''` | Docker image repository. |
| `image.tag` | string | `''' + appv + '''` | Docker image tag. Falls back to `Chart.appVersion`. |
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
| `ingress.hosts[].host` | string | `''' + svc + '''.example.com` | Hostname for routing. |
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
| `serviceMonitor.port` | string | `http` | Port name to scrape. |''' + ('''

### Java AJSC Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `javaOpts` | string | *(from Ansible ajsc_args_map)* | Full JVM options string. |
| `springProfilesActive` | string | `default` | Spring Boot active profiles. |
| `managementPort` | int | `8080` | Actuator/management port. |
| `tomcat.maxThreads` | int | `200` | Tomcat connector max threads. |
| `tomcat.minSpareThreads` | int | `25` | Tomcat connector min spare threads. |''' if stype == 'java-ajsc' else '') + '''

---

## Environment Overrides

Environment-specific values files override the base `values.yaml`. Generated environments: ''' + envs + '''.

Files: ''' + env_files + '''.

Layer them using Helm's `-f` flag (later files take precedence):

```bash
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  -f ./''' + svc + '''/values-{environment}.yaml \\
  -n ''' + ns + '''
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

''' + dep_section + '''

```bash
# Update dependencies
helm dependency update ./''' + svc + '''

# Install with dependency enabled
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  --set common-library.enabled=true \\
  -n ''' + ns + '''
```

---

## Examples

### Override replicas and image tag

```bash
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  --set replicaCount=3 \\
  --set image.tag=2.0.0 \\
  -n ''' + ns + '''
```

### Enable ingress with TLS

```bash
helm upgrade --install ''' + svc + ''' ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  --set ingress.enabled=true \\
  --set ingress.hosts[0].host=''' + svc + '''.prod.example.com \\
  --set ingress.tls[0].secretName=prod-tls \\
  --set ingress.tls[0].hosts[0]=''' + svc + '''.prod.example.com \\
  -n ''' + ns + '''
```

### Template rendering (no deploy)

```bash
helm template my-release ./''' + svc + ''' \\
  -f ./''' + svc + '''/values.yaml \\
  -f ./''' + svc + '''/values-dev.yaml
```

### Lint validation

```bash
helm lint ./''' + svc + '''/
```
'''

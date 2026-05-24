"""Data models for parsed Ansible data and Helm chart generation."""

from dataclasses import dataclass, field


@dataclass
class ResourceSpec:
    requests_memory: str = "256Mi"
    requests_cpu: str = "250m"
    limits_memory: str = "512Mi"
    limits_cpu: str = "500m"


@dataclass
class ProbeSpec:
    path: str = "/actuator/health"
    port: int = 8080
    scheme: str = "HTTP"
    initial_delay_seconds: int = 120
    period_seconds: int = 30
    timeout_seconds: int = 30


@dataclass
class EnvVar:
    name: str
    value: str | None = None
    secret_name: str | None = None
    secret_key: str | None = None
    field_ref: str | None = None


@dataclass
class VolumeSpec:
    name: str
    mount_path: str
    source_type: str  # configmap, secret
    source_name: str
    items: list[dict] | None = None
    optional: bool = False


@dataclass
class EnvironmentConfig:
    name: str
    variables: dict[str, str] = field(default_factory=dict)
    resources: ResourceSpec | None = None
    replicas: int = 1
    jvm_args: str = ""
    node_affinity_key: str = ""
    node_affinity_value: str = ""


@dataclass
class ParsedAnsibleData:
    service_name: str = ""
    service_type: str = ""
    namespace: str = ""
    container_port: int = 8080
    service_port: int = 80
    service_type_k8s: str = "ClusterIP"
    health_path: str = "/actuator/health"
    management_port: int = 8080
    image_pull_policy: str = "IfNotPresent"
    image_pull_secrets: list[str] = field(default_factory=lambda: ["regcred"])
    deployment_strategy: str = "RollingUpdate"
    max_unavailable: str = "25%"
    max_surge: str = "25%"
    min_ready_seconds: int = 120
    revision_history_limit: int = 3
    replicas: int = 1
    resources: dict[str, ResourceSpec] = field(default_factory=dict)
    liveness_probe: ProbeSpec | None = None
    readiness_probe: ProbeSpec | None = None
    env_vars: list[EnvVar] = field(default_factory=list)
    secret_env_vars: list[EnvVar] = field(default_factory=list)
    volumes: list[VolumeSpec] = field(default_factory=list)
    config_files: dict[str, str] = field(default_factory=dict)
    role_defaults: dict = field(default_factory=dict)
    environment_configs: dict[str, EnvironmentConfig] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    node_affinity_key: str = ""
    node_affinity_value: str = ""
    jvm_args: dict[str, str] = field(default_factory=dict)
    deployment_variants: list[dict] = field(default_factory=list)
    service_variants: list[dict] = field(default_factory=list)
    tomcat_max_threads: int = 200
    tomcat_min_spare_threads: int = 25


@dataclass
class ConversionResult:
    output_path: str
    files_created: int
    warnings: list[str] = field(default_factory=list)

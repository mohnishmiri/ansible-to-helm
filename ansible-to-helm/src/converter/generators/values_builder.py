"""Builds values.yaml and environment-specific values files from parsed Ansible data."""

from converter.core.config import ConverterConfig
from converter.core.models import ParsedAnsibleData, ResourceSpec


ENV_MAP = {
    "dev": ["com-att-attcc-dev-merge"],
    "perf": ["com-att-attcc-new-perf"],
    "stage": ["com-att-attcc-preprod"],
    "uat": ["com-att-attcc-uat-merge"],
    "prod": ["com-att-attcc-prod"],
    "dr": ["com-att-attcc-dr"],
}


class ValuesBuilder:
    def __init__(self, config: ConverterConfig):
        self.config = config

    def build(self, parsed: ParsedAnsibleData) -> dict:
        dev_resources = self._get_resources_for_env("dev", parsed)

        values = {
            "namespace": self.config.namespace,
            "appLabel": self.config.service_name,
            "routeoffer": "",
            "replicaCount": parsed.replicas,
            "image": {
                "repository": f"acr.azurecr.io/{self.config.namespace}/{self.config.service_name}",
                "tag": self.config.app_version,
                "pullPolicy": parsed.image_pull_policy,
            },
            "imagePullSecrets": [{"name": s} for s in parsed.image_pull_secrets],
            "nameOverride": "",
            "fullnameOverride": "",
            "serviceAccount": {
                "create": True,
                "annotations": {},
                "name": "",
            },
            "podAnnotations": {
                "prometheus.io/scrape": "true",
                "prometheus.io/port": str(parsed.management_port),
                "prometheus.io/path": "/actuator/prometheus",
            },
            "podSecurityContext": {
                "runAsNonRoot": True,
                "seccompProfile": {"type": "RuntimeDefault"},
            },
            "securityContext": {
                "allowPrivilegeEscalation": False,
                "readOnlyRootFilesystem": False,
                "runAsNonRoot": True,
                "capabilities": {"drop": ["ALL"]},
            },
            "service": {
                "type": "ClusterIP",
                "port": parsed.service_port,
                "targetPort": parsed.container_port,
            },
            "ingress": {
                "enabled": False,
                "className": "nginx",
                "annotations": {
                    "kubernetes.io/ingress.class": "nginx",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                },
                "hosts": [
                    {
                        "host": f"{self.config.service_name}.example.com",
                        "paths": [{"path": "/", "pathType": "Prefix"}],
                    }
                ],
                "tls": [],
            },
            "resources": {
                "requests": {
                    "memory": dev_resources.requests_memory,
                    "cpu": dev_resources.requests_cpu,
                },
                "limits": {
                    "memory": dev_resources.limits_memory,
                    "cpu": dev_resources.limits_cpu,
                },
            },
            "livenessProbe": self._probe_to_dict(parsed.liveness_probe, "Alive"),
            "readinessProbe": self._probe_to_dict(parsed.readiness_probe, "Ready"),
            "autoscaling": {
                "enabled": False,
                "minReplicas": parsed.replicas,
                "maxReplicas": max(parsed.replicas * 3, 3),
                "targetCPUUtilizationPercentage": 75,
                "targetMemoryUtilizationPercentage": 80,
            },
            "pdb": {
                "enabled": False,
                "minAvailable": 1,
            },
            "deploymentStrategy": {
                "type": parsed.deployment_strategy,
                "rollingUpdate": {
                    "maxUnavailable": parsed.max_unavailable,
                    "maxSurge": parsed.max_surge,
                },
            },
            "minReadySeconds": parsed.min_ready_seconds,
            "revisionHistoryLimit": max(parsed.revision_history_limit, 3),
            "nodeSelector": {},
            "tolerations": [],
            "affinity": self._build_affinity(parsed),
            "env": self._build_env_list(parsed),
            "envFromSecrets": self._build_secret_env_refs(parsed),
            "volumes": self._build_volumes(parsed),
            "volumeMounts": self._build_volume_mounts(parsed),
            "configFiles": parsed.config_files,
            "networkPolicy": {
                "enabled": False,
                "ingress": [
                    {"from": [{"namespaceSelector": {"matchLabels": {"name": self.config.namespace}}}]}
                ],
            },
            "serviceMonitor": {
                "enabled": False,
                "interval": "30s",
                "path": "/actuator/prometheus",
                "port": "http",
            },
        }

        if self.config.service_type == "java-ajsc":
            values["javaOpts"] = self._get_jvm_args_for_env("dev", parsed)
            values["env"].insert(0, {
                "name": "JAVA_OPTS",
                "value": "$(JAVA_OPTS_OVERRIDE)",
            })
            values["env"].insert(0, {
                "name": "JAVA_OPTS_OVERRIDE",
                "value": values["javaOpts"],
            })
            values["springProfilesActive"] = "default"
            values["managementPort"] = parsed.management_port
            values["tomcat"] = {
                "maxThreads": parsed.tomcat_max_threads,
                "minSpareThreads": parsed.tomcat_min_spare_threads,
            }

        return values

    def build_env_values(self, parsed: ParsedAnsibleData) -> dict[str, dict]:
        env_values = {}

        for env_name in self.config.environments:
            env_data = parsed.environment_configs.get(env_name, None)
            resources = self._get_resources_for_env(env_name, parsed)

            env_namespace = ENV_MAP.get(env_name, [self.config.namespace])[0]

            override: dict = {
                "namespace": env_namespace,
                "replicaCount": self._get_replicas_for_env(env_name),
                "resources": {
                    "requests": {
                        "memory": resources.requests_memory,
                        "cpu": resources.requests_cpu,
                    },
                    "limits": {
                        "memory": resources.limits_memory,
                        "cpu": resources.limits_cpu,
                    },
                },
            }

            if self.config.service_type == "java-ajsc":
                override["javaOpts"] = self._get_jvm_args_for_env(env_name, parsed)

            if env_name in ("prod", "dr"):
                override["autoscaling"] = {
                    "enabled": True,
                    "minReplicas": 2,
                    "maxReplicas": 6,
                    "targetCPUUtilizationPercentage": 70,
                }
                override["pdb"] = {"enabled": True, "minAvailable": 1}
                override["ingress"] = {
                    "enabled": True,
                    "annotations": {
                        "kubernetes.io/ingress.class": "nginx",
                        "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                    },
                }

            if env_data and env_data.variables:
                env_specific_vars = []
                interesting_keys = [
                    "ROUTEOFFER", "ENVCONTEXT", "AFTENVIRONMENT",
                    "AFTLATITUDE", "AFTLONGITUDE", "CSI_CLUSTER",
                    "WMQ_ENVCONTEXT", "GL_ENV", "DEBUG_LEVEL",
                ]
                for key in interesting_keys:
                    if key in env_data.variables:
                        env_specific_vars.append({
                            "name": key,
                            "value": env_data.variables[key],
                        })
                if env_specific_vars:
                    override["envOverrides"] = env_specific_vars

                if env_data.node_affinity_key:
                    override["affinity"] = {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": [{
                                    "matchExpressions": [{
                                        "key": env_data.node_affinity_key,
                                        "operator": "In",
                                        "values": [env_data.node_affinity_value],
                                    }]
                                }]
                            }
                        }
                    }

            env_values[env_name] = override

        return env_values

    def _get_resources_for_env(self, env_name: str, parsed: ParsedAnsibleData) -> ResourceSpec:
        for mapping_key in ENV_MAP.get(env_name, []):
            if mapping_key in parsed.resources:
                return parsed.resources[mapping_key]
        first_key = next(iter(parsed.resources), None)
        if first_key:
            return parsed.resources[first_key]
        return ResourceSpec()

    def _get_jvm_args_for_env(self, env_name: str, parsed: ParsedAnsibleData) -> str:
        for mapping_key in ENV_MAP.get(env_name, []):
            if mapping_key in parsed.jvm_args:
                raw = parsed.jvm_args[mapping_key]
                return self._clean_jinja_vars(raw)
        first = next(iter(parsed.jvm_args.values()), "")
        return self._clean_jinja_vars(first)

    def _clean_jinja_vars(self, value: str) -> str:
        import re
        result = value
        replacements = {
            r"\{\{dev_min_heap_size\}\}": "512m",
            r"\{\{dev_max_heap_size\}\}": "2048m",
            r"\{\{dev_min_metaspace_size\}\}": "256m",
            r"\{\{perf_min_heap_size\}\}": "512m",
            r"\{\{perf_max_heap_size\}\}": "2048m",
            r"\{\{perf_min_metaspace_size\}\}": "512m",
            r"\{\{uat_min_heap_size\}\}": "512m",
            r"\{\{uat_max_heap_size\}\}": "2048m",
            r"\{\{uat_min_metaspace_size\}\}": "512m",
            r"\{\{prod_min_heap_size\}\}": "512m",
            r"\{\{prod_max_heap_size\}\}": "2048m",
            r"\{\{prod_min_metaspace_size\}\}": "512m",
            r"\{\{preprod_min_heap_size\}\}": "512m",
            r"\{\{preprod_max_heap_size\}\}": "2048m",
            r"\{\{preprod_min_metaspace_size\}\}": "512m",
            r"\{\{dr_min_heap_size\}\}": "512m",
            r"\{\{dr_max_heap_size\}\}": "2048m",
            r"\{\{dr_min_metaspace_size\}\}": "512m",
            r"\{\{non_proxy_hosts\}\}": "*.windows.net",
        }
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result)
        result = re.sub(r"\{\{\w+\}\}", "", result)
        return result.strip()

    def _get_replicas_for_env(self, env_name: str) -> int:
        defaults = {"dev": 1, "perf": 2, "stage": 2, "uat": 1, "prod": 2, "dr": 2}
        return defaults.get(env_name, 1)

    def _probe_to_dict(self, probe, header_value: str) -> dict:
        if not probe:
            return {}
        return {
            "httpGet": {
                "path": probe.path,
                "port": probe.port,
                "scheme": probe.scheme,
                "httpHeaders": [{"name": "X-Custom-Header", "value": header_value}],
            },
            "initialDelaySeconds": probe.initial_delay_seconds,
            "periodSeconds": probe.period_seconds,
            "timeoutSeconds": probe.timeout_seconds,
        }

    def _build_affinity(self, parsed: ParsedAnsibleData) -> dict:
        if not parsed.node_affinity_key:
            return {}
        return {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [{
                        "matchExpressions": [{
                            "key": "nodepool",
                            "operator": "In",
                            "values": ["default"],
                        }]
                    }]
                }
            }
        }

    def _build_env_list(self, parsed: ParsedAnsibleData) -> list[dict]:
        env_list = []
        skip_vars = {"AJSCARGS", "AAF_ID", "AAF_PASSWORD"}

        for ev in parsed.env_vars:
            if ev.name in skip_vars:
                continue
            env_list.append({"name": ev.name, "value": ev.value or ""})

        return env_list

    def _build_secret_env_refs(self, parsed: ParsedAnsibleData) -> list[dict]:
        secret_groups: dict[str, list] = {}
        for ev in parsed.secret_env_vars:
            if ev.field_ref:
                continue
            if ev.secret_name:
                secret_groups.setdefault(ev.secret_name, []).append({
                    "name": ev.name,
                    "key": ev.secret_key,
                })

        result = []
        for secret_name, keys in secret_groups.items():
            result.append({
                "secretName": secret_name,
                "keys": keys,
            })
        return result

    def _build_volumes(self, parsed: ParsedAnsibleData) -> list[dict]:
        volumes = []
        for v in parsed.volumes:
            vol_name = self._clean_ansible_name(v.name)
            vol: dict = {"name": vol_name, "type": v.source_type}
            is_external = v.source_name and "{{" not in v.source_name
            if v.source_type == "configmap":
                if is_external:
                    vol["sourceName"] = v.source_name
                    vol["external"] = True
                else:
                    vol["sourceName"] = "config"
            elif v.source_type == "secret":
                if is_external:
                    vol["sourceName"] = v.source_name
                    vol["external"] = True
                else:
                    vol["sourceName"] = "secret"
                if v.optional:
                    vol["optional"] = True
            volumes.append(vol)
        return volumes if volumes else [
            {"name": "config-volume", "type": "configmap", "sourceName": "config"},
            {"name": "secret-volume", "type": "secret", "sourceName": "secret"},
        ]

    def _clean_ansible_name(self, name: str) -> str:
        import re
        cleaned = re.sub(r"\{\{[^}]+\}\}", "", name)
        cleaned = re.sub(r"^-+|-+$", "", cleaned).strip("-").strip()
        return cleaned or "app"

    def _build_volume_mounts(self, parsed: ParsedAnsibleData) -> list[dict]:
        mounts = []
        for v in parsed.volumes:
            mounts.append({
                "name": self._clean_ansible_name(v.name),
                "mountPath": v.mount_path,
            })
        return mounts if mounts else [
            {"name": "config-volume", "mountPath": "/opt/app/config"},
            {"name": "secret-volume", "mountPath": "/opt/app/secret"},
        ]

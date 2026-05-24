"""Core conversion engine that orchestrates parsing and generation."""

from pathlib import Path

from rich.console import Console

from converter.core.config import ConverterConfig
from converter.core.models import ConversionResult
from converter.parsers.registry import ParserRegistry
from converter.generators.helm_generator import HelmChartGenerator

console = Console()


class ConversionEngine:
    def __init__(self, config: ConverterConfig):
        self.config = config
        self.parser_registry = ParserRegistry()
        self.generator = HelmChartGenerator(config)

    def run(self) -> ConversionResult:
        console.print("[bold]Step 1/3:[/bold] Parsing Ansible sources...")
        parsed_data = self._parse_ansible()

        console.print("[bold]Step 2/3:[/bold] Transforming to Helm model...")
        helm_model = self.generator.build_model(parsed_data)

        console.print("[bold]Step 3/3:[/bold] Generating Helm chart...")
        if self.config.dry_run:
            console.print("[yellow]Dry run — no files written.[/yellow]")
            return ConversionResult(
                output_path=str(self.config.helm_chart_path),
                files_created=0,
            )

        return self.generator.generate(helm_model)

    def _parse_ansible(self):
        from converter.parsers.playbook_parser import PlaybookParser
        from converter.parsers.role_parser import RoleParser
        from converter.parsers.inventory_parser import InventoryParser
        from converter.parsers.k8s_template_parser import K8sTemplateParser
        from converter.core.models import ParsedAnsibleData

        parsed = ParsedAnsibleData(
            service_name=self.config.service_name,
            service_type=self.config.service_type,
            namespace=self.config.namespace,
        )

        playbook_parser = PlaybookParser(self.config.playbook_path)
        playbook_data = playbook_parser.parse()
        console.print(f"  Parsed playbook: [dim]{playbook_data.get('name', 'unknown')}[/dim]")

        role_parser = RoleParser(self.config.config_role_path)
        role_data = role_parser.parse()
        self._merge_role_data(parsed, role_data)

        inventory_parser = InventoryParser(self.config.playbook_path / "inventory")
        env_configs = inventory_parser.parse()
        for env_name, env_data in env_configs.items():
            parsed.environment_configs[env_name] = env_data

        k8s_template_dir = self.config.config_role_path / "templates" / "k8s"
        if k8s_template_dir.exists():
            k8s_parser = K8sTemplateParser(k8s_template_dir)
            k8s_data = k8s_parser.parse()
            self._merge_k8s_data(parsed, k8s_data)

        return parsed

    def _merge_role_data(self, parsed, role_data):
        defaults = role_data.get("defaults", {})

        if "resource_map" in defaults:
            from converter.core.models import ResourceSpec
            for env_key, res in defaults["resource_map"].items():
                parsed.resources[env_key] = ResourceSpec(
                    requests_memory=res.get("requests_memory", "256Mi"),
                    requests_cpu=res.get("requests_cpu", "250m"),
                    limits_memory=res.get("limits_memory", "512Mi"),
                    limits_cpu=res.get("limits_cpu", "500m"),
                )

        if "ajsc_args_map" in defaults:
            parsed.jvm_args = defaults["ajsc_args_map"]

        probe_fields = {
            "k8s_liveness_initialDelaySeconds": "initial_delay_seconds",
            "k8s_liveness_periodSeconds": "period_seconds",
            "k8s_liveness_timeoutSeconds": "timeout_seconds",
        }
        from converter.core.models import ProbeSpec
        liveness = ProbeSpec()
        readiness = ProbeSpec()
        for ans_key, spec_key in probe_fields.items():
            if ans_key in defaults:
                setattr(liveness, spec_key, int(defaults[ans_key]))
        for ans_key, spec_key in {
            "k8s_readiness_initialDelaySeconds": "initial_delay_seconds",
            "k8s_readiness_periodSeconds": "period_seconds",
            "k8s_readiness_timeoutSeconds": "timeout_seconds",
        }.items():
            if ans_key in defaults:
                setattr(readiness, spec_key, int(defaults[ans_key]))
        parsed.liveness_probe = liveness
        parsed.readiness_probe = readiness

        strategy_fields = {
            "k8s_deployment_strategy": "deployment_strategy",
            "k8s_imagepullpolicy": "image_pull_policy",
            "pod_maxUnavailable": "max_unavailable",
            "pod_maxSurge": "max_surge",
            "pod_minReadySeconds": "min_ready_seconds",
            "pod_revisionHistoryLimit": "revision_history_limit",
        }
        for ans_key, attr in strategy_fields.items():
            if ans_key in defaults:
                val = defaults[ans_key]
                if attr in ("min_ready_seconds", "revision_history_limit"):
                    val = int(val)
                setattr(parsed, attr, val)

        if "att_ms_replicas" in defaults:
            parsed.replicas = int(defaults["att_ms_replicas"])

        if "server_health_port" in defaults:
            parsed.management_port = int(defaults["server_health_port"])
        if "server_tomcat_max_threads" in defaults:
            parsed.tomcat_max_threads = int(defaults["server_tomcat_max_threads"])
        if "server_tomcat_min_Spare_Threads" in defaults:
            parsed.tomcat_min_spare_threads = int(defaults["server_tomcat_min_Spare_Threads"])

        parsed.config_files = role_data.get("config_files", {})
        parsed.role_defaults = defaults

    def _merge_k8s_data(self, parsed, k8s_data):
        if "env_vars" in k8s_data:
            parsed.env_vars = k8s_data["env_vars"]
        if "secret_env_vars" in k8s_data:
            parsed.secret_env_vars = k8s_data["secret_env_vars"]
        if "volumes" in k8s_data:
            parsed.volumes = k8s_data["volumes"]
        if "container_port" in k8s_data:
            parsed.container_port = k8s_data["container_port"]
        if "labels" in k8s_data:
            parsed.labels = k8s_data["labels"]
        if "annotations" in k8s_data:
            parsed.annotations = k8s_data["annotations"]
        if "node_affinity_key" in k8s_data:
            parsed.node_affinity_key = k8s_data["node_affinity_key"]
        if "node_affinity_value" in k8s_data:
            parsed.node_affinity_value = k8s_data["node_affinity_value"]
        if "service_port" in k8s_data:
            parsed.service_port = k8s_data["service_port"]
        if "service_type" in k8s_data:
            parsed.service_type_k8s = k8s_data["service_type"]
        if "deployment_variants" in k8s_data:
            parsed.deployment_variants = k8s_data["deployment_variants"]
        if "service_variants" in k8s_data:
            parsed.service_variants = k8s_data["service_variants"]

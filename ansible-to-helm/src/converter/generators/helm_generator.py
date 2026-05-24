"""Helm chart generator — builds the complete chart directory from parsed data."""

from pathlib import Path

import yaml

from converter.core.config import ConverterConfig
from converter.core.models import ParsedAnsibleData, ConversionResult
from converter.generators.values_builder import ValuesBuilder
from converter.generators.template_renderer import TemplateRenderer


class HelmChartGenerator:
    def __init__(self, config: ConverterConfig):
        self.config = config
        self.values_builder = ValuesBuilder(config)
        self.template_renderer = TemplateRenderer()

    def build_model(self, parsed: ParsedAnsibleData) -> dict:
        return {
            "parsed": parsed,
            "values": self.values_builder.build(parsed),
            "env_values": self.values_builder.build_env_values(parsed),
        }

    def generate(self, model: dict) -> ConversionResult:
        chart_dir = self.config.helm_chart_path
        templates_dir = chart_dir / "templates"
        charts_dir = chart_dir / "charts"
        files_created = 0

        for d in [chart_dir, templates_dir, charts_dir]:
            d.mkdir(parents=True, exist_ok=True)

        files_created += self._write_chart_yaml(chart_dir)
        files_created += self._write_values(chart_dir, model)
        files_created += self._write_templates(templates_dir, model)
        files_created += self._write_readme(chart_dir)

        return ConversionResult(
            output_path=str(chart_dir),
            files_created=files_created,
        )

    def _write_chart_yaml(self, chart_dir: Path) -> int:
        chart = {
            "apiVersion": "v2",
            "name": self.config.service_name,
            "description": f"Helm chart for {self.config.service_name} ({self.config.service_type})",
            "type": "application",
            "version": self.config.chart_version,
            "appVersion": self.config.app_version,
            "maintainers": [
                {"name": "Platform Engineering", "email": "platform-eng@company.com"}
            ],
            "keywords": [self.config.service_type, "aks", "microservice"],
        }

        if self.config.enable_dependencies:
            chart["dependencies"] = [
                {
                    "name": "common-library",
                    "version": "1.0.0",
                    "repository": "file://../common-library",
                    "condition": "common-library.enabled",
                }
            ]

        self._write_yaml(chart_dir / "Chart.yaml", chart)
        return 1

    def _write_values(self, chart_dir: Path, model: dict) -> int:
        count = 0

        self._write_yaml(chart_dir / "values.yaml", model["values"])
        count += 1

        envs_dir = chart_dir / "envs"
        envs_dir.mkdir(parents=True, exist_ok=True)
        for env_name, env_values in model["env_values"].items():
            self._write_yaml(envs_dir / f"{env_name}.yaml", env_values)
            count += 1

        return count

    def _write_templates(self, templates_dir: Path, model: dict) -> int:
        count = 0
        parsed: ParsedAnsibleData = model["parsed"]

        template_files = {
            "_helpers.tpl": self.template_renderer.render_helpers(self.config),
            "deployment.yaml": self.template_renderer.render_deployment(self.config, parsed),
            "service.yaml": self.template_renderer.render_service(self.config, parsed),
            "configmap.yaml": self.template_renderer.render_configmap(self.config, parsed),
            "secret.yaml": self.template_renderer.render_secret(self.config),
            "hpa.yaml": self.template_renderer.render_hpa(self.config),
            "serviceaccount.yaml": self.template_renderer.render_serviceaccount(self.config),
            "ingress.yaml": self.template_renderer.render_ingress(self.config),
            "networkpolicy.yaml": self.template_renderer.render_networkpolicy(self.config),
            "NOTES.txt": self.template_renderer.render_notes(self.config),
        }

        for filename, content in template_files.items():
            (templates_dir / filename).write_text(content, encoding="utf-8")
            count += 1

        return count

    def _write_readme(self, chart_dir: Path) -> int:
        readme = self.template_renderer.render_readme(self.config)
        (chart_dir / "README.md").write_text(readme, encoding="utf-8")
        return 1

    def _write_yaml(self, filepath: Path, data: dict):
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

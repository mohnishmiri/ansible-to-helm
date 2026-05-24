"""Converter configuration model."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConverterConfig:
    playbook_path: Path
    config_role_path: Path
    output_path: Path
    service_name: str
    service_type: str
    namespace: str
    enable_dependencies: bool = False
    environments: list[str] = field(default_factory=lambda: ["dev", "perf", "stage", "uat", "prod", "dr"])
    chart_version: str = "1.0.0"
    app_version: str = "1.0.0"
    dry_run: bool = False

    @property
    def helm_chart_path(self) -> Path:
        return self.output_path / self.service_name

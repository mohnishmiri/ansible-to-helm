"""Parser for Ansible inventory and environment-specific group_vars."""

from pathlib import Path
from typing import Any

from converter.parsers.base import BaseParser
from converter.core.models import EnvironmentConfig, ResourceSpec


class InventoryParser(BaseParser):
    def parse(self) -> dict[str, EnvironmentConfig]:
        environments = {}

        if not self.path.exists():
            return environments

        for env_dir in sorted(self.path.iterdir()):
            if not env_dir.is_dir():
                continue

            env_name = env_dir.name
            group_vars_file = env_dir / "group_vars" / "all"

            if not group_vars_file.exists():
                environments[env_name] = EnvironmentConfig(name=env_name)
                continue

            data = self._load_yaml(group_vars_file)
            if not isinstance(data, dict):
                environments[env_name] = EnvironmentConfig(name=env_name)
                continue

            env_config = EnvironmentConfig(name=env_name)
            env_config.variables = {k: str(v) for k, v in data.items() if v is not None}

            if "nodeAffinitykey" in data:
                env_config.node_affinity_key = data["nodeAffinitykey"]
            if "nodeAffinityvalue" in data:
                env_config.node_affinity_value = data["nodeAffinityvalue"]

            environments[env_name] = env_config

        return environments

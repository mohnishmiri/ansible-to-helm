"""Parser for Ansible role defaults, tasks, and config templates."""

from pathlib import Path
from typing import Any

from converter.parsers.base import BaseParser


class RoleParser(BaseParser):
    def parse(self) -> dict[str, Any]:
        result = {"defaults": {}, "tasks": [], "config_files": {}}

        defaults_dir = self.path / "defaults"
        if defaults_dir.exists():
            for f in defaults_dir.glob("*.yml"):
                result["defaults"].update(self._load_yaml(f))
            for f in defaults_dir.glob("*.yaml"):
                result["defaults"].update(self._load_yaml(f))

        tasks_dir = self.path / "tasks"
        if tasks_dir.exists():
            for f in sorted(tasks_dir.glob("*.yml")) + sorted(tasks_dir.glob("*.yaml")):
                data = self._load_yaml(f)
                if isinstance(data, list):
                    result["tasks"].extend(data)

        configs_dir = self.path / "templates" / "configs"
        if configs_dir.exists():
            for f in configs_dir.iterdir():
                if f.is_file():
                    result["config_files"][f.name] = self._read_file(f)

        return result

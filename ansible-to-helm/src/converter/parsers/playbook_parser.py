"""Parser for Ansible playbooks."""

from pathlib import Path
from typing import Any

from converter.parsers.base import BaseParser


class PlaybookParser(BaseParser):
    def parse(self) -> dict[str, Any]:
        result = {"name": "", "hosts": "", "roles": [], "serial": ""}

        playbook_files = list(self.path.glob("*.yml")) + list(self.path.glob("*.yaml"))
        if not playbook_files:
            return result

        for pf in playbook_files:
            data = self._load_yaml_all(pf)
            for doc in data:
                if not isinstance(doc, list):
                    doc = [doc]
                for play in doc:
                    if not isinstance(play, dict):
                        continue
                    result["name"] = play.get("name", result["name"])
                    result["hosts"] = play.get("hosts", result["hosts"])
                    result["serial"] = play.get("serial", result["serial"])
                    roles = play.get("roles", [])
                    for role in roles:
                        if isinstance(role, dict):
                            result["roles"].append(role.get("role", ""))
                        elif isinstance(role, str):
                            result["roles"].append(role)

        return result

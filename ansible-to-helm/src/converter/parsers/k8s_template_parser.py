"""Parser for existing Kubernetes YAML templates in Ansible roles."""

import re
from pathlib import Path
from typing import Any

from converter.parsers.base import BaseParser
from converter.core.models import EnvVar, VolumeSpec


class K8sTemplateParser(BaseParser):
    """Parses Ansible-templated K8s YAML to extract structure without resolving Jinja2 vars."""

    def parse(self) -> dict[str, Any]:
        result = {}

        deployment_file = self.path / "deployment.yaml"
        if deployment_file.exists():
            result.update(self._parse_deployment(deployment_file))

        service_file = self.path / "service.yaml"
        if service_file.exists():
            result.update(self._parse_service(service_file))

        return result

    def _parse_deployment(self, filepath: Path) -> dict[str, Any]:
        content = self._read_file(filepath)
        result: dict[str, Any] = {}

        port_match = re.search(r"containerPort:\s*(\d+)", content)
        if port_match:
            result["container_port"] = int(port_match.group(1))

        result["env_vars"] = []
        result["secret_env_vars"] = []

        env_blocks = self._extract_env_vars(content)
        for ev in env_blocks:
            if ev.secret_name or ev.field_ref:
                result["secret_env_vars"].append(ev)
            else:
                result["env_vars"].append(ev)

        result["volumes"] = self._extract_volumes(content)

        affinity_key = re.search(r"key:\s*\{\{(\w+)\}\}", content)
        if affinity_key:
            result["node_affinity_key"] = affinity_key.group(1)

        affinity_val = re.findall(r"values:\s*\n\s*-\s*\{\{(\w+)\}\}", content)
        if affinity_val:
            result["node_affinity_value"] = affinity_val[0]

        return result

    def _parse_service(self, filepath: Path) -> dict[str, Any]:
        content = self._read_file(filepath)
        result: dict[str, Any] = {}

        port_match = re.search(r"port:\s*(\d+)", content)
        if port_match:
            result["service_port"] = int(port_match.group(1))

        target_match = re.search(r"targetPort:\s*(\d+)", content)
        if target_match:
            result["target_port"] = int(target_match.group(1))

        type_match = re.search(r"type:\s*(\w+)", content)
        if type_match:
            result["service_type"] = type_match.group(1)

        return result

    def _extract_env_vars(self, content: str) -> list[EnvVar]:
        env_vars = []
        lines = content.split("\n")
        in_env_block = False
        env_indent = 0
        i = 0
        while i < len(lines):
            raw_line = lines[i]
            stripped = raw_line.strip()
            indent = len(raw_line) - len(raw_line.lstrip())

            if stripped == "env:":
                in_env_block = True
                env_indent = indent
                i += 1
                continue

            if in_env_block and indent <= env_indent and stripped and not stripped.startswith("-"):
                in_env_block = False

            if in_env_block and stripped.startswith("- name:"):
                env_name = stripped.split("- name:")[1].strip().strip('"')

                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith("value:"):
                        raw_val = next_line.split("value:", 1)[1].strip().strip('"')
                        ansible_var = re.search(r"\{\{(\w+)\}\}", raw_val)
                        env_vars.append(EnvVar(
                            name=env_name,
                            value=ansible_var.group(1) if ansible_var else raw_val,
                        ))
                    elif next_line.startswith("valueFrom:"):
                        ev = self._parse_value_from(env_name, lines, i + 1)
                        if ev:
                            env_vars.append(ev)
            i += 1
        return env_vars

    def _parse_value_from(self, name: str, lines: list[str], start: int) -> EnvVar | None:
        block = "\n".join(lines[start:start + 6])
        secret_name = re.search(r"name:\s*([\w-]+)", block)
        secret_key = re.search(r"key:\s*([\w_]+)", block)
        field_ref = re.search(r"fieldPath:\s*([\w.]+)", block)

        if field_ref:
            return EnvVar(name=name, field_ref=field_ref.group(1))
        if secret_name and secret_key:
            return EnvVar(
                name=name,
                secret_name=secret_name.group(1),
                secret_key=secret_key.group(1),
            )
        return None

    def _extract_volumes(self, content: str) -> list[VolumeSpec]:
        volumes = []
        lines = content.split("\n")

        volume_mount_map = {}
        in_mounts = False
        for line in lines:
            stripped = line.strip()
            if "volumeMounts:" in stripped:
                in_mounts = True
                continue
            if in_mounts:
                if stripped.startswith("- name:"):
                    current_vol = stripped.split("- name:")[1].strip()
                elif stripped.startswith("mountPath:"):
                    mount_path = stripped.split("mountPath:")[1].strip()
                    volume_mount_map[current_vol] = mount_path
                elif not stripped.startswith("mountPath") and not stripped.startswith("-") and ":" in stripped and not stripped.startswith("name:"):
                    if stripped.startswith("livenessProbe:") or stripped.startswith("readinessProbe:"):
                        in_mounts = False

        in_volumes = False
        current_vol_name = ""
        current_source_type = ""
        current_source_name = ""
        current_optional = False
        for line in lines:
            stripped = line.strip()
            if stripped == "volumes:":
                in_volumes = True
                continue
            if in_volumes:
                if stripped.startswith("- name:"):
                    if current_vol_name:
                        volumes.append(VolumeSpec(
                            name=current_vol_name,
                            mount_path=volume_mount_map.get(current_vol_name, "/mnt"),
                            source_type=current_source_type,
                            source_name=current_source_name,
                            optional=current_optional,
                        ))
                    current_vol_name = stripped.split("- name:")[1].strip()
                    current_source_type = ""
                    current_source_name = ""
                    current_optional = False
                elif stripped.startswith("configMap:"):
                    current_source_type = "configmap"
                elif stripped.startswith("secret:"):
                    current_source_type = "secret"
                elif stripped.startswith("name:") and current_source_type == "configmap":
                    current_source_name = stripped.split("name:")[1].strip()
                elif stripped.startswith("secretName:"):
                    current_source_name = stripped.split("secretName:")[1].strip()
                elif stripped.startswith("optional:"):
                    val = stripped.split("optional:")[1].strip().lower()
                    current_optional = val == "true"
                elif stripped.startswith("containers:"):
                    if current_vol_name:
                        volumes.append(VolumeSpec(
                            name=current_vol_name,
                            mount_path=volume_mount_map.get(current_vol_name, "/mnt"),
                            source_type=current_source_type,
                            source_name=current_source_name,
                            optional=current_optional,
                        ))
                    in_volumes = False

        return volumes

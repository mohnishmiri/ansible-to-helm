"""Tests for the Ansible role parser."""

import tempfile
from pathlib import Path

import pytest
import yaml

from converter.parsers.role_parser import RoleParser


@pytest.fixture
def role_dir(tmp_path):
    defaults_dir = tmp_path / "defaults"
    defaults_dir.mkdir()
    (defaults_dir / "main.yml").write_text(yaml.dump({
        "att_ms_replicas": "2",
        "k8s_imagepullpolicy": "Always",
        "k8s_readiness_initialDelaySeconds": "90",
        "k8s_readiness_periodSeconds": "15",
        "k8s_readiness_timeoutSeconds": "10",
        "resource_map": {
            "dev": {
                "limits_memory": "1Gi",
                "requests_memory": "512Mi",
                "limits_cpu": "500m",
                "requests_cpu": "250m",
            },
        },
    }))

    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "main.yaml").write_text(yaml.dump([
        {"name": "copy dir", "copy": {"src": "templates", "dest": "/tmp"}},
    ]))

    configs_dir = tmp_path / "templates" / "configs"
    configs_dir.mkdir(parents=True)
    (configs_dir / "app.properties").write_text("key=value\n")

    return tmp_path


def test_parse_defaults(role_dir):
    parser = RoleParser(role_dir)
    result = parser.parse()
    assert result["defaults"]["att_ms_replicas"] == "2"
    assert result["defaults"]["k8s_imagepullpolicy"] == "Always"


def test_parse_resource_map(role_dir):
    parser = RoleParser(role_dir)
    result = parser.parse()
    assert "dev" in result["defaults"]["resource_map"]
    assert result["defaults"]["resource_map"]["dev"]["limits_memory"] == "1Gi"


def test_parse_config_files(role_dir):
    parser = RoleParser(role_dir)
    result = parser.parse()
    assert "app.properties" in result["config_files"]
    assert result["config_files"]["app.properties"] == "key=value\n"


def test_parse_tasks(role_dir):
    parser = RoleParser(role_dir)
    result = parser.parse()
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["name"] == "copy dir"

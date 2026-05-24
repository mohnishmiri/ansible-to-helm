"""Tests for the inventory parser."""

from pathlib import Path

import pytest
import yaml

from converter.parsers.inventory_parser import InventoryParser


@pytest.fixture
def inventory_dir(tmp_path):
    for env in ["dev", "prod"]:
        group_vars = tmp_path / env / "group_vars"
        group_vars.mkdir(parents=True)
        (group_vars / "all").write_text(yaml.dump({
            "ROUTEOFFER": "D2A" if env == "dev" else "P1A",
            "ENVCONTEXT": "TEST" if env == "dev" else "PROD",
            "nodeAffinitykey": "nodepool",
            "nodeAffinityvalue": "default",
        }))
    return tmp_path


def test_parse_environments(inventory_dir):
    parser = InventoryParser(inventory_dir)
    result = parser.parse()
    assert "dev" in result
    assert "prod" in result


def test_env_variables(inventory_dir):
    parser = InventoryParser(inventory_dir)
    result = parser.parse()
    assert result["dev"].variables["ROUTEOFFER"] == "D2A"
    assert result["prod"].variables["ENVCONTEXT"] == "PROD"


def test_node_affinity(inventory_dir):
    parser = InventoryParser(inventory_dir)
    result = parser.parse()
    assert result["dev"].node_affinity_key == "nodepool"

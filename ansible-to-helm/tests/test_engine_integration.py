"""Integration test — runs the full conversion pipeline against real Ansible data."""

import os
import pytest
from pathlib import Path

from converter.core.config import ConverterConfig
from converter.core.engine import ConversionEngine


REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def real_config(tmp_path):
    playbook_path = REPO_ROOT / "playbook"
    config_role_path = REPO_ROOT / "configrole"

    if not playbook_path.exists() or not config_role_path.exists():
        pytest.skip("Real Ansible data not found at repo root")

    return ConverterConfig(
        playbook_path=playbook_path,
        config_role_path=config_role_path,
        output_path=tmp_path,
        service_name="customer-ms",
        service_type="java-ajsc",
        namespace="customer",
        environments=["dev", "perf", "uat", "prod"],
        enable_dependencies=True,
    )


def test_full_conversion(real_config):
    engine = ConversionEngine(real_config)
    result = engine.run()
    chart_dir = Path(result.output_path)

    assert (chart_dir / "Chart.yaml").exists()
    assert (chart_dir / "values.yaml").exists()
    assert (chart_dir / "values-dev.yaml").exists()
    assert (chart_dir / "values-prod.yaml").exists()
    assert (chart_dir / "templates" / "deployment.yaml").exists()
    assert (chart_dir / "templates" / "service.yaml").exists()
    assert (chart_dir / "templates" / "hpa.yaml").exists()
    assert (chart_dir / "templates" / "pdb.yaml").exists()
    assert (chart_dir / "templates" / "ingress.yaml").exists()
    assert (chart_dir / "templates" / "configmap.yaml").exists()
    assert (chart_dir / "templates" / "secret.yaml").exists()
    assert (chart_dir / "templates" / "serviceaccount.yaml").exists()
    assert (chart_dir / "templates" / "networkpolicy.yaml").exists()
    assert (chart_dir / "templates" / "_helpers.tpl").exists()
    assert (chart_dir / "templates" / "NOTES.txt").exists()
    assert (chart_dir / "README.md").exists()

    assert result.files_created > 10

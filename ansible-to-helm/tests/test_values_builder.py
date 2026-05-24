"""Tests for the values builder."""

import pytest

from converter.core.config import ConverterConfig
from converter.core.models import ParsedAnsibleData, ResourceSpec, ProbeSpec
from converter.generators.values_builder import ValuesBuilder


@pytest.fixture
def config(tmp_path):
    return ConverterConfig(
        playbook_path=tmp_path / "playbook",
        config_role_path=tmp_path / "role",
        output_path=tmp_path / "output",
        service_name="test-ms",
        service_type="java-ajsc",
        namespace="test-ns",
        environments=["dev", "prod"],
    )


@pytest.fixture
def parsed():
    p = ParsedAnsibleData(
        service_name="test-ms",
        service_type="java-ajsc",
        namespace="test-ns",
        container_port=8080,
        replicas=1,
    )
    p.resources["com-att-attcc-dev-merge"] = ResourceSpec(
        requests_memory="1Gi",
        requests_cpu="512m",
        limits_memory="2Gi",
        limits_cpu="1024m",
    )
    p.liveness_probe = ProbeSpec(initial_delay_seconds=120)
    p.readiness_probe = ProbeSpec(initial_delay_seconds=110)
    return p


def test_build_values(config, parsed):
    builder = ValuesBuilder(config)
    values = builder.build(parsed)
    assert values["replicaCount"] == 1
    assert values["service"]["targetPort"] == 8080
    assert values["resources"]["requests"]["memory"] == "1Gi"


def test_build_env_values(config, parsed):
    builder = ValuesBuilder(config)
    env_values = builder.build_env_values(parsed)
    assert "dev" in env_values
    assert "prod" in env_values
    assert env_values["prod"]["autoscaling"]["enabled"] is True


def test_dr_env_mirrors_prod(tmp_path, parsed):
    cfg = ConverterConfig(
        playbook_path=tmp_path / "playbook",
        config_role_path=tmp_path / "role",
        output_path=tmp_path / "output",
        service_name="test-ms",
        service_type="java-ajsc",
        namespace="test-ns",
        environments=["dev", "prod", "dr"],
    )
    parsed.resources["com-att-attcc-dr"] = ResourceSpec(
        requests_memory="2Gi",
        requests_cpu="512m",
        limits_memory="4Gi",
        limits_cpu="1024m",
    )
    builder = ValuesBuilder(cfg)
    env_values = builder.build_env_values(parsed)
    assert "dr" in env_values
    assert env_values["dr"]["autoscaling"]["enabled"] is True
    assert env_values["dr"]["pdb"]["enabled"] is True
    assert env_values["dr"]["ingress"]["enabled"] is True
    assert env_values["dr"]["replicaCount"] == 2
    assert env_values["dr"]["resources"]["limits"]["memory"] == "4Gi"


def test_java_opts_in_values(config, parsed):
    builder = ValuesBuilder(config)
    values = builder.build(parsed)
    assert "javaOpts" in values

"""CLI entry point for the Ansible to Helm converter."""

import sys
from pathlib import Path

import click
from rich.console import Console

from converter.core.engine import ConversionEngine
from converter.core.config import ConverterConfig

console = Console()


@click.command()
@click.option("--playbook-location", required=True, type=click.Path(exists=True),
              help="Path to Ansible playbooks directory")
@click.option("--config-role-location", required=True, type=click.Path(exists=True),
              help="Path to Ansible roles/config directory")
@click.option("--output-location", required=True, type=click.Path(),
              help="Output directory for generated Helm chart")
@click.option("--service-name", required=True, help="Name of the microservice")
@click.option("--service-type", required=True,
              type=click.Choice(["java-ajsc", "nodejs", "react", "generic"]),
              help="Type of microservice")
@click.option("--namespace", required=True, help="Kubernetes namespace")
@click.option("--enable-dependency-chart", default=False, is_flag=True,
              help="Enable dependency chart support")
@click.option("--environment", multiple=True, default=["dev", "perf", "stage", "uat", "prod", "dr"],
              help="Environments to generate values files for")
@click.option("--chart-version", default="1.0.0", help="Helm chart version")
@click.option("--app-version", default="1.0.0", help="Application version")
@click.option("--dry-run", is_flag=True, help="Show what would be generated without writing")
def main(playbook_location, config_role_location, output_location,
         service_name, service_type, namespace, enable_dependency_chart,
         environment, chart_version, app_version, dry_run):
    """Convert Ansible playbooks and roles into production-ready Helm charts."""
    config = ConverterConfig(
        playbook_path=Path(playbook_location),
        config_role_path=Path(config_role_location),
        output_path=Path(output_location),
        service_name=service_name,
        service_type=service_type,
        namespace=namespace,
        enable_dependencies=enable_dependency_chart,
        environments=list(environment),
        chart_version=chart_version,
        app_version=app_version,
        dry_run=dry_run,
    )

    console.print(f"[bold blue]Ansible to Helm Converter v1.0.0[/bold blue]")
    console.print(f"  Service: [green]{service_name}[/green] ({service_type})")
    console.print(f"  Namespace: [green]{namespace}[/green]")
    console.print(f"  Environments: [green]{', '.join(environment)}[/green]")
    console.print()

    try:
        engine = ConversionEngine(config)
        result = engine.run()
        console.print(f"\n[bold green]Helm chart generated at:[/bold green] {result.output_path}")
        console.print(f"  Files created: {result.files_created}")
        console.print(f"\n[dim]Run 'helm lint {result.output_path}' to validate.[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

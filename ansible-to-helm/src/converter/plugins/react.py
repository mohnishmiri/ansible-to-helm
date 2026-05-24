"""React frontend application plugin."""

from converter.plugins.base_plugin import ServiceTypePlugin
from converter.core.models import ParsedAnsibleData


class ReactPlugin(ServiceTypePlugin):
    @property
    def service_type(self) -> str:
        return "react"

    def customize_values(self, values: dict, parsed: ParsedAnsibleData) -> dict:
        values["livenessProbe"]["httpGet"]["path"] = "/"
        values["readinessProbe"]["httpGet"]["path"] = "/"
        values["resources"] = {
            "requests": {"memory": "128Mi", "cpu": "100m"},
            "limits": {"memory": "256Mi", "cpu": "250m"},
        }
        return values

    def default_health_path(self) -> str:
        return "/"

    def default_port(self) -> int:
        return 80

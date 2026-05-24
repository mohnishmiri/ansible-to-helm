"""Node.js microservice plugin."""

from converter.plugins.base_plugin import ServiceTypePlugin
from converter.core.models import ParsedAnsibleData


class NodejsPlugin(ServiceTypePlugin):
    @property
    def service_type(self) -> str:
        return "nodejs"

    def customize_values(self, values: dict, parsed: ParsedAnsibleData) -> dict:
        values.setdefault("nodeOptions", "--max-old-space-size=2048")
        values["livenessProbe"]["httpGet"]["path"] = "/health"
        values["readinessProbe"]["httpGet"]["path"] = "/health"
        return values

    def default_health_path(self) -> str:
        return "/health"

    def default_port(self) -> int:
        return 3000

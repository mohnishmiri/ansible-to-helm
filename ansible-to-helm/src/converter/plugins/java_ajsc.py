"""Java AJSC microservice plugin."""

from converter.plugins.base_plugin import ServiceTypePlugin
from converter.core.models import ParsedAnsibleData


class JavaAjscPlugin(ServiceTypePlugin):
    @property
    def service_type(self) -> str:
        return "java-ajsc"

    def customize_values(self, values: dict, parsed: ParsedAnsibleData) -> dict:
        values.setdefault("javaOpts", "-Xms512m -Xmx2048m -XX:MetaspaceSize=256m")
        values.setdefault("springProfilesActive", "default")
        values.setdefault("managementPort", 8080)
        values.setdefault("tomcat", {
            "maxThreads": parsed.tomcat_max_threads,
            "minSpareThreads": parsed.tomcat_min_spare_threads,
        })
        return values

    def default_health_path(self) -> str:
        return "/actuator/health"

    def default_port(self) -> int:
        return 8080

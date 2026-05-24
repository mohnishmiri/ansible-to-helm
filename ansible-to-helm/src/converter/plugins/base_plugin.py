"""Base plugin interface for service-type-specific conversions."""

from abc import ABC, abstractmethod
from converter.core.models import ParsedAnsibleData


class ServiceTypePlugin(ABC):
    @property
    @abstractmethod
    def service_type(self) -> str:
        ...

    @abstractmethod
    def customize_values(self, values: dict, parsed: ParsedAnsibleData) -> dict:
        ...

    @abstractmethod
    def default_health_path(self) -> str:
        ...

    @abstractmethod
    def default_port(self) -> int:
        ...

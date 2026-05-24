"""Base parser interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml


class BaseParser(ABC):
    def __init__(self, path: Path):
        self.path = path

    @abstractmethod
    def parse(self) -> Any:
        ...

    def _load_yaml(self, filepath: Path) -> Any:
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_yaml_all(self, filepath: Path) -> list:
        with open(filepath, "r", encoding="utf-8") as f:
            return list(yaml.safe_load_all(f))

    def _read_file(self, filepath: Path) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

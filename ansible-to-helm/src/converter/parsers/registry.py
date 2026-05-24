"""Plugin registry for parsers."""


class ParserRegistry:
    def __init__(self):
        self._parsers: dict[str, type] = {}

    def register(self, name: str, parser_class: type):
        self._parsers[name] = parser_class

    def get(self, name: str) -> type | None:
        return self._parsers.get(name)

    def list_parsers(self) -> list[str]:
        return list(self._parsers.keys())

from dataclasses import dataclass


@dataclass(slots=True)
class Branch:
    id: str
    current_node_name: str | None
    _is_entry: bool = False

    @property
    def is_entry(self) -> bool:
        return self._is_entry

    def advance_to(self, next_name: str | None) -> None:
        self.current_node_name = next_name
        self._is_entry = False

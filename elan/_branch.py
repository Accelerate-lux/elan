from dataclasses import dataclass


@dataclass(slots=True)
class Branch:
    id: str
    current_node_name: str | None
    _is_entry: bool = False
    _is_complete: bool = False

    @property
    def is_entry(self) -> bool:
        return self._is_entry

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    def advance_to(self, next_name: str | None) -> None:
        self.current_node_name = next_name
        self._is_entry = False

    def complete(self) -> None:
        self.current_node_name = None
        self._is_entry = False
        self._is_complete = True

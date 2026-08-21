from dataclasses import dataclass, field


@dataclass(slots=True)
class Branch:
    id: str
    current_node_name: str | None
    _is_entry: bool = False
    _is_complete: bool = False
    scope_instances: dict[str, str] = field(default_factory=dict)
    suspended_on: str | None = None

    @property
    def is_entry(self) -> bool:
        return self._is_entry

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    def advance_to(self, next_name: str | None) -> None:
        self.current_node_name = next_name
        self._is_entry = False
        self._is_complete = False
        self.suspended_on = None

    def suspend(self, scope_instance_id: str) -> None:
        self.current_node_name = None
        self._is_entry = False
        self._is_complete = False
        self.suspended_on = scope_instance_id

    def complete(self) -> None:
        self.current_node_name = None
        self._is_entry = False
        self._is_complete = True
        self.suspended_on = None

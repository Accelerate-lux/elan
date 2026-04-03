from __future__ import annotations

from dataclasses import dataclass

from ._refs import ModelFieldRef


@dataclass(frozen=True, slots=True)
class When:
    condition: str | ModelFieldRef
    target: str | list[str]

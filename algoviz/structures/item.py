from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Item:
    id: Any
    value: Any

    def __post_init__(self):
        if type(self.id) not in (int, str):
            raise ValueError("ID элемента должен быть целым числом или строкой.")

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Algorithm:
    id: str
    title: str
    category: str
    description: str
    input_type: str
    visualization: str
    example: str
    build: Callable[[Any], dict]

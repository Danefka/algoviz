"""Input editors/validation only; no model or renderer dispatch."""
from dataclasses import dataclass
from typing import Callable
from . import integer_array


@dataclass(frozen=True)
class InputSpec:
    id: str
    input_hint: str
    parse: Callable
    random_input: Callable


INPUTS = {
    "integer_array": InputSpec("integer_array", "До 12 целых чисел от −99 до 99",
                                integer_array.parse_values, integer_array.random_input),
}


def get_input(input_type):
    try:
        return INPUTS[input_type]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Неизвестный формат ввода: {input_type}") from exc

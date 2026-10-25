"""Numeric input policy; independent of the reusable array model."""
from __future__ import annotations

import random
import re

MAX_ITEMS = 12
MIN_VALUE = -99
MAX_VALUE = 99


def parse_values(text: str) -> list[int]:
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    if not text:
        raise ValueError("Введите хотя бы одно целое число.")
    tokens = re.split(r"[,;\s]+", text)
    if len(tokens) > MAX_ITEMS:
        raise ValueError(f"Можно показать до {MAX_ITEMS} чисел.")
    if any(not re.fullmatch(r"[+-]?[0-9]{1,3}", token) for token in tokens):
        raise ValueError("Введите целые числа через запятую или пробел.")
    values = [int(token) for token in tokens]
    validate_values(values)
    return values


def validate_values(values):
    if not isinstance(values, list) or len(values) > MAX_ITEMS:
        raise ValueError(f"Нужен массив длиной до {MAX_ITEMS} элементов.")
    if any(type(value) is not int or not MIN_VALUE <= value <= MAX_VALUE for value in values):
        raise ValueError("Числа должны быть целыми, от −99 до 99.")


def random_input() -> str:
    return ", ".join(map(str, random.sample(range(1, 21), 6)))

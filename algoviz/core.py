"""Build and validate deterministic, renderer-independent execution records."""
from copy import deepcopy
from .registry import get_algorithm
from .inputs.integer_array import MAX_ITEMS, MIN_VALUE, MAX_VALUE, parse_values


def build_execution(values, algorithm_id="bubble_sort"):
    return get_algorithm(algorithm_id).build(values)


def validate_execution(execution):
    try:
        if execution["schema_version"] != 2:
            raise ValueError("Нужна история формата 2. Создайте её заново из исходного ввода.")
        algorithm = get_algorithm(execution["algorithm"])
        expected = algorithm.build(deepcopy(execution["input"]))
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Повреждена запись выполнения.") from exc
    if execution != expected:
        raise ValueError("Запись шагов не соответствует выбранному алгоритму.")

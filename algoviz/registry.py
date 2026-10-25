"""Discover algorithm cards once at startup, in the GUI and export worker."""
from importlib import import_module
from pkgutil import iter_modules

from . import algorithms
from .algorithms.spec import Algorithm
from .inputs.registry import get_input
from .renderers.registry import get_visualization


def iter_algorithm_modules(package):
    modules = iter_modules(package.__path__, package.__name__ + ".")
    for info in sorted(modules, key=lambda item: item.name):
        short_name = info.name.rsplit(".", 1)[-1]
        if short_name == "spec" or short_name.startswith("_"):
            continue
        if info.ispkg:
            try:
                nested = import_module(info.name)
            except Exception as exc:
                raise ValueError(f"Не удалось загрузить пакет {info.name}: {exc}") from exc
            yield from iter_algorithm_modules(nested)
        else:
            yield info


def discover_algorithms():
    catalog = {}
    sources = {}
    for info in sorted(iter_algorithm_modules(algorithms), key=lambda item: item.name):
        try:
            module = import_module(info.name)
        except Exception as exc:
            raise ValueError(f"Не удалось загрузить алгоритм из {info.name}: {exc}") from exc
        if not hasattr(module, "ALGORITHM"):
            continue
        entry = module.ALGORITHM
        if not isinstance(entry, Algorithm):
            raise ValueError(f"В {info.name} ALGORITHM должен быть объектом Algorithm.")
        if not isinstance(entry.id, str) or not entry.id.strip():
            raise ValueError(f"В {info.name} нужен непустой строковый ID алгоритма.")
        if not callable(entry.build):
            raise ValueError(f"В {info.name} build должен быть функцией.")
        try:
            get_input(entry.input_type)
            get_visualization(entry.visualization)
        except ValueError as exc:
            raise ValueError(f"Неверная карточка в {info.name}: {exc}") from exc
        if entry.id in catalog:
            raise ValueError(
                f"Повторяющийся ID {entry.id!r}: {sources[entry.id]} и {info.name}.")
        catalog[entry.id] = entry
        sources[entry.id] = info.name
    return catalog


ALGORITHMS = discover_algorithms()


def list_algorithms():
    return tuple(ALGORITHMS.values())


def get_algorithm(algorithm_id):
    try:
        return ALGORITHMS[algorithm_id]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Неизвестный алгоритм: {algorithm_id}") from exc

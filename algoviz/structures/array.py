"""Reusable array model. No parsing, sorting, history or drawing."""
from copy import deepcopy
from .item import Item


class Array:
    def __init__(self, values, element_ids=None):
        values = list(values)
        ids = list(range(len(values))) if element_ids is None else list(element_ids)
        if len(ids) != len(values):
            raise ValueError("Число ID не совпадает с числом элементов.")
        self._items = [Item(i, deepcopy(value)) for i, value in zip(ids, values)]
        self._check_ids(self._items)

    @staticmethod
    def _check_ids(items):
        if any(not isinstance(item, Item) for item in items):
            raise ValueError("Ожидаются элементы Item.")
        if len({item.id for item in items}) != len(items):
            raise ValueError("ID внутри массива должны быть уникальны.")

    def __len__(self):
        return len(self._items)

    def _check_index(self, index):
        if type(index) is not int or not 0 <= index < len(self):
            raise IndexError("Индекс вне массива.")

    def __getitem__(self, index):
        return self.item(index).value

    def item(self, index):
        self._check_index(index)
        return deepcopy(self._items[index])

    @property
    def values(self):
        return [deepcopy(item.value) for item in self._items]

    @property
    def element_ids(self):
        return [item.id for item in self._items]

    def swap(self, i, j):
        self._check_index(i)
        self._check_index(j)
        self._items[i], self._items[j] = self._items[j], self._items[i]

    def replace_range(self, lo, hi, items):
        items = list(items)
        if type(lo) is not int or type(hi) is not int or not 0 <= lo <= hi <= len(self):
            raise IndexError("Участок вне массива.")
        if len(items) != hi - lo:
            raise ValueError("Размер участка должен сохраниться.")
        candidate = self._items[:lo] + deepcopy(items) + self._items[hi:]
        self._check_ids(candidate)
        self._items = candidate

    def snapshot(self):
        return {"values": self.values, "element_ids": self.element_ids}

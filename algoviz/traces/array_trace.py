from ..inputs.integer_array import validate_values
from ..structures.array import Array
from .base import Recorder


class ArrayTrace(Recorder):
    def __init__(self, values, algorithm_id):
        validate_values(values)
        self.array = Array(values)
        self.state = {"sorted_indices": [], "comparisons": 0, "swaps": 0,
                      "focus": {"range": None, "pivot_id": None, "pointers": {}}}
        super().__init__(algorithm_id, values, self.capture, {"order": "ascending"})

    def capture(self):
        return {**self.array.snapshot(), **self.state}

    @property
    def values(self):
        return self.array.values

    def compare(self, i, j, *, description=None, line_id="compare"):
        left, right = self.array[i], self.array[j]
        self.state["comparisons"] += 1
        self.record("compare", {"indices": [i, j]},
                    description or f"Сравниваем {left} и {right}", line_id)
        return left, right

    def swap(self, i, j, *, description=None, line_id="swap"):
        left, right = self.array[i], self.array[j]
        if i == j:
            return
        self.array.swap(i, j)
        self.state["swaps"] += 1
        self.record("swap", {"indices": [i, j]},
                    description or f"Меняем местами {left} и {right}", line_id)

    def _validate_pointers(self, pointers, lo, hi):
        if not isinstance(pointers, dict):
            raise ValueError("Указатели задаются словарём: имя → индекс.")
        for name, index in pointers.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("У указателя должно быть непустое имя.")
            if type(index) is not int or not lo <= index < hi:
                raise ValueError("Указатель должен находиться внутри текущего участка.")

    def set_focus(self, lo, hi, *, pivot=None, pointers=None, description=None):
        """Select [lo, hi), an optional pivot by index, and named index pointers.

        The pivot is stored by element ID so it follows the value during swaps.
        Pointers belong to positions and remain in place when elements move.
        """
        if type(lo) is not int or type(hi) is not int or not 0 <= lo < hi <= len(self.array):
            raise ValueError("Нужен непустой участок [lo, hi) внутри массива.")
        if pivot is not None and (type(pivot) is not int or not lo <= pivot < hi):
            raise ValueError("Опорный элемент должен находиться внутри участка.")
        pointers = {} if pointers is None else pointers
        self._validate_pointers(pointers, lo, hi)
        self.state["focus"] = {"range": [lo, hi],
                               "pivot_id": None if pivot is None else self.array.item(pivot).id,
                               "pointers": dict(pointers)}
        self.record("focus", {"indices": []},
                    description or f"Работаем с участком от {lo} до {hi - 1}")

    def move_pointers(self, *, description=None, **positions):
        """Move named pointers; None removes a pointer. Records only changes."""
        focus = self.state["focus"]
        if focus["range"] is None:
            raise ValueError("Сначала выдели участок через set_focus.")
        pointers = dict(focus["pointers"])
        for name, index in positions.items():
            if index is None:
                pointers.pop(name, None)
            else:
                pointers[name] = index
        self._validate_pointers(pointers, *focus["range"])
        if pointers != focus["pointers"]:
            focus["pointers"] = pointers
            self.record("pointers", {"indices": []}, description or "Перемещаем указатели")

    def clear_focus(self):
        if self.state["focus"]["range"] is not None:
            self.state["focus"] = {"range": None, "pivot_id": None, "pointers": {}}
            self.record("focus", {"indices": []}, "Завершили работу с участком")

    def mark_sorted(self, indices, *, description=None):
        fresh = sorted(set(indices) - set(self.state["sorted_indices"]))
        if fresh:
            self.state["sorted_indices"] = sorted(set(self.state["sorted_indices"]) | set(fresh))
            self.record("mark_sorted", {"indices": fresh},
                        description or "Эти элементы уже на своих местах", "pass_complete")

    def finish(self):
        self.clear_focus()
        self.mark_sorted(range(len(self.array)))
        self.record("done", {"indices": []}, "Готово! Массив отсортирован", "finished")
        return self.execution()

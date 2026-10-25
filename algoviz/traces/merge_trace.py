"""Persistent recursion tree and merge buffers in one seekable history."""
from __future__ import annotations

from ..inputs.integer_array import validate_values
from ..structures.array import Array
from .base import Recorder


class MergeTrace(Recorder):
    def __init__(self, values, algorithm_id):
        validate_values(values)
        self.original_values = list(values)
        self.array = Array(values)
        self.original_items = {self.array.item(i).id: self.array.item(i) for i in range(len(self.array))}
        self.state = {
            "arrays": {"left": [], "right": [], "result": []},
            "pointers": {"left": 0, "right": 0},
            "range": [0, len(values)], "middle": None, "depth": 0,
            "phase": "initial", "comparisons": 0, "writes": 0, "merges": 0,
            "nodes": {}, "active_node": self.node_id(0, len(values)),
            "selected": {}, "selection_kind": "normal",
        }
        self.add_node(0, len(values), 0, None)
        super().__init__(algorithm_id, values, self.capture, {"order": "ascending"})

    def capture(self):
        return {**self.array.snapshot(), **self.state}

    @staticmethod
    def node_id(lo, hi):
        return f"{lo}:{hi}"

    def add_node(self, lo, hi, depth, parent):
        self.state["nodes"][self.node_id(lo, hi)] = {
            "range": [lo, hi], "depth": depth, "parent": parent,
            "ids": self.array.element_ids[lo:hi],
            "status": "ready" if hi - lo < 2 else "pending",
        }

    def numbers(self, ids):
        return "[" + ", ".join(str(self.original_values[i]) for i in ids) + "]"

    def focus(self, lo, middle, hi, depth, phase):
        ids = self.array.element_ids
        self.state.update({
            "range": [lo, hi], "middle": middle, "depth": depth, "phase": phase,
            "arrays": {"left": ids[lo:middle], "right": ids[middle:hi], "result": []},
            "pointers": {"left": 0, "right": 0},
            "active_node": self.node_id(lo, hi), "selected": {},
            "selection_kind": "normal",
        })

    def split(self, lo, middle, hi, depth):
        self.focus(lo, middle, hi, depth, "split")
        node = self.state["active_node"]
        self.state["nodes"][node]["status"] = "split"
        self.add_node(lo, middle, depth + 1, node)
        self.add_node(middle, hi, depth + 1, node)
        self.record("split", {"range": [lo, hi], "middle": middle},
                    f"Делим {self.numbers(self.state['nodes'][node]['ids'])} пополам")

    def begin_merge(self, lo, middle, hi, depth):
        self.focus(lo, middle, hi, depth, "merge")
        node = self.state["nodes"][self.state["active_node"]]
        node.update({"status": "merging", "ids": []})
        self.record("merge_start", {"range": [lo, hi], "middle": middle},
                    f"Собираем {self.numbers(self.state['arrays']['left'])} "
                    f"и {self.numbers(self.state['arrays']['right'])}")

    def source_node(self, side):
        lo, hi = self.state["range"]
        middle = self.state["middle"]
        return self.node_id(lo, middle) if side == "left" else self.node_id(middle, hi)

    def has_next(self, side):
        return self.state["pointers"][side] < len(self.state["arrays"][side])

    def compare(self):
        left = self.state["pointers"]["left"]
        right = self.state["pointers"]["right"]
        left_id = self.state["arrays"]["left"][left]
        right_id = self.state["arrays"]["right"][right]
        a, b = self.original_values[left_id], self.original_values[right_id]
        self.state["comparisons"] += 1
        self.state["selected"] = {self.source_node("left"): [left], self.source_node("right"): [right]}
        self.state["selection_kind"] = "compare"
        self.record("merge_compare", {"left": left, "right": right},
                    f"Сравниваем {a} и {b}" + (" — равны, берём слева" if a == b else ""))
        return a, b

    def copy_next(self, side):
        source = self.state["pointers"][side]
        element_id = self.state["arrays"][side][source]
        target = len(self.state["arrays"]["result"])
        self.state["arrays"]["result"].append(element_id)
        self.state["pointers"][side] += 1
        self.state["writes"] += 1
        self.state["nodes"][self.state["active_node"]]["ids"].append(element_id)
        self.state["selected"] = {self.source_node(side): [source], self.state["active_node"]: [target]}
        self.state["selection_kind"] = "copy"
        self.record("merge_copy", {"from": side, "source_index": source,
                                  "target_index": target, "element_id": element_id},
                    f"Поднимаем {self.original_values[element_id]} в общий массив")

    def commit(self):
        lo, hi = self.state["range"]
        result = self.state["arrays"]["result"]
        if len(result) != hi - lo:
            raise ValueError("Слияние ещё не завершено.")
        self.array.replace_range(lo, hi, [self.original_items[index] for index in result])
        self.state["phase"] = "merged"
        self.state["merges"] += 1
        self.state["nodes"][self.state["active_node"]]["status"] = "ready"
        for side in ("left", "right"):
            self.state["nodes"][self.source_node(side)]["status"] = "collapsed"
        self.state["selected"] = {}
        self.record("merge_commit", {"range": [lo, hi]},
                    f"Часть {self.numbers(result)} собрана")

    def finish(self):
        self.state.update({
            "arrays": {"left": [], "right": [], "result": []},
            "pointers": {"left": 0, "right": 0},
            "range": [0, len(self.original_values)], "middle": None,
            "depth": 0, "phase": "done",
            "active_node": self.node_id(0, len(self.original_values)), "selected": {},
        })
        self.record("done", {}, "Готово! Массив отсортирован")
        return self.execution()

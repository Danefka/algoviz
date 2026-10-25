from copy import deepcopy
import json
import random
import unittest

from algoviz.core import build_execution, validate_execution
from algoviz.inputs.integer_array import MAX_ITEMS


class MergeSortTests(unittest.TestCase):
    def check_execution(self, values):
        original = list(values)
        trace = build_execution(values, "merge_sort")
        self.assertEqual(values, original)
        self.assertEqual(trace["result"]["values"], sorted(values))
        expected_ids = sorted(range(len(values)), key=lambda index: values[index])
        self.assertEqual(trace["result"]["element_ids"], expected_ids)
        self.assertEqual(trace["result"]["merges"], max(0, len(values) - 1))
        previous = trace["initial_state"]
        for step in trace["steps"]:
            state = step["state_after"]
            kind, payload = step["type"], step["payload"]
            arrays = state["arrays"]
            self.assertEqual(sorted(state["element_ids"]), list(range(len(values))))
            self.assertEqual(state["values"], [values[i] for i in state["element_ids"]])
            self.assertEqual(state["comparisons"], previous["comparisons"] + (kind == "merge_compare"))
            self.assertEqual(state["writes"], previous["writes"] + (kind == "merge_copy"))
            self.assertEqual(state["merges"], previous["merges"] + (kind == "merge_commit"))
            for side in ("left", "right"):
                self.assertLessEqual(state["pointers"][side], len(arrays[side]))
                self.assertGreaterEqual(state["pointers"][side], 0)
            if kind in ("split", "merge_start"):
                lo, hi = state["range"]
                middle = state["middle"]
                self.assertEqual(arrays["left"], state["element_ids"][lo:middle])
                self.assertEqual(arrays["right"], state["element_ids"][middle:hi])
                self.assertEqual(arrays["result"], [])
                self.assertEqual(state["pointers"], {"left": 0, "right": 0})
                if kind == "merge_start":
                    for side in ("left", "right"):
                        self.assertEqual(arrays[side], sorted(arrays[side], key=lambda i: (values[i], i)))
            elif kind == "merge_compare":
                self.assertEqual(arrays, previous["arrays"])
                self.assertEqual(state["pointers"], previous["pointers"])
                self.assertEqual(payload, state["pointers"])
                for side in ("left", "right"):
                    self.assertLess(payload[side], len(arrays[side]))
            elif kind == "merge_copy":
                old_arrays = previous["arrays"]
                heads = {side: old_arrays[side][previous["pointers"][side]]
                         for side in ("left", "right")
                         if previous["pointers"][side] < len(old_arrays[side])}
                # Independent choice by value and original ID also checks stability.
                side = min(heads, key=lambda name: (values[heads[name]], heads[name]))
                self.assertEqual(payload["from"], side)
                self.assertEqual(payload["element_id"], heads[side])
                self.assertEqual(payload["source_index"], previous["pointers"][side])
                self.assertEqual(payload["target_index"], len(old_arrays["result"]))
                self.assertEqual(arrays["result"], old_arrays["result"] + [heads[side]])
                for name in ("left", "right"):
                    self.assertEqual(arrays[name], old_arrays[name])
                    self.assertEqual(state["pointers"][name], previous["pointers"][name] + (name == side))
            elif kind == "merge_commit":
                lo, hi = state["range"]
                ids = previous["element_ids"][:lo] + arrays["result"] + previous["element_ids"][hi:]
                self.assertEqual(state["element_ids"], ids)
                self.assertEqual(len(arrays["result"]), hi - lo)
                self.assertEqual(state["values"][lo:hi], sorted(previous["values"][lo:hi]))
            elif kind == "done":
                self.assertEqual(state["phase"], "done")
                self.assertEqual(arrays, {"left": [], "right": [], "result": []})
            else:
                self.fail(f"Unknown merge event: {kind}")
            if kind != "merge_commit":
                self.assertEqual(state["values"], previous["values"])
                self.assertEqual(state["element_ids"], previous["element_ids"])
            previous = state
        self.assertEqual(previous, trace["result"])
        validate_execution(json.loads(json.dumps(trace)))

    def test_edge_cases_and_duplicates(self):
        for values in ([], [4], [3, 1], [-99, 0, 99], [3, 3, 1, 3, 1],
                       [1, 2, 3, 4, 5], [5, 4, 3, 2, 1], [2] * MAX_ITEMS):
            with self.subTest(values=values):
                self.check_execution(values)

    def test_random_inputs_and_each_merge_decision(self):
        rng = random.Random(81)
        for _ in range(200):
            values = [rng.randint(-9, 9) for _ in range(rng.randint(0, MAX_ITEMS))]
            with self.subTest(values=values):
                self.check_execution(values)

    def test_snapshots_are_independent(self):
        trace = build_execution([3, 2, 1], "merge_sort")
        initial = deepcopy(trace["initial_state"])
        other = deepcopy(trace["steps"][1])
        trace["steps"][0]["state_after"]["arrays"]["left"].append(99)
        trace["steps"][0]["state_after"]["nodes"]["0:3"]["ids"].append(99)
        trace["result"]["values"][0] = 99
        self.assertEqual(trace["initial_state"], initial)
        self.assertEqual(trace["steps"][1], other)
        self.assertEqual(trace["steps"][-1]["state_after"]["values"], [1, 2, 3])

    def test_full_tree_is_divided_before_recursive_assembly(self):
        values = [8, 2, 6, 1, 4, 3, 7]
        trace = build_execution(values, "merge_sort")
        steps = trace["steps"]
        self.assertEqual([s["type"] for s in steps[:len(values) - 1]], ["split"] * (len(values) - 1))
        divided = steps[len(values) - 2]["state_after"]
        self.assertEqual(len(divided["nodes"]), 2 * len(values) - 1)
        leaves = [n for n in divided["nodes"].values() if n["status"] == "ready"]
        self.assertEqual(sorted(n["ids"][0] for n in leaves), list(range(len(values))))
        for step in steps:
            state = step["state_after"]
            if step["type"] == "merge_start":
                children = [n for n in state["nodes"].values() if n["parent"] == state["active_node"]]
                self.assertEqual(len(children), 2)
                self.assertTrue(all(n["status"] == "ready" for n in children))
            elif step["type"] == "merge_commit":
                self.assertEqual(state["nodes"][state["active_node"]]["ids"], state["arrays"]["result"])
        visible = {key: n for key, n in trace["result"]["nodes"].items() if n["status"] != "collapsed"}
        self.assertEqual(list(visible), ["0:7"])
        self.assertEqual(visible["0:7"]["ids"], trace["result"]["element_ids"])

    def test_rejects_invalid_input_and_tampered_buffer(self):
        for values in ([True], [1.5], [100], [0] * (MAX_ITEMS + 1)):
            with self.assertRaises(ValueError):
                build_execution(values, "merge_sort")
        trace = build_execution([2, 1], "merge_sort")
        copy_step = next(step for step in trace["steps"] if step["type"] == "merge_copy")
        copy_step["state_after"]["arrays"]["result"][0] = 99
        with self.assertRaises(ValueError):
            validate_execution(trace)

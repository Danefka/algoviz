"""Opt-in checks for stable sorting by comparing/swapping adjacent elements.

This mixin is NOT a TestCase: discovery only runs concrete subclasses that
explicitly select an algorithm. Other sorting strategies need their own checks.
"""
from copy import deepcopy
import json
import random

from algoviz.core import build_execution, validate_execution
from algoviz.inputs.integer_array import MAX_ITEMS


class AdjacentSwapSortingChecks:
    algorithm_id: str

    def check_execution(self, values):
        original = list(values)
        execution = build_execution(values, self.algorithm_id)
        self.assertEqual(values, original)
        expected_values = sorted(original)
        self.assertEqual(execution["result"]["values"], expected_values)
        state = deepcopy(execution["initial_state"])
        last_compared = None
        for step in execution["steps"]:
            kind = step["type"]
            indices = step["payload"]["indices"]
            if kind == "compare":
                i, j = indices
                self.assertEqual(j, i + 1)
                self.assertNotIn(i, state["sorted_indices"])
                self.assertNotIn(j, state["sorted_indices"])
                state["comparisons"] += 1
                last_compared = indices
            elif kind == "swap":
                self.assertEqual(indices, last_compared)
                i, j = indices
                self.assertGreater(state["values"][i], state["values"][j])
                for key in ("values", "element_ids"):
                    state[key][i], state[key][j] = state[key][j], state[key][i]
                state["swaps"] += 1
            elif kind == "mark_sorted":
                for index in indices:
                    self.assertEqual(state["values"][index], expected_values[index])
                state["sorted_indices"] = sorted(set(state["sorted_indices"]) | set(indices))
            elif kind == "done":
                self.assertEqual(state["values"], expected_values)
            else:
                self.fail(f"Unknown sorting event: {kind}")
            self.assertEqual(state, step["state_after"])
        self.assertEqual(state, execution["result"])
        self.assertEqual(state["sorted_indices"], list(range(len(original))))
        expected_ids = sorted(range(len(original)), key=lambda index: original[index])
        self.assertEqual(state["element_ids"], expected_ids)
        validate_execution(json.loads(json.dumps(execution)))

    def test_edge_cases_and_stable_duplicates(self):
        for values in ([], [4], [3, 1], [0, -99, 99], [2, 2, 1, 2],
                       [1, 2, 3], [6, 5, 4, 3, 2, 1]):
            with self.subTest(values=values):
                self.check_execution(values)

    def test_random_inputs_and_trace_replay(self):
        rng = random.Random(42)
        for _ in range(300):
            values = [rng.randint(-9, 9) for _ in range(rng.randint(0, MAX_ITEMS))]
            with self.subTest(values=values):
                self.check_execution(values)

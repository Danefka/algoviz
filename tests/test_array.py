from copy import deepcopy
import unittest

from algoviz.inputs.integer_array import MAX_ITEMS, parse_values
from algoviz.traces.array_trace import ArrayTrace


class ArrayInputTests(unittest.TestCase):
    def test_separators_brackets_and_signs(self):
        self.assertEqual(parse_values("[3, -1; +2 0]"), [3, -1, 2, 0])

    def test_invalid_inputs(self):
        for text in ("", "[]", "1.2, 3", "one", "100, 2", "-100", "[1, 2", "1e2"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_values(text)

    def test_limit(self):
        self.assertEqual(len(parse_values(",".join(["1"] * MAX_ITEMS))), MAX_ITEMS)
        with self.assertRaises(ValueError):
            parse_values(",".join(["1"] * (MAX_ITEMS + 1)))


class ArrayTraceTests(unittest.TestCase):
    def test_rejects_invalid_values(self):
        for values in ([True], [1.5], [100], [0] * (MAX_ITEMS + 1)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                ArrayTrace(values, "test")

    def test_swap_moves_identity_with_value_and_does_not_change_input(self):
        values = [3, 1, 3]
        trace = ArrayTrace(values, "test")
        self.assertEqual(trace.compare(0, 1), (3, 1))
        trace.swap(0, 1)
        self.assertEqual(values, [3, 1, 3])
        self.assertEqual(trace.values, [1, 3, 3])
        self.assertEqual(trace.array.element_ids, [1, 0, 2])
        self.assertEqual(trace.state["comparisons"], 1)
        self.assertEqual(trace.state["swaps"], 1)

    def test_snapshots_are_independent(self):
        trace = ArrayTrace([2, 1], "test")
        trace.compare(0, 1)
        initial = deepcopy(trace.initial_state)
        first_step = deepcopy(trace.steps[0])
        trace.swap(0, 1)
        execution = trace.finish()
        execution["result"]["values"][0] = 77
        execution["steps"][-1]["state_after"]["values"][0] = 88
        self.assertEqual(execution["initial_state"], initial)
        self.assertEqual(execution["steps"][0], first_step)


if __name__ == "__main__":
    unittest.main()

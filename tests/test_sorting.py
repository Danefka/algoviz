import unittest

from algoviz.core import build_execution
from tests.sorting_checks import AdjacentSwapSortingChecks


class BubbleSortTests(AdjacentSwapSortingChecks, unittest.TestCase):
    algorithm_id = "bubble_sort"

    def test_sorted_input_short_circuits(self):
        execution = build_execution([1, 2, 3, 4, 5], self.algorithm_id)
        self.assertEqual(execution["result"]["comparisons"], 4)
        self.assertEqual(execution["result"]["swaps"], 0)


if __name__ == "__main__":
    unittest.main()

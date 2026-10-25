import unittest
from algoviz.structures.array import Array
from algoviz.structures.item import Item


class ArrayModelTests(unittest.TestCase):
    def test_numbers_symbols_and_ids_use_the_same_model(self):
        for values in ([3, 1, 3], ["a", "b", "a"]):
            array = Array(values)
            array.swap(0, 1)
            self.assertEqual(array.values, [values[1], values[0], values[2]])
            self.assertEqual(array.element_ids, [1, 0, 2])
            array.replace_range(0, 2, [array.item(1), array.item(0)])
            self.assertEqual(array.values, values)

    def test_invalid_operations_are_atomic(self):
        array = Array([4, 2, 1])
        saved = array.snapshot()
        for i, j in ((-1, 1), (0, 3), (True, 1)):
            with self.assertRaises(IndexError):
                array.swap(i, j)
        with self.assertRaises(ValueError):
            array.replace_range(0, 2, [Item(2, 9), Item(1, 3)])
        with self.assertRaises(ValueError):
            array.replace_range(0, 2, [Item(0, 1)])
        self.assertEqual(array.snapshot(), saved)

    def test_nested_values_and_snapshots_do_not_alias(self):
        values = [{"name": [1]}]
        array = Array(values)
        values[0]["name"].append(2)
        snapshot = array.snapshot()
        snapshot["values"][0]["name"].append(3)
        self.assertEqual(array[0], {"name": [1]})


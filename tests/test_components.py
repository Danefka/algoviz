from copy import deepcopy
import unittest
from algoviz.renderers.components import array_view, compose, interpolate
from algoviz.structures.array import Array


class ComponentTests(unittest.TestCase):
    def test_reuse_array_view_with_independent_object_ids(self):
        source = Array([10, 20])
        picture = compose(array_view(source.snapshot(), "input", y=0),
                          array_view(source.snapshot(), "copy", y=2))
        self.assertEqual(len(picture.cells), 4)
        self.assertEqual(len({cell.key for cell in picture.cells}), 4)
        self.assertEqual({cell.object_id for cell in picture.cells}, {"input", "copy"})
        with self.assertRaises(ValueError):
            compose(array_view(source.snapshot(), "same"), array_view(source.snapshot(), "same"))

    def test_interpolation_preserves_snapshots_and_element_identity(self):
        source = Array([10, 20])
        before = compose(array_view(source.snapshot(), "input"))
        source.swap(0, 1)
        after = compose(array_view(source.snapshot(), "input", y=2))
        saved = deepcopy((before, after))
        self.assertEqual(interpolate(before, after, 0), before)
        self.assertEqual(interpolate(before, after, 1), after)
        middle = interpolate(before, after, 0.5)
        for cell in middle.cells:
            a = next(item for item in before.cells if item.key == cell.key)
            b = next(item for item in after.cells if item.key == cell.key)
            self.assertEqual(cell.value, a.value)
            self.assertAlmostEqual(cell.x, (a.x + b.x) / 2)
            self.assertAlmostEqual(cell.y, (a.y + b.y) / 2)
        self.assertEqual((before, after), saved)

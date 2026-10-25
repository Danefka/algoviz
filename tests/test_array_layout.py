from copy import deepcopy
import math
import random
import unittest

from algoviz.core import build_execution
from algoviz.playback import DURATIONS, Frame, Timeline
from algoviz.renderers.array_layout import swap_position, visual_cells


class ArrayLayoutTests(unittest.TestCase):
    def setUp(self):
        self.timeline = Timeline(build_execution([3, 1, 2, 1]))

    def test_cells_match_values_and_ids_after_any_seek(self):
        indices = list(range(self.timeline.total + 1))
        random.Random(41).shuffle(indices)
        for index in indices:
            self.timeline.seek(index)
            frame = self.timeline.frame()
            cells = sorted(visual_cells(frame), key=lambda cell: cell.slot)
            self.assertEqual([cell.value for cell in cells], frame.after["values"])
            self.assertEqual([cell.element_id for cell in cells], frame.after["element_ids"])

    def test_swap_uses_mirrored_lanes_and_resumes_at_same_position(self):
        self.timeline.seek(1)
        self.timeline.play()
        self.timeline.advance(DURATIONS["swap"] / 2)
        cells = visual_cells(self.timeline.frame())
        self.assertAlmostEqual(cells[0].slot, 0.5)
        self.assertAlmostEqual(cells[1].slot, 0.5)
        self.assertLess(cells[0].lift, 0)
        self.assertGreater(cells[1].lift, 0)
        self.timeline.pause()
        self.timeline.advance(500)
        self.assertEqual(visual_cells(self.timeline.frame()), cells)
        self.timeline.play()
        self.timeline.advance(DURATIONS["swap"] / 2)
        self.assertEqual(self.timeline.position, 2)
        self.assertEqual(self.timeline.state_at(2)["values"], [1, 3, 2, 1])

    def test_swap_rounds_the_turns_without_moving_other_cells(self):
        execution = self.timeline.execution
        before = execution["steps"][0]["state_after"]
        swap = execution["steps"][1]
        for progress in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1):
            with self.subTest(progress=progress):
                cells = visual_cells(Frame(before, swap["state_after"], swap, progress, 2))
                left, right = cells[:2]
                self.assertAlmostEqual(left.slot + right.slot, 1)
                self.assertAlmostEqual(left.lift, -right.lift)
                self.assertLessEqual(left.lift, 0)
                self.assertGreaterEqual(right.lift, 0)
                if progress == 0:
                    self.assertEqual((left.slot, left.lift), (0, 0))
                elif progress == 1:
                    self.assertEqual((left.slot, left.lift), (1, 0))
                elif progress in (0.25, 0.75):
                    # Vertical and horizontal motion overlap, rounding each turn.
                    self.assertTrue(0 < left.slot < 1)
                    self.assertTrue(-1 < left.lift < 0)
                self.assertEqual([(cell.slot, cell.lift) for cell in cells[2:]], [(2, 0), (3, 0)])

    def test_swap_paths_are_continuous_symmetric_and_do_not_overlap(self):
        for step in range(1001):
            progress = step / 1000
            left_x, left_y = swap_position(0, 1, progress)
            right_x, right_y = swap_position(1, 0, progress)
            self.assertAlmostEqual(left_x + right_x, 1)
            self.assertAlmostEqual(left_y + right_y, 0)
            # Conservative dimensions also cover the smallest supported Qt canvas.
            overlap_x = abs(left_x - right_x) * 1.05 < 1
            overlap_y = abs(left_y - right_y) * 0.95 < 1
            self.assertFalse(overlap_x and overlap_y, progress)
        for boundary in (0.15, 0.40, 0.60, 0.85):
            before = swap_position(0, 1, boundary - 0.000001)
            after = swap_position(0, 1, boundary + 0.000001)
            for a, b in zip(before, after):
                self.assertLess(abs(a - b), 0.00002)
        self.assertEqual(swap_position(2, 2, 0.5), (2, 0))

    def test_swap_has_smooth_acceleration_and_no_stops_between_turns(self):
        h = 0.00001
        for t in (0, 0.15, 0.40, 0.60, 0.85, 1):
            points = [swap_position(0, 1, t + offset * h) for offset in (-2, -1, 0, 1, 2)]
            for axis in (0, 1):
                a, b, c, d, e = (point[axis] for point in points)
                velocity_before, velocity_after = (c - b) / h, (d - c) / h
                acceleration_before, acceleration_after = (c - 2 * b + a) / h ** 2, (e - 2 * d + c) / h ** 2
                self.assertAlmostEqual(velocity_before, velocity_after, delta=0.002)
                self.assertAlmostEqual(acceleration_before, acceleration_after, delta=0.04)
                if t in (0, 1):
                    self.assertAlmostEqual(velocity_before, 0, delta=0.001)
                    self.assertAlmostEqual(velocity_after, 0, delta=0.001)
        for step in range(1, 100):
            t = step / 100
            before, after = swap_position(0, 1, t - h), swap_position(0, 1, t + h)
            speed = math.hypot(*(b - a for a, b in zip(before, after))) / (2 * h)
            self.assertGreater(speed, 0.01)

    def test_completed_sort_marks_all_cells_sorted(self):
        self.timeline.play()
        self.timeline.advance(1000)
        self.assertTrue(all(cell.role == "sorted" for cell in visual_cells(self.timeline.frame())))

    def test_compare_highlights_only_compared_items(self):
        self.timeline.forward()
        cells = visual_cells(self.timeline.frame())
        self.assertEqual([cell.role for cell in cells], ["compare", "compare", "normal", "normal"])

    def test_random_playback_preserves_trace_and_stable_ids(self):
        rng = random.Random(42)
        for _ in range(80):
            values = [rng.randint(-5, 5) for _ in range(rng.randint(0, 12))]
            execution = build_execution(values)
            saved = deepcopy(execution)
            timeline = Timeline(execution)
            timeline.set_speed(rng.choice([0.5, 1, 2, 4]))
            timeline.play()
            while timeline.running:
                timeline.advance(rng.uniform(0.05, 0.4))
                cells = visual_cells(timeline.frame())
                self.assertEqual(sorted(cell.element_id for cell in cells), list(range(len(values))))
                for cell in cells:
                    self.assertEqual(cell.value, values[cell.element_id])
                    self.assertTrue(math.isfinite(cell.slot))
                    self.assertLessEqual(abs(cell.lift), 1)
            self.assertEqual(timeline.frame().after["values"], sorted(values))
            self.assertEqual(execution, saved)


if __name__ == "__main__":
    unittest.main()

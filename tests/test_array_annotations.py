from copy import deepcopy
import unittest

from algoviz.playback import DURATIONS, Frame, Timeline
from algoviz.renderers.array_layout import array_geometry, swap_position, visual_cells, visual_guides
from algoviz.traces.array_trace import ArrayTrace
from tests.fixtures import build_annotation_example


class ArrayAnnotationTests(unittest.TestCase):
    def test_generic_focus_is_reusable_and_follows_ids_not_duplicate_values(self):
        trace = ArrayTrace([4, 2, 4, 1], "custom_algorithm")
        trace.set_focus(1, 4, pivot=2, pointers={"scan": 1, "next": 1})
        before = trace.capture()
        trace.swap(2, 3)
        after = trace.capture()
        frame = Frame(before, after, trace.steps[-1], 0.5, len(trace.steps))
        cells = visual_cells(frame)
        pivot = next(cell for cell in cells if cell.pivot)
        self.assertEqual(pivot.element_id, 2)
        self.assertEqual(pivot.value, 4)
        self.assertAlmostEqual(pivot.slot, 2.5)
        self.assertFalse(cells[0].pivot)
        self.assertLess(cells[0].opacity, 1)
        self.assertEqual(visual_guides(frame).pointers, ((1, "next · scan"),))
        self.assertEqual(visual_guides(frame).active_range, (1, 4))
        self.assertEqual(after["focus"]["pointers"], {"scan": 1, "next": 1})
        saved = deepcopy(trace.steps[0])
        trace.move_pointers(scan=2, next=None)
        self.assertEqual(trace.steps[0], saved)
        trace.clear_focus()
        self.assertEqual(trace.state["focus"], {"range": None, "pivot_id": None, "pointers": {}})

    def test_invalid_annotations_do_not_partially_mutate_state(self):
        trace = ArrayTrace([2, 1], "custom")
        for args, kwargs in (((-1, 2), {}), ((0, 3), {}), ((0, 0), {}), ((0, 2), {"pivot": 2}),
                             ((0, 2), {"pointers": {"i": True}}), ((0, 2), {"pointers": {"": 0}})):
            saved = trace.execution()
            with self.assertRaises(ValueError):
                trace.set_focus(*args, **kwargs)
            self.assertEqual(trace.execution(), saved)
        with self.assertRaises(ValueError):
            trace.move_pointers(i=0)
        trace.set_focus(0, 2, pointers={"i": 0})
        saved = trace.execution()
        with self.assertRaises(ValueError):
            trace.move_pointers(i=1, j=99)
        self.assertEqual(trace.execution(), saved)
        trace.move_pointers(i=0)
        trace.swap(0, 0)
        self.assertEqual(trace.execution(), saved)

    def test_seek_and_paused_pivot_swap_restore_annotations(self):
        execution = build_annotation_example([3, 2, 1, 2])
        saved = deepcopy(execution)
        timeline = Timeline(execution)
        for index in reversed(range(timeline.total + 1)):
            timeline.seek(index)
            frame = timeline.frame()
            focus = frame.after["focus"]
            self.assertEqual(visual_guides(frame).active_range,
                             tuple(focus["range"]) if focus["range"] is not None else None)
            cells = sorted(visual_cells(frame), key=lambda c: c.slot)
            self.assertEqual([c.element_id for c in cells], frame.after["element_ids"])
        index = next(i for i, s in enumerate(execution["steps"]) if s["type"] == "swap")
        timeline.seek(index)
        timeline.play()
        timeline.advance(DURATIONS["swap"] / 2)
        timeline.pause()
        before = (visual_cells(timeline.frame()), visual_guides(timeline.frame()))
        timeline.advance(100)
        self.assertEqual((visual_cells(timeline.frame()), visual_guides(timeline.frame())), before)
        self.assertEqual(len([cell for cell in before[0] if cell.pivot]), 1)
        timeline.play()
        timeline.advance(DURATIONS["swap"] / 2)
        self.assertEqual(timeline.position, index + 1)
        self.assertEqual(execution, saved)

    def test_long_swaps_clear_stationary_cells_and_guides_fit(self):
        for width, height in ((400, 260), (696, 300), (854, 320), (1100, 600)):
            for count in range(2, 13):
                geometry = array_geometry(width, height, count)
                self.assertGreaterEqual(geometry.range_y - 22, 0)
                self.assertLessEqual(geometry.pointer_y + 16, height)
                for target in {1, count // 2, count - 1}:
                    for frame in range(201):
                        positions = []
                        for start, end in ((0, target), (target, 0)):
                            slot, lift = swap_position(start, end, frame / 200)
                            positions.append((slot * geometry.stride, lift * geometry.lift_height))
                            y = geometry.center_y + lift * geometry.lift_height
                            self.assertGreaterEqual(y - geometry.cell_height / 2, 0)
                            self.assertLessEqual(y + geometry.cell_height / 2, height)
                        positions.extend((i * geometry.stride, 0) for i in range(count) if i not in (0, target))
                        for i in range(2):
                            for j in range(i + 1, len(positions)):
                                dx = abs(positions[i][0] - positions[j][0])
                                dy = abs(positions[i][1] - positions[j][1])
                                self.assertFalse(dx < geometry.cell_width - 1e-8 and dy < geometry.cell_height - 1e-8,
                                                 (width, height, count, target, frame))

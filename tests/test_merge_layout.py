from copy import deepcopy
import random
import unittest

from algoviz.core import build_execution
from algoviz.playback import DURATIONS, Frame, Timeline
from algoviz.renderers.merge_layout import CELL_HEIGHT, CELL_WIDTH, VIEW_TOP, visual_merge


class MergeLayoutTests(unittest.TestCase):
    def test_every_seek_restores_the_tree_and_stable_ids(self):
        trace = build_execution([3, 1, 2, 1], "merge_sort")
        timeline = Timeline(trace)
        positions = list(range(timeline.total + 1))
        random.Random(91).shuffle(positions)
        for position in positions:
            timeline.seek(position)
            state = timeline.frame().after
            picture = visual_merge(timeline.frame())
            for key, node in state["nodes"].items():
                actual = [c.element_id for c in picture.cells if c.lane == key and c.element_id is not None]
                self.assertEqual(actual, [] if node["status"] == "collapsed" else node["ids"])
            for cell in picture.cells:
                if cell.element_id is not None:
                    self.assertEqual(cell.value, trace["initial_state"]["values"][cell.element_id])

    def test_split_moves_halves_down_and_keeps_other_branches_still(self):
        trace = build_execution([7, 3, 5, 1], "merge_sort")
        before = trace["steps"][0]["state_after"]
        step = trace["steps"][1]
        pictures = {p: visual_merge(Frame(before, step["state_after"], step, p, 2))
                    for p in (0, 0.5, 1)}
        for p, picture in pictures.items():
            right = [c for c in picture.cells if c.lane == "2:4"]
            self.assertEqual(right, [c for c in pictures[0].cells if c.lane == "2:4"])
        new = [next(c for c in pictures[p].cells if c.lane == "0:1") for p in (0, 0.5, 1)]
        parent = next(c for c in pictures[0].cells if c.lane == "0:2" and c.index == 0)
        self.assertEqual((new[0].x, new[0].y), (parent.x, parent.y))
        self.assertEqual(new[0].opacity, 0)
        self.assertLess(new[0].y, new[1].y)
        self.assertLess(new[1].y, new[2].y)
        self.assertEqual(new[2].opacity, 1)

    def test_copy_moves_up_to_its_parent_and_resumes_without_a_jump(self):
        trace = build_execution([3, 1], "merge_sort")
        index = next(i for i, step in enumerate(trace["steps"]) if step["type"] == "merge_copy")
        step = trace["steps"][index]
        before = trace["steps"][index - 1]["state_after"]
        pictures = {p: visual_merge(Frame(before, step["state_after"], step, p, index + 1))
                    for p in (0, 0.25, 0.5, 0.75, 1)}
        source = next(c for c in pictures[0].cells if c.lane == "1:2")
        copies = {p: next(c for c in picture.cells if c.lane == "flight")
                  for p, picture in pictures.items() if p < 1}
        target = next(c for c in pictures[1].cells if c.lane == "0:2" and c.index == 0)
        self.assertEqual((copies[0].x, copies[0].y), (source.x, source.y))
        self.assertEqual(copies[0].element_id, source.element_id)
        self.assertGreater(copies[0].y, copies[0.5].y)
        self.assertGreater(copies[0.5].y, target.y)
        self.assertAlmostEqual(copies[0.5].x, (source.x + target.x) / 2)
        self.assertEqual(target.element_id, source.element_id)
        timeline = Timeline(trace)
        timeline.seek(index)
        timeline.play()
        timeline.advance(DURATIONS["merge_copy"] / 2)
        middle = visual_merge(timeline.frame())
        timeline.pause()
        timeline.advance(100)
        self.assertEqual(visual_merge(timeline.frame()), middle)
        timeline.play()
        timeline.advance(DURATIONS["merge_copy"] / 2)
        self.assertEqual(timeline.position, index + 1)

    def test_tree_fits_all_input_sizes_and_sibling_rows_do_not_overlap(self):
        for size in range(13):
            trace = build_execution(list(range(size, 0, -1)), "merge_sort")
            saved = deepcopy(trace)
            before = trace["initial_state"]
            viewport = None
            for number, step in enumerate(trace["steps"], 1):
                for progress in (0, 0.25, 0.5, 0.75, 1):
                    picture = visual_merge(Frame(before, step["state_after"], step, progress, number))
                    viewport = viewport or (picture.width, picture.height)
                    self.assertEqual((picture.width, picture.height), viewport)
                    keys = [cell.key for cell in picture.cells]
                    self.assertEqual(len(keys), len(set(keys)))
                    for cell in picture.cells:
                        self.assertLessEqual(abs(cell.x) + CELL_WIDTH / 2, picture.width / 2)
                        self.assertGreaterEqual(cell.y - CELL_HEIGHT / 2, VIEW_TOP)
                        self.assertLessEqual(cell.y + CELL_HEIGHT / 2, VIEW_TOP + picture.height)
                    if progress == 1:
                        for i, a in enumerate(picture.cells):
                            for b in picture.cells[i + 1:]:
                                self.assertTrue(abs(a.x - b.x) >= CELL_WIDTH or abs(a.y - b.y) >= CELL_HEIGHT)
                before = step["state_after"]
            self.assertEqual(trace, saved)

    def test_all_step_boundaries_are_visually_continuous(self):
        for values in ([2, 1], [7, 3, 5, 1, 3]):
            trace = build_execution(values, "merge_sort")
            before = trace["initial_state"]
            for number, step in enumerate(trace["steps"], 1):
                start = visual_merge(Frame(before, step["state_after"], step, 0, number))
                previous = visual_merge(Frame(before, before, None, 1, number - 1))
                # Zero-opacity incoming objects must not change the visible starting frame.
                visible = lambda p: {c.key: (c.element_id, c.x, c.y, c.opacity, c.color)
                                     for c in p.cells if c.opacity > 0}
                self.assertEqual(visible(start), visible(previous), step["type"])
                end = visual_merge(Frame(before, step["state_after"], step, 1, number))
                exact = visual_merge(Frame(step["state_after"], step["state_after"], step, 1, number))
                self.assertEqual(end, exact)
                before = step["state_after"]


if __name__ == "__main__":
    unittest.main()

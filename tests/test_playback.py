from copy import deepcopy
import random
import unittest

from algoviz.playback import Timeline
from tests.fixtures import build_history_example


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.execution = build_history_example([3, 1, 2])
        self.timeline = Timeline(self.execution)

    def test_every_seek_restores_all_objects_from_one_snapshot(self):
        indices = list(range(self.timeline.total + 1))
        random.Random(41).shuffle(indices)
        for index in indices:
            self.timeline.seek(index)
            frame = self.timeline.frame()
            expected = (self.execution["initial_state"] if index == 0
                        else self.execution["steps"][index - 1]["state_after"])
            self.assertEqual(frame.before, expected)
            self.assertEqual(frame.after, expected)
            items = frame.after["storage"]["items"]
            current_id = items[-1]["id"] if items else None
            self.assertEqual(frame.after["cursor"]["current_id"], current_id)
            self.assertFalse(self.timeline.running)

    def test_pause_and_resume_halfway_through_custom_step(self):
        # "visit" has no entry in DURATIONS: new events use the default 0.6 s.
        self.timeline.seek(1)
        self.timeline.play()
        self.timeline.advance(0.3)
        middle = self.timeline.frame()
        self.assertAlmostEqual(middle.progress, 0.5)
        self.assertEqual(middle.before, self.execution["steps"][0]["state_after"])
        self.assertEqual(middle.after, self.execution["steps"][1]["state_after"])
        self.timeline.pause()
        self.timeline.advance(500)
        self.assertEqual(self.timeline.frame(), middle)
        self.timeline.play()
        self.timeline.advance(0.3)
        self.assertEqual(self.timeline.position, 2)

    def test_step_buttons_from_mid_animation(self):
        self.timeline.seek(1)
        self.timeline.play()
        self.timeline.advance(0.2)
        self.timeline.backward()
        self.assertEqual(self.timeline.position, 1)
        self.assertFalse(self.timeline.in_transition)
        self.timeline.backward()
        self.assertEqual(self.timeline.position, 0)
        self.timeline.seek(1)
        self.timeline.play()
        self.timeline.advance(0.2)
        self.timeline.forward()
        self.assertEqual(self.timeline.position, 2)
        self.assertFalse(self.timeline.running)

    def test_speed_change_keeps_current_position(self):
        self.timeline.play()
        self.timeline.advance(0.1)
        before = self.timeline.frame()
        self.timeline.set_speed(2)
        self.assertEqual(self.timeline.frame(), before)
        self.timeline.advance(0.1)
        self.assertAlmostEqual(self.timeline.frame().progress, 0.5)

    def test_completion_and_replay(self):
        self.timeline.play()
        self.timeline.advance(1000)
        self.assertEqual(self.timeline.position, self.timeline.total)
        self.assertEqual(self.timeline.frame().after, self.execution["result"])
        self.assertFalse(self.timeline.running)
        self.timeline.play()
        self.assertEqual(self.timeline.position, 0)
        self.assertEqual(self.timeline.elapsed, 0)
        self.assertTrue(self.timeline.running)

    def test_seek_clamps_and_clears_partial_motion(self):
        self.timeline.play()
        self.timeline.advance(0.2)
        self.timeline.seek(-100)
        self.assertEqual(self.timeline.position, 0)
        self.assertEqual(self.timeline.elapsed, 0)
        self.timeline.seek(10000)
        self.assertEqual(self.timeline.position, self.timeline.total)
        self.assertFalse(self.timeline.in_transition)

    def test_playback_does_not_modify_the_history(self):
        original = deepcopy(self.execution)
        self.timeline.play()
        self.timeline.advance(0.3)
        self.timeline.pause()
        self.timeline.backward()
        self.timeline.forward()
        self.timeline.set_speed(4)
        self.timeline.play()
        self.timeline.advance(1000)
        self.assertEqual(self.execution, original)

    def test_empty_history_stays_at_initial_state(self):
        timeline = Timeline(build_history_example([]))
        timeline.play()
        timeline.advance(100)
        timeline.forward()
        timeline.backward()
        self.assertFalse(timeline.running)
        self.assertEqual(timeline.position, 0)
        self.assertIsNone(timeline.frame().step)
        self.assertEqual(timeline.frame().after, timeline.execution["initial_state"])

    def test_rejects_invalid_clock_and_speed(self):
        for speed in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.timeline.set_speed(speed)
        for seconds in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.timeline.advance(seconds)


if __name__ == "__main__":
    unittest.main()

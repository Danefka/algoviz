"""Exercise the actual scene, worker protocol and MP4 encoder when installed."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from algoviz.core import build_execution
from algoviz.worker import EVENT_PREFIX


@unittest.skipUnless(importlib.util.find_spec("manim"), "Manim is not installed")
class ExportTests(unittest.TestCase):
    def test_array_annotations_export_without_a_catalog_entry(self):
        import av

        root = Path(__file__).resolve().parents[1]
        script = '''import json, sys
from manim import tempconfig
from algoviz.renderers.manim_array import ArrayScene
from tests.fixtures import build_annotation_example
execution = build_annotation_example([3, 2, 1])
progress = []
with tempconfig({"renderer": "cairo", "media_dir": sys.argv[1], "output_file": "annotations",
                 "pixel_width": 640, "pixel_height": 360, "frame_rate": 10,
                 "frame_width": 14.2222222222, "frame_height": 8,
                 "format": "mp4", "write_to_movie": True, "save_last_frame": False,
                 "preview": False, "disable_caching": True, "progress_bar": "none",
                 "verbosity": "WARNING"}):
    scene = ArrayScene(execution, "Annotations", on_progress=lambda current, total: progress.append(current),
                       show_title=False, show_indices=False, show_counters=False, show_comments=False)
    scene.render()
    path = str(scene.renderer.file_writer.movie_file_path)
print(json.dumps({"path": path, "progress": progress, "total": len(execution["steps"])}))
'''
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-c", script, folder], cwd=root,
                                    capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(data["progress"], list(range(1, data["total"] + 1)))
            blue_visible = False
            frames = 0
            with av.open(data["path"]) as container:
                for frame in container.decode(video=0):
                    frames += 1
                    rgb = frame.to_ndarray(format="rgb24").astype("int16")
                    blue = (rgb[:, :, 2] > rgb[:, :, 0] + 30) & (rgb[:, :, 2] > rgb[:, :, 1] + 15)
                    blue_visible |= int(blue.sum()) > 10
            self.assertGreater(frames, 1)
            self.assertTrue(blue_visible, "Pivot/range/pointers must remain visible with all text options off")

    def test_all_scenes_produce_decodable_video(self):
        import av

        root = Path(__file__).resolve().parents[1]
        cases = (
            ("bubble_sort", None),
            ("bubble_sort", {"show_comments": False}),
            ("merge_sort", None),
            ("merge_sort", {"show_title": False, "show_indices": False,
                            "show_counters": False, "show_comments": False}),
        )
        for algorithm, options in cases:
            with self.subTest(algorithm=algorithm, options=options), tempfile.TemporaryDirectory() as folder:
                job = Path(folder) / "job.json"
                execution = build_execution([2, 1], algorithm)
                payload = {"execution": execution, "quality": "preview"}
                # Exercise old jobs without options and videos with comments disabled.
                if options is not None:
                    payload["options"] = options
                job.write_text(json.dumps(payload), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, "-u", str(root / "main.py"), "--render", str(job)],
                    cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                events = [json.loads(line[len(EVENT_PREFIX):])
                          for line in result.stdout.splitlines() if line.startswith(EVENT_PREFIX)]
                self.assertEqual(events[-1]["kind"], "complete", events)
                progress = [event["current"] for event in events if event["kind"] == "progress"]
                self.assertEqual(progress, list(range(1, len(execution["steps"]) + 1)))
                video = Path(events[-1]["path"])
                self.assertTrue(video.is_file())
                with av.open(str(video)) as container:
                    frames = list(container.decode(video=0))
                self.assertGreater(len(frames), 1)
                self.assertEqual((frames[0].width, frames[0].height), (854, 480))


if __name__ == "__main__":
    unittest.main()

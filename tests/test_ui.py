"""Qt integration checks; explicit skips when PySide6 is unavailable."""
import hashlib
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from algoviz.playback import DURATIONS

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HAS_QT = importlib.util.find_spec("PySide6") is not None

if HAS_QT:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLabel
    from algoviz.registry import get_algorithm, list_algorithms
    from algoviz.ui import MainWindow
    from algoviz.ui.home import HomePage


@unittest.skipUnless(HAS_QT, "PySide6 is not installed; real Qt integration not run")
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_home_lists_catalog_and_opens_the_selected_algorithm(self):
        window = self.window
        self.assertIs(window.stack.currentWidget(), window.home)
        self.assertEqual(set(window.home.buttons), {entry.id for entry in list_algorithms()})
        self.assertEqual(set(window.home.category_buttons), {entry.category for entry in list_algorithms()})
        self.assertIs(window.home.category_stack.currentWidget(), window.home.root_page)
        self.assertEqual([label.text() for label in window.home.findChildren(QLabel) if label.isVisible()],
                         ["Алгоритмы"])
        category = get_algorithm("merge_sort").category
        window.home.category_buttons[category].click()
        self.assertEqual(window.home.title.text(), category)
        window.home.buttons["merge_sort"].click()
        page = window.stack.currentWidget()
        self.assertEqual(page.execution["algorithm"], "merge_sort")
        self.assertTrue(page.stats.isHidden())
        self.assertFalse(window.export_dialog.isVisible())
        page.home_button.click()
        self.assertIs(window.stack.currentWidget(), window.home)
        self.assertIs(window.home.category_stack.currentWidget(), window.home.category_pages[category])
        window.home.back_button.click()
        self.assertIs(window.home.category_stack.currentWidget(), window.home.root_page)
        self.assertTrue(window.home.back_button.isHidden())

    def test_new_category_is_created_from_algorithm_metadata(self):
        base = replace(list_algorithms()[0], category="Исходная категория")
        extra = replace(base, id="test_search", title="Тестовый поиск", category="Поиск")
        with patch("algoviz.ui.home.list_algorithms", return_value=(base, extra)):
            home = HomePage()
        try:
            home.show()
            self.app.processEvents()
            selected = []
            home.algorithm_selected.connect(selected.append)
            home.category_buttons["Поиск"].click()
            self.app.processEvents()
            self.assertTrue(home.buttons[extra.id].isVisible())
            self.assertFalse(home.buttons[base.id].isVisible())
            home.buttons[extra.id].click()
            self.assertEqual(selected, [extra.id])
            home.back_button.click()
            self.assertEqual(home.title.text(), "Алгоритмы")
            self.assertTrue(home.category_buttons["Поиск"].isVisible())
        finally:
            home.close()
            home.deleteLater()
            self.app.processEvents()

    def test_return_to_menu_pauses_and_preserves_position(self):
        page = self.window.open_algorithm("bubble_sort")
        page.toggle_playback()
        page.timeline.advance(0.3)
        before = page.timeline.frame()
        page.home_button.click()
        self.assertFalse(page.timer.isActive())
        self.assertFalse(page.timeline.running)
        self.assertIs(self.window.stack.currentWidget(), self.window.home)
        self.assertIs(self.window.open_algorithm("bubble_sort"), page)
        self.assertEqual(page.timeline.frame(), before)

    def test_algorithm_pages_have_independent_state(self):
        bubble = self.window.open_algorithm("bubble_sort")
        bubble.input.setText("3, 2, 1")
        bubble.seek_to(2)
        merge = self.window.open_algorithm("merge_sort")
        merge.input.setText("5, 4")
        merge.seek_to(merge.timeline.total)
        self.assertEqual(merge.timeline.frame().after["values"], [4, 5])
        self.assertEqual(bubble.timeline.position, 2)
        self.assertEqual(bubble.execution["initial_state"]["values"], [3, 2, 1])

    def test_preview_does_not_start_manim_or_a_process(self):
        page = self.window.open_algorithm("bubble_sort")
        with patch("algoviz.ui.export_dialog.QProcess") as process:
            page.play_button.click()
            self.assertTrue(page.timeline.running)
            page.play_button.click()
            page.next_button.click()
            self.assertEqual(page.timeline.position, 1)
            page.previous_button.click()
            self.assertEqual(page.timeline.position, 0)
            page.seek.setValue(page.timeline.total)
            self.assertEqual(page.timeline.frame().after, page.execution["result"])
            process.assert_not_called()
        self.assertNotIn("manim", sys.modules)

    def test_invalid_input_stops_playback_and_recovers(self):
        page = self.window.open_algorithm("bubble_sort")
        page.toggle_playback()
        page.input.setText("1, wrong")
        self.assertFalse(page.timer.isActive())
        self.assertFalse(page.play_button.isEnabled())
        self.assertFalse(page.export_action.isEnabled())
        page.input.setText("-2, -2, 0")
        self.assertTrue(page.play_button.isEnabled())
        self.assertEqual(page.timeline.position, 0)

    def test_canvas_paints_paused_mid_swap(self):
        page = self.window.open_algorithm("bubble_sort")
        page.input.setText("2, 1")
        page.seek_to(1)
        page.toggle_playback()
        page.timeline.advance(DURATIONS["swap"] / 2)
        page.pause()
        before = page.timeline.frame()
        self.assertFalse(page.canvas.grab().toImage().isNull())
        self.window.resize(1100, 750)
        self.app.processEvents()
        self.assertEqual(page.timeline.frame(), before)
        self.assertEqual([cell.slot for cell in page.canvas.cells], [0.5, 0.5])

    def test_speed_slider_changes_live_speed_without_resetting_position(self):
        page = self.window.open_algorithm("bubble_sort")
        page.input.setText("2, 1")
        page.seek_to(1)
        page.timeline.play()
        page.timeline.advance(0.1)
        before = page.timeline.frame()
        menu = page.more.menu()
        menu.popup(page.more.mapToGlobal(page.more.rect().bottomLeft()))
        self.app.processEvents()
        try:
            self.assertTrue(page.speed_slider.isVisible())
            page.speed_slider.setValue(3)
            self.assertEqual(page.playback_speed, 2)
            self.assertEqual(page.timeline.speed, 2)
            self.assertEqual(page.speed_value.text(), "2×")
            self.assertEqual(page.timeline.frame(), before)
            self.assertTrue(page.timeline.running)
            page.speed_slider.setFocus()
            QTest.keyClick(page.speed_slider, Qt.Key.Key_Right)
            self.assertEqual(page.timeline.speed, 4)
            self.assertEqual(page.speed_value.text(), "4×")
            self.assertTrue(menu.isVisible())
            QTest.mouseClick(page.speed_slider, Qt.MouseButton.LeftButton,
                             pos=QPoint(page.speed_slider.width() // 2, 16))
            self.assertEqual(page.timeline.speed, 1.5)
            self.assertEqual(page.speed_value.text(), "1,5×")
            self.assertEqual(page.timeline.frame(), before)
            QTest.mousePress(page.speed_slider, Qt.MouseButton.LeftButton, pos=QPoint(24, 16))
            end = QPoint(page.speed_slider.width() - 24, 16)
            QTest.mouseMove(page.speed_slider, end)
            QTest.mouseRelease(page.speed_slider, Qt.MouseButton.LeftButton, pos=end)
            self.assertEqual(page.timeline.speed, 4)
            self.assertFalse(page.speed_slider.grab().toImage().isNull())
        finally:
            menu.hide()
        page.input.setText("4, 1")
        self.assertEqual(page.timeline.speed, 4)
        for value, expected in enumerate((0.5, 1, 1.5, 2, 4)):
            page.speed_slider.setValue(value)
            self.assertEqual(page.timeline.speed, expected)

    def test_indices_toggle_repaints_without_changing_a_paused_swap(self):
        page = self.window.open_algorithm("bubble_sort")
        page.input.setText("2, 1")
        page.seek_to(1)
        page.timeline.play()
        page.timeline.advance(DURATIONS["swap"] / 2)
        page.pause()
        before = page.timeline.frame()
        cells = list(page.canvas.cells)
        with_indices = page.canvas.grab().toImage()
        page.indices_action.trigger()
        self.assertFalse(page.canvas.show_indices)
        without_indices = page.canvas.grab().toImage()
        self.assertFalse(with_indices == without_indices)
        self.assertEqual(page.timeline.frame(), before)
        self.assertEqual(page.canvas.cells, cells)
        page.home_button.click()
        self.assertIs(self.window.open_algorithm("bubble_sort"), page)
        self.assertFalse(page.indices_action.isChecked())
        page.input.setText("3, 1")
        self.assertFalse(page.canvas.show_indices)
        other = self.window.open_algorithm("merge_sort")
        self.assertTrue(other.indices_action.isChecked())
        self.assertTrue(other.canvas.show_indices)
        page.indices_action.trigger()
        self.assertTrue(page.canvas.show_indices)

    def test_merge_sort_uses_one_canvas_and_keeps_a_copy_paused(self):
        page = self.window.open_algorithm("merge_sort")
        self.assertEqual(page.algorithm.visualization, "merge_tree")
        index = next(i for i, step in enumerate(page.execution["steps"])
                     if step["type"] == "merge_copy")
        page.seek_to(index)
        page.timeline.play()
        page.timeline.advance(DURATIONS["merge_copy"] / 2)
        page.pause()
        picture = page.canvas.picture
        self.assertIn("flight", {cell.lane for cell in picture.cells})
        self.assertIn("0:4", {cell.lane for cell in picture.cells})
        self.assertEqual(len(picture.edges), 6)
        self.assertFalse(page.canvas.grab().toImage().isNull())
        page.indices_action.trigger()
        self.assertFalse(page.canvas.show_indices)
        self.assertEqual(page.canvas.picture, picture)
        page.home_button.click()
        self.assertIs(self.window.open_algorithm("merge_sort"), page)
        self.assertEqual(page.canvas.picture, picture)
        page.seek_to(page.timeline.total)
        self.assertEqual(page.timeline.frame().after["values"], [1, 3, 5, 7])

    def test_comments_toggle_preserves_playback_and_survives_input_and_navigation(self):
        for algorithm in ("bubble_sort", "merge_sort"):
            with self.subTest(algorithm=algorithm):
                page = self.window.open_algorithm(algorithm)
                self.assertTrue(page.comments_action.isChecked())
                self.assertFalse(page.caption.isHidden())
                page.timeline.play()
                page.timeline.advance(0.2)
                before = page.timeline.frame()
                page.comments_action.trigger()
                page.refresh()
                self.assertTrue(page.caption.isHidden())
                self.assertEqual(page.timeline.frame(), before)
                self.assertTrue(page.timeline.running)
                page.pause()
                page.step_forward()
                self.assertTrue(page.caption.isHidden())
                page.home_button.click()
                self.assertIs(self.window.open_algorithm(algorithm), page)
                page.input.setText("5, 1")
                self.assertTrue(page.caption.isHidden())
                page.seek_to(page.timeline.total)
                page.comments_action.trigger()
                self.assertFalse(page.caption.isHidden())
                self.assertEqual(page.caption.text(), page.execution["steps"][-1]["description"])
                self.assertEqual(page.timeline.position, page.timeline.total)

    def test_array_annotations_survive_pause_and_view_toggles(self):
        from algoviz.renderers.qt_array import ArrayCanvas
        from tests.fixtures import build_annotation_example
        entry = replace(get_algorithm("bubble_sort"), id="annotation_example",
                        example="3, 2, 1", build=build_annotation_example)
        with patch.dict("algoviz.registry.ALGORITHMS", {entry.id: entry}):
            page = self.window.open_algorithm("annotation_example")
            self.assertIsInstance(page.canvas, ArrayCanvas)
            page.input.setText("3, 2, 1")
            index = next(i for i, step in enumerate(page.execution["steps"])
                         if step["type"] == "swap")
            page.seek_to(index)
            page.timeline.play()
            page.timeline.advance(DURATIONS["swap"] / 2)
            page.pause()
            frame = page.timeline.frame()
            cells, guides = list(page.canvas.cells), page.canvas.guides
            self.assertEqual(guides.active_range, (0, 3))
            self.assertEqual(guides.pivot_value, 1)
            self.assertEqual(len([cell for cell in cells if cell.pivot]), 1)
            page.indices_action.trigger()
            page.comments_action.trigger()
            self.window.resize(760, 560)
            self.app.processEvents()
            self.assertFalse(page.canvas.grab().toImage().isNull())
            self.assertEqual(page.timeline.frame(), frame)
            self.assertEqual(page.canvas.cells, cells)
            self.assertEqual(page.canvas.guides, guides)
            page.home_button.click()
            self.assertIs(self.window.open_algorithm("annotation_example"), page)
            self.assertEqual(page.timeline.frame(), frame)
            page.seek_to(page.timeline.total)
            self.assertIsNone(page.canvas.guides.active_range)
            self.assertEqual(page.canvas.guides.pointers, ())

    def test_export_captures_trace_and_missing_manim_does_not_break_preview(self):
        page = self.window.open_algorithm("merge_sort")
        dialog = self.window.export_dialog
        dialog.capture(page.execution)
        captured = dialog.execution
        page.input.setText("9, 2")
        self.assertNotEqual(dialog.execution, page.execution)
        with patch("algoviz.ui.export_dialog.importlib.util.find_spec", return_value=None), \
                patch("algoviz.ui.export_dialog.QMessageBox.information") as message, \
                patch.object(dialog, "save_target") as picker:
            dialog.export_video()
            message.assert_called_once()
            picker.assert_not_called()
        self.assertIs(dialog.execution, captured)
        self.assertTrue(page.play_button.isEnabled())

    def test_cached_export_copies_file_without_manim(self):
        page = self.window.open_algorithm("merge_sort")
        dialog = self.window.export_dialog
        dialog.capture(page.execution)
        content = json.dumps({"execution": dialog.execution, "quality": dialog.quality.currentData(),
                              "options": {"show_title": True, "show_indices": True, "show_counters": True,
                                          "show_comments": True}},
                             ensure_ascii=False, sort_keys=True)
        key = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            source, destination = Path(folder) / "source.mp4", Path(folder) / "output.mp4"
            source.write_bytes(b"test-only-video-placeholder")
            dialog.video_cache[key] = source
            with patch.object(dialog, "save_target", return_value=str(destination)), \
                    patch("algoviz.ui.export_dialog.QProcess") as process, \
                    patch("algoviz.ui.export_dialog.importlib.util.find_spec") as dependency:
                dialog.export_video()
                self.assertEqual(source.read_bytes(), destination.read_bytes())
                process.assert_not_called()
                dependency.assert_not_called()
            for checkbox in dialog.option_checks.values():
                checkbox.setChecked(False)
                with patch("algoviz.ui.export_dialog.importlib.util.find_spec", return_value=None), \
                        patch("algoviz.ui.export_dialog.QMessageBox.information") as message, \
                        patch.object(dialog, "save_target") as picker:
                    dialog.export_video()
                    message.assert_called_once()
                    picker.assert_not_called()
                checkbox.setChecked(True)


if __name__ == "__main__":
    unittest.main()

from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from algoviz.core import build_execution, validate_execution
from algoviz.registry import ALGORITHMS, get_algorithm, list_algorithms


class RegistryTests(unittest.TestCase):
    def discover_in_copy(self, files, script="import algoviz.registry"):
        # Fresh interpreter and real files: exercise startup discovery, not a mocked catalog.
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "algoviz"
            shutil.copytree(root / "algoviz", target, ignore=shutil.ignore_patterns("__pycache__"))
            for filename, source in files.items():
                path = target / "algorithms" / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
            return subprocess.run([sys.executable, "-c", script], cwd=folder,
                                  capture_output=True, text=True, encoding="utf-8", timeout=10)

    def test_new_file_is_discovered_at_startup_and_can_execute(self):
        source = '''from dataclasses import replace
from algoviz.algorithms.sorting.bubble_sort import ALGORITHM as BASE
def build(values):
    trace = BASE.build(values)
    trace["algorithm"] = "automatic_test"
    return trace
ALGORITHM = replace(BASE, id="automatic_test", build=build)
'''
        script = '''from algoviz.registry import list_algorithms
from algoviz.core import build_execution, validate_execution
assert "automatic_test" in {entry.id for entry in list_algorithms()}
trace = build_execution([3, 1, 2], "automatic_test")
assert trace["result"]["values"] == [1, 2, 3]
validate_execution(trace)
'''
        for location in ("automatic_test.py", "sorting/automatic_test.py", "sorting/extra/automatic_test.py"):
            with self.subTest(location=location):
                files = {location: source}
                if "extra/" in location:
                    files["sorting/extra/__init__.py"] = ""
                result = self.discover_in_copy(files, script)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_private_modules_packages_and_files_without_cards_are_ignored(self):
        files = {
            "_private.py": "raise RuntimeError('private module imported')",
            "_private_package/__init__.py": "raise RuntimeError('private package imported')",
            "sorting/_private/__init__.py": "raise RuntimeError('nested private package imported')",
            "helper.py": "HELPER = 1",
        }
        script = ('from algoviz.registry import ALGORITHMS; '
                  f'assert set(ALGORITHMS) == {set(ALGORITHMS)!r}')
        result = self.discover_in_copy(files, script)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_id_reports_both_modules(self):
        result = self.discover_in_copy({"duplicate.py": "from .sorting.bubble_sort import ALGORITHM"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Повторяющийся ID", result.stderr)
        self.assertIn("algoviz.algorithms.sorting.bubble_sort", result.stderr)
        self.assertIn("algoviz.algorithms.duplicate", result.stderr)

    def test_invalid_card_reports_its_module(self):
        result = self.discover_in_copy({"invalid_card.py": "ALGORITHM = {}"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("algoviz.algorithms.invalid_card", result.stderr)
        self.assertIn("ALGORITHM должен быть объектом Algorithm", result.stderr)

    def test_invalid_id_and_build_are_rejected(self):
        for field in ('id=""', 'build=None', 'input_type="missing"', 'visualization="missing"'):
            with self.subTest(field=field):
                source = ("from dataclasses import replace\n"
                          "from .sorting.bubble_sort import ALGORITHM as BASE\n"
                          f"ALGORITHM = replace(BASE, {field})\n")
                result = self.discover_in_copy({"invalid_fields.py": source})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("algoviz.algorithms.invalid_fields", result.stderr)

    def test_import_error_reports_its_module_and_original_cause(self):
        result = self.discover_in_copy({"broken.py": "raise RuntimeError('example failure')"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Не удалось загрузить алгоритм из algoviz.algorithms.broken", result.stderr)
        self.assertIn("example failure", result.stderr)

    def test_package_import_error_reports_its_name_and_cause(self):
        result = self.discover_in_copy({"broken/__init__.py": "raise RuntimeError('package failure')"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Не удалось загрузить пакет algoviz.algorithms.broken", result.stderr)
        self.assertIn("package failure", result.stderr)

    def test_a_new_entry_works_without_changing_core_or_worker(self):
        base = get_algorithm("bubble_sort")

        def build(values):
            trace = base.build(values)
            trace["algorithm"] = "test_algorithm"
            return trace

        entry = replace(base, id="test_algorithm", title="Test algorithm", build=build)
        with patch.dict(ALGORITHMS, {entry.id: entry}):
            trace = build_execution([3, 1, 2], entry.id)
            self.assertIn(entry, list_algorithms())
            self.assertEqual(trace["result"]["values"], [1, 2, 3])
            validate_execution(trace)

    def test_catalog_does_not_import_rendering_libraries(self):
        script = ('import sys; import algoviz.registry; import algoviz.inputs.registry; import algoviz.renderers.registry; '
                  'assert not any(name.startswith(("PySide6", "manim")) for name in sys.modules)')
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                                cwd=Path(__file__).resolve().parents[1], timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

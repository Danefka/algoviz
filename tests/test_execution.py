from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from algoviz.algorithms.spec import Algorithm
from algoviz.core import build_execution, validate_execution
from algoviz.registry import ALGORITHMS, list_algorithms
from algoviz.inputs.registry import INPUTS, InputSpec, get_input
from tests.fixtures import build_history_example


class ExecutionTests(unittest.TestCase):
    def check_example_contract(self, algorithm):
        input_spec = get_input(algorithm.input_type)
        data = input_spec.parse(algorithm.example)
        original = deepcopy(data)
        trace = build_execution(data, algorithm.id)
        self.assertEqual(data, original)
        self.assertEqual(trace["algorithm"], algorithm.id)
        self.assertEqual(trace["input"], data)
        self.assertEqual(trace["schema_version"], 2)
        self.assertEqual(trace["kind"], "algorithm")
        self.assertIsInstance(trace["initial_state"], dict)
        self.assertIsInstance(trace["steps"], list)
        for step in trace["steps"]:
            self.assertIsInstance(step["type"], str)
            self.assertIsInstance(step["payload"], dict)
            self.assertIsInstance(step["state_after"], dict)
            self.assertIsInstance(step["description"], str)
            self.assertIsInstance(step["line_id"], str)
        final = trace["steps"][-1]["state_after"] if trace["steps"] else trace["initial_state"]
        self.assertEqual(trace["result"], final)
        restored = json.loads(json.dumps(trace))
        self.assertEqual(restored, trace)
        validate_execution(restored)
        return trace

    def test_every_registered_example_obeys_the_execution_contract(self):
        # No assumptions about sorting, indices, or arrays.
        for algorithm in list_algorithms():
            with self.subTest(algorithm=algorithm.id):
                self.check_example_contract(algorithm)

    def test_non_array_algorithm_uses_its_own_input_and_state(self):
        input_spec = InputSpec(id="test_json", input_hint="JSON", parse=json.loads,
                               random_input=lambda: "[3, 1, 2]")
        algorithm = Algorithm(
            id="test_history", title="Test history", category="Tests",
            description="Synthetic test fixture", input_type=input_spec.id, visualization="array",
            example="[3, 1, 2]", build=build_history_example,
        )
        with patch.dict(INPUTS, {input_spec.id: input_spec}), \
                patch.dict(ALGORITHMS, {algorithm.id: algorithm}):
            trace = self.check_example_contract(algorithm)
            items = trace["result"]["storage"]["items"]
            self.assertEqual([item["value"] for item in items], [3, 1, 2])
            self.assertNotIn("values", trace["result"])
            self.assertEqual(trace["result"]["cursor"]["current_id"], "e2")

    def test_saved_examples_are_compatible(self):
        examples = Path(__file__).resolve().parents[1] / "examples"
        paths = sorted(examples.rglob("*.json"))
        self.assertTrue(paths, "Нет сохранённых примеров для проверки")
        for path in paths:
            with self.subTest(example=str(path.relative_to(examples))):
                validate_execution(json.loads(path.read_text(encoding="utf-8")))
        old = json.loads((examples / "sorting" / "bubble_sort.json").read_text(encoding="utf-8"))
        self.assertEqual(build_execution([3, 1, 2]), old)

    def test_rejects_tampered_trace(self):
        trace = build_execution([3, 1])
        trace["steps"][0]["payload"]["indices"] = [0, 99]
        with self.assertRaises(ValueError):
            validate_execution(trace)

    def test_wrong_algorithm_input_or_schema_is_rejected(self):
        for field, value in (("algorithm", "missing"), ("input", [2, 2]), ("schema_version", 1)):
            with self.subTest(field=field):
                trace = build_execution([2, 1])
                trace[field] = value
                with self.assertRaises(ValueError):
                    validate_execution(trace)


if __name__ == "__main__":
    unittest.main()

from copy import deepcopy


class Recorder:
    """Records the whole scenario, regardless of its number of structures."""
    def __init__(self, algorithm_id, input_data, snapshot, parameters=None):
        self.algorithm_id = algorithm_id
        self.input_data = deepcopy(input_data)
        self.parameters = deepcopy(parameters or {})
        self.snapshot = snapshot
        self.initial_state = deepcopy(snapshot())
        self.steps = []

    def record(self, kind, payload, description, line_id=None):
        self.steps.append({"type": kind, "payload": deepcopy(payload),
                           "description": description, "line_id": line_id or kind,
                           "state_after": deepcopy(self.snapshot())})

    def execution(self):
        return deepcopy({"schema_version": 2, "kind": "algorithm", "algorithm": self.algorithm_id,
                         "input": self.input_data, "parameters": self.parameters,
                         "initial_state": self.initial_state, "steps": self.steps,
                         "result": self.snapshot()})

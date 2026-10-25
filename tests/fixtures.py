"""Synthetic histories for infrastructure tests, not application plugins."""
from copy import deepcopy
from algoviz.traces.array_trace import ArrayTrace


def build_annotation_example(values):
    """A short UI/renderer fixture, not a sorting algorithm or application plugin."""
    trace = ArrayTrace(values, "annotation_example")
    trace.set_focus(0, len(values), pivot=len(values) - 1, pointers={"i": 0, "j": 0})
    trace.compare(0, len(values) - 1)
    trace.move_pointers(j=None)
    trace.swap(0, len(values) - 1, line_id="move_selected_element")
    trace.move_pointers(i=None)
    trace.clear_focus()
    trace.record("done", {"indices": []}, "Демонстрация аннотаций завершена")
    return trace.execution()


def build_history_example(values):
    """A cursor and visited items test opaque, synchronized scenario state."""
    state = {
        "cursor": {"storage_id": "storage", "current_id": None},
        "storage": {"items": []},
    }
    initial = deepcopy(state)
    steps = []
    for index, value in enumerate(values):
        element_id = f"e{index}"
        state["storage"]["items"].append({"id": element_id, "value": value})
        state["cursor"]["current_id"] = element_id
        steps.append({
            "type": "visit", "payload": {"element_id": element_id},
            "description": f"Добавляем {value}", "line_id": "visit",
            "state_after": deepcopy(state),
        })
    return {
        "schema_version": 2, "kind": "algorithm",
        "algorithm": "test_history", "input": list(values),
        "parameters": {},
        "initial_state": initial, "steps": steps, "result": deepcopy(state),
    }

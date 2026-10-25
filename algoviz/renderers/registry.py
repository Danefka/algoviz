"""A visualization may compose any number of reusable structure views."""
from dataclasses import dataclass
from typing import Callable
from .statistics import array_statistics, merge_statistics


@dataclass(frozen=True)
class Visualization:
    id: str
    statistics: Callable
    create_canvas: Callable
    create_scene: Callable


def array_canvas(parent=None):
    from .qt_array import ArrayCanvas
    return ArrayCanvas(parent)


def array_scene(execution, algorithm, on_progress, options=None):
    from .manim_array import ArrayScene
    return ArrayScene(execution, title=algorithm.title, on_progress=on_progress, **(options or {}))


def merge_canvas(parent=None):
    from .qt_merge import MergeCanvas
    return MergeCanvas(parent)


def merge_scene(execution, algorithm, on_progress, options=None):
    from .manim_merge import MergeScene
    return MergeScene(execution, title=algorithm.title, on_progress=on_progress, **(options or {}))


VISUALIZATIONS = {
    "array": Visualization("array", array_statistics, array_canvas, array_scene),
    "merge_tree": Visualization("merge_tree", merge_statistics, merge_canvas, merge_scene),
}


def get_visualization(visualization_id):
    try:
        return VISUALIZATIONS[visualization_id]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Неизвестная визуализация: {visualization_id}") from exc
